"""Build four gross living-biomass addition rates from Gibbs/GFW raster tiles.

The 2001-2023 published raster gives cumulative gross CO2 removals per hectare
in above- and below-ground living biomass. The annual mean is converted to tC
per hectare per year, then area-weighted within FAO ecological-zone biomes.

This module only builds and checks the biome rate table. It does not execute the
country accounting pipeline or interpret spatial dispersion as rate uncertainty.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window

from .config import (
    GFW_GIBBS_PERIOD_YEARS,
    GFW_GIBBS_REMOVALS_DIR,
    GFW_GIBBS_REMOVALS_PATTERN,
    GFW_GIBBS_STRIPE_ROWS,
    GEZ_DOMAIN_TO_BIOME,
    GEZ_SHP,
    SUMMARY,
)
from .validation import write_table

CARBON_FRACTION_OF_CO2 = 12.0 / 44.0
BIOME_ORDER = ["tropical", "subtropical", "temperate", "boreal"]
BIOME_CODE = {biome: index + 1 for index, biome in enumerate(BIOME_ORDER)}


def annual_rate_tc_ha_yr(cumulative_mg_co2_ha: np.ndarray | float, period_years: int = GFW_GIBBS_PERIOD_YEARS):
    """Convert cumulative Mg CO2/ha into mean annual tC/ha/yr."""
    if period_years <= 0:
        raise ValueError("period_years must be positive")
    return np.asarray(cumulative_mg_co2_ha) * CARBON_FRACTION_OF_CO2 / period_years


def _biome_shapes(gez_path: str, bounds) -> list[tuple[object, int]]:
    """Read FAO GEZ polygons intersecting bounds and encode their four biomes."""
    zones = pyogrio.read_dataframe(gez_path, columns=["gez_code"], bbox=bounds)
    shapes = []
    for geom, raw_code in zip(zones.geometry, zones["gez_code"]):
        if geom is None or pd.isna(raw_code):
            continue
        domain = int(raw_code) // 10
        biome = GEZ_DOMAIN_TO_BIOME.get(domain)
        if biome is not None:
            shapes.append((geom, BIOME_CODE[biome]))
    return shapes


def _weighted_moments(rate: np.ndarray, biome_grid: np.ndarray, latitude_centres: np.ndarray) -> dict[int, tuple[float, float, float, int]]:
    """Return area-weighted mean, spatial SD, area proxy and pixel count by biome."""
    output = {}
    weights = np.cos(np.deg2rad(latitude_centres))[:, None]
    for code in BIOME_CODE.values():
        selected = (biome_grid == code) & np.isfinite(rate)
        if not selected.any():
            continue
        w = np.broadcast_to(weights, rate.shape)[selected]
        x = rate[selected].astype(np.float64)
        total_w = float(w.sum())
        mean = float(np.dot(w, x) / total_w)
        variance = float(np.dot(w, (x - mean) ** 2) / total_w)
        output[code] = (mean, float(np.sqrt(max(variance, 0.0))), total_w, int(selected.sum()))
    return output


def aggregate_tile(path: str | Path, gez_path: str = GEZ_SHP, stripe_rows: int = GFW_GIBBS_STRIPE_ROWS) -> pd.DataFrame:
    """Area-weight annualized gross-removal values by biome for one 10x10° tile.

    Raster values are cumulative Mg CO2/ha for 2001-2023. Pixel area weights
    account for the latitude-dependent area of geographic-grid cells.
    """
    if stripe_rows < 1:
        raise ValueError("stripe_rows must be at least one")
    totals = {code: np.zeros(4, dtype=np.float64) for code in BIOME_CODE.values()}
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise ValueError(f"Expected EPSG:4326 Gibbs raster, got {src.crs}")
        if src.count != 1:
            raise ValueError(f"Expected one cumulative-removals band, got {src.count} in {path}")
        dx, dy = abs(src.transform.a), abs(src.transform.e)
        if dx <= 0 or dy <= 0:
            raise ValueError(f"Invalid raster pixel size in {path}")
        shapes = _biome_shapes(gez_path, (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top))
        if not shapes:
            return pd.DataFrame(columns=["biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "area_weight_sum", "pixel_count"])

        for row in range(0, src.height, stripe_rows):
            n_rows = min(stripe_rows, src.height - row)
            window = Window(0, row, src.width, n_rows)
            transform = src.window_transform(window)
            biome_grid = rasterize(
                shapes,
                out_shape=(n_rows, src.width),
                transform=transform,
                fill=0,
                dtype="uint8",
            )
            cumulative = src.read(1, window=window, masked=True).astype(np.float64)
            values = np.asarray(cumulative.filled(np.nan))
            if np.any(values[np.isfinite(values)] < 0):
                raise ValueError(
                    f"Negative values found in 30 m gross-removals tile {path}; "
                    "check the source version and sign convention before aggregation."
                )
            rates = annual_rate_tc_ha_yr(values)
            north = transform.f
            latitudes = north + (np.arange(n_rows) + 0.5) * transform.e
            moments = _weighted_moments(rates, biome_grid, latitudes)
            for code, (mean, sd, weight_sum, count) in moments.items():
                # Accumulate moments across stripes using stable first and second moments.
                totals[code][0] += mean * weight_sum
                totals[code][1] += (sd**2 + mean**2) * weight_sum
                totals[code][2] += weight_sum
                totals[code][3] += count

    rows = []
    for biome, code in BIOME_CODE.items():
        weighted_sum, weighted_second, weight_sum, count = totals[code]
        if weight_sum == 0:
            continue
        mean = weighted_sum / weight_sum
        variance = max(weighted_second / weight_sum - mean**2, 0.0)
        rows.append({
            "biome": biome,
            "rate_tc_ha_yr_mean": mean,
            "rate_tc_ha_yr_spatial_sd": float(np.sqrt(variance)),
            "area_weight_sum": weight_sum,
            "pixel_count": int(count),
            "source_tile": Path(path).name,
        })
    return pd.DataFrame(rows)


def combine_tile_summaries(summaries: list[pd.DataFrame]) -> pd.DataFrame:
    """Combine tile moments into global area-weighted biome rates."""
    if not summaries:
        raise ValueError("No Gibbs/GFW tile summaries supplied")
    tiles = pd.concat(summaries, ignore_index=True)
    required = {"biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "area_weight_sum", "pixel_count"}
    if not required.issubset(tiles.columns):
        raise ValueError(f"Tile summaries missing columns: {sorted(required - set(tiles.columns))}")
    records = []
    for biome in BIOME_ORDER:
        group = tiles.loc[tiles["biome"] == biome]
        weight = group["area_weight_sum"].to_numpy(dtype=np.float64)
        if weight.sum() <= 0:
            raise ValueError(f"No Gibbs/GFW forest pixels found for biome {biome}")
        mean = group["rate_tc_ha_yr_mean"].to_numpy(dtype=np.float64)
        sd = group["rate_tc_ha_yr_spatial_sd"].to_numpy(dtype=np.float64)
        global_mean = float(np.dot(weight, mean) / weight.sum())
        second = float(np.dot(weight, sd**2 + mean**2) / weight.sum())
        records.append({
            "biome": biome,
            "rate_tc_ha_yr_mean": global_mean,
            "rate_tc_ha_yr_spatial_sd": float(np.sqrt(max(second - global_mean**2, 0.0))),
            "area_weight_sum": float(weight.sum()),
            "pixel_count": int(group["pixel_count"].sum()),
            "period": "2001-2023 mean annual rate",
            "pool": "above- and below-ground living biomass",
            "source": "Gibbs et al. (2025), Harvard Dataverse DOI 10.7910/DVN/V2ISRH",
            "spatial_sd_interpretation": "spatial dispersion; not an estimate of rate uncertainty",
        })
    return pd.DataFrame(records)


def run() -> pd.DataFrame:
    """Build the global four-biome GFW/Gibbs rate table from locally staged tiles."""
    files = sorted(GFW_GIBBS_REMOVALS_DIR.glob(GFW_GIBBS_REMOVALS_PATTERN))
    if not files:
        raise FileNotFoundError(
            f"No Gibbs/GFW 2001-2023 gross-removals tiles found in {GFW_GIBBS_REMOVALS_DIR}. "
            "Stage the published Harvard Dataverse files there; the full raster set is about 37 GB."
        )
    print(f"  aggregating {len(files)} Gibbs/GFW gross-removals tiles")
    summaries = []
    for index, path in enumerate(files, start=1):
        print(f"    [{index}/{len(files)}] {path.name}")
        summaries.append(aggregate_tile(path))
    rates = combine_tile_summaries(summaries)
    write_table(rates, SUMMARY / "gfw_gibbs_biome_rates.csv")
    write_table(pd.concat(summaries, ignore_index=True), SUMMARY / "gfw_gibbs_tile_rates.csv")
    return rates
