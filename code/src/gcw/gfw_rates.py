"""Build four gross living-biomass addition rates from Gibbs/GFW raster tiles.

The 2001-2023 published raster gives cumulative gross CO2 removals per hectare
in above- and below-ground living biomass. The annual mean is converted to tC
per hectare per year, then area-weighted within FAO ecological-zone biomes.

This module only builds and checks the biome rate table. It does not execute the
country accounting pipeline or interpret spatial dispersion as rate uncertainty.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from contextlib import nullcontext

import numpy as np
import pandas as pd
import pyogrio
import shapely
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
    GIBBS_OUTPUT,
)
from .validation import write_table

CARBON_FRACTION_OF_CO2 = 12.0 / 44.0
BIOME_ORDER = ["tropical", "subtropical", "temperate", "boreal"]
BIOME_CODE = {biome: index + 1 for index, biome in enumerate(BIOME_ORDER)}
EARTH_RADIUS_M = 6_371_008.8
GFW_MANGROVE_FOREST_TYPE = 6
FOREST_TYPE_SUFFIX = "_removal_forest_type.tif"


def annual_rate_tc_ha_yr(cumulative_mg_co2_ha: np.ndarray | float, period_years: int = GFW_GIBBS_PERIOD_YEARS):
    """Convert cumulative Mg CO2/ha into mean annual tC/ha/yr."""
    if period_years <= 0:
        raise ValueError("period_years must be positive")
    return np.asarray(cumulative_mg_co2_ha) * CARBON_FRACTION_OF_CO2 / period_years


def _biome_shapes(gez_path: str, bounds) -> list[tuple[object, int]]:
    """Read FAO GEZ polygons intersecting bounds and encode their four biomes."""
    _, _, geometries, values = pyogrio.raw.read(gez_path, columns=["gez_code"], bbox=bounds)
    shapes = []
    if geometries is None or len(geometries) == 0 or values is None or len(values) == 0:
        return shapes
    for geometry, raw_code in zip(geometries, values[0]):
        if geometry is None or raw_code is None or pd.isna(raw_code):
            continue
        domain = int(raw_code) // 10
        biome = GEZ_DOMAIN_TO_BIOME.get(domain)
        if biome is not None:
            shapes.append((shapely.from_wkb(geometry), BIOME_CODE[biome]))
    return shapes


def _weighted_moments(rate: np.ndarray, biome_grid: np.ndarray, pixel_area_ha: np.ndarray) -> dict[int, tuple[float, float, float, int]]:
    """Return spherical-area-weighted moments and valid area by biome.

    ``pixel_area_ha`` may be a per-row vector because all pixels in an EPSG:4326
    raster row have the same area.
    """
    output = {}
    weights = np.asarray(pixel_area_ha, dtype=np.float64)
    if weights.ndim == 1:
        weights = weights[:, None]
    weights = np.broadcast_to(weights, rate.shape)
    for code in BIOME_CODE.values():
        selected = (biome_grid == code) & np.isfinite(rate)
        if not selected.any():
            continue
        w = weights[selected]
        x = rate[selected].astype(np.float64)
        total_w = float(w.sum())
        mean = float(np.dot(w, x) / total_w)
        variance = float(np.dot(w, (x - mean) ** 2) / total_w)
        output[code] = (mean, float(np.sqrt(max(variance, 0.0))), total_w, int(selected.sum()))
    return output


def aggregate_tile(
    path: str | Path,
    gez_path: str = GEZ_SHP,
    stripe_rows: int = GFW_GIBBS_STRIPE_ROWS,
    forest_type_path: str | Path | None = None,
) -> pd.DataFrame:
    """Area-weight annualized gross-removal values by biome for one 10x10° tile.

    Raster values are cumulative Mg CO2/ha for 2001-2023. Pixel area weights
    account for the latitude-dependent area of geographic-grid cells.
    """
    if stripe_rows < 1:
        raise ValueError("stripe_rows must be at least one")
    totals = {code: np.zeros(4, dtype=np.float64) for code in BIOME_CODE.values()}
    negative_pixel_counts = {code: 0 for code in BIOME_CODE.values()}
    mangrove_area_ha = {code: 0.0 for code in BIOME_CODE.values()}
    mangrove_pixel_counts = {code: 0 for code in BIOME_CODE.values()}
    forest_type_context = rasterio.open(forest_type_path) if forest_type_path is not None else nullcontext(None)
    with rasterio.open(path) as src, forest_type_context as forest_type:
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise ValueError(f"Expected EPSG:4326 Gibbs raster, got {src.crs}")
        if src.count != 1:
            raise ValueError(f"Expected one cumulative-removals band, got {src.count} in {path}")
        if forest_type is not None and (
            forest_type.count != 1
            or forest_type.crs != src.crs
            or forest_type.shape != src.shape
            or not forest_type.transform.almost_equals(src.transform)
        ):
            raise ValueError(f"Forest-type raster is not aligned with the Gibbs tile: {forest_type_path}")
        dx, dy = abs(src.transform.a), abs(src.transform.e)
        if dx <= 0 or dy <= 0:
            raise ValueError(f"Invalid raster pixel size in {path}")
        shapes = _biome_shapes(gez_path, (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top))
        if not shapes:
            return pd.DataFrame(columns=["biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "area_ha", "pixel_count"])
        # Build one mask per tile. It uses about 1.6 GB for a 40,000 x 40,000
        # tile, which avoids re-burning thousands of GEZ polygons for every stripe.
        biome_grid = rasterize(
            shapes,
            out_shape=(src.height, src.width),
            transform=src.transform,
            fill=0,
            dtype="uint8",
        )

        for row in range(0, src.height, stripe_rows):
            n_rows = min(stripe_rows, src.height - row)
            window = Window(0, row, src.width, n_rows)
            transform = src.window_transform(window)
            biome_stripe = biome_grid[row:row + n_rows]
            cumulative = src.read(1, window=window, masked=True).astype(np.float64)
            values = np.asarray(cumulative.filled(np.nan))
            mangrove = (
                forest_type.read(1, window=window) == GFW_MANGROVE_FOREST_TYPE
                if forest_type is not None
                else np.zeros(values.shape, dtype=bool)
            )
            # Keep source values unchanged. The official WRI model documents this
            # layer as positive gross removals, but a subset of published pixels is
            # negative. Count them for auditing; do not clip or flip them.
            negative = np.isfinite(values) & (values < 0)
            for code in BIOME_CODE.values():
                negative_pixel_counts[code] += int(np.count_nonzero(negative & (biome_stripe == code) & ~mangrove))
            lat_north = transform.f + np.arange(n_rows, dtype=np.float64) * transform.e
            lat_south = lat_north + transform.e
            pixel_area_ha = (
                EARTH_RADIUS_M**2
                * np.deg2rad(dx)
                * (np.sin(np.deg2rad(lat_north)) - np.sin(np.deg2rad(lat_south)))
                / 10_000.0
            )
            for code in BIOME_CODE.values():
                excluded = mangrove & np.isfinite(values) & (biome_stripe == code)
                mangrove_pixel_counts[code] += int(np.count_nonzero(excluded))
                mangrove_area_ha[code] += float(np.dot(np.count_nonzero(excluded, axis=1), pixel_area_ha))
            rates = annual_rate_tc_ha_yr(np.where(mangrove, np.nan, values))
            moments = _weighted_moments(rates, biome_stripe, pixel_area_ha)
            for code, (mean, sd, weight_sum, count) in moments.items():
                # Accumulate moments across stripes using stable first and second moments.
                totals[code][0] += mean * weight_sum
                totals[code][1] += (sd**2 + mean**2) * weight_sum
                totals[code][2] += weight_sum
                totals[code][3] += count

    rows = []
    for biome, code in BIOME_CODE.items():
        weighted_sum, weighted_second, weight_sum, count = totals[code]
        if weight_sum == 0 and mangrove_pixel_counts[code] == 0:
            continue
        # Retain an audit row even when every valid pixel in this tile/biome
        # was excluded. Its zero weight leaves the combined rate unchanged.
        mean = weighted_sum / weight_sum if weight_sum else 0.0
        variance = max(weighted_second / weight_sum - mean**2, 0.0) if weight_sum else 0.0
        rows.append({
            "biome": biome,
            "rate_tc_ha_yr_mean": mean,
            "rate_tc_ha_yr_spatial_sd": float(np.sqrt(variance)),
            "area_ha": weight_sum,
            "pixel_count": int(count),
            "negative_source_pixel_count": negative_pixel_counts[code],
            "excluded_mangrove_pixel_count": mangrove_pixel_counts[code],
            "excluded_mangrove_area_ha": mangrove_area_ha[code],
            "source_tile": Path(path).name,
        })
    return pd.DataFrame(rows)


def combine_tile_summaries(summaries: list[pd.DataFrame]) -> pd.DataFrame:
    """Combine tile moments into global area-weighted biome rates."""
    if not summaries:
        raise ValueError("No Gibbs/GFW tile summaries supplied")
    tiles = pd.concat(summaries, ignore_index=True)
    required = {
        "biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "area_ha",
        "pixel_count", "negative_source_pixel_count",
    }
    if not required.issubset(tiles.columns):
        raise ValueError(f"Tile summaries missing columns: {sorted(required - set(tiles.columns))}")
    records = []
    for biome in BIOME_ORDER:
        group = tiles.loc[tiles["biome"] == biome]
        weight = group["area_ha"].to_numpy(dtype=np.float64)
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
            "area_ha": float(weight.sum()),
            "pixel_count": int(group["pixel_count"].sum()),
            "negative_source_pixel_count": int(group["negative_source_pixel_count"].sum()),
            "negative_source_pixel_share": float(
                group["negative_source_pixel_count"].sum() / group["pixel_count"].sum()
            ),
            "excluded_mangrove_pixel_count": int(group["excluded_mangrove_pixel_count"].sum()) if "excluded_mangrove_pixel_count" in group else 0,
            "excluded_mangrove_area_ha": float(group["excluded_mangrove_area_ha"].sum()) if "excluded_mangrove_area_ha" in group else 0.0,
            "period": "2001-2023 mean annual rate",
            "pool": "above- and below-ground living biomass",
            "source": "Gibbs et al. (2025), Harvard Dataverse DOI 10.7910/DVN/V2ISRH",
            "spatial_sd_interpretation": "spatial dispersion; not an estimate of rate uncertainty",
        })
    return pd.DataFrame(records)


def run(max_workers: int = 8, forest_type_dir: str | Path | None = None) -> pd.DataFrame:
    """Build the global four-biome GFW/Gibbs rate table from locally staged tiles."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least one")
    files = sorted(GFW_GIBBS_REMOVALS_DIR.glob(GFW_GIBBS_REMOVALS_PATTERN))
    if not files:
        raise FileNotFoundError(
            f"No Gibbs/GFW 2001-2023 gross-removals tiles found in {GFW_GIBBS_REMOVALS_DIR}. "
            "Stage the published Harvard Dataverse files there; the full raster set is about 37 GB."
        )
    print(f"  aggregating {len(files)} Gibbs/GFW gross-removals tiles with {max_workers} workers", flush=True)
    forest_type_paths = [
        Path(forest_type_dir) / (path.name.split("_gross_removals", 1)[0] + FOREST_TYPE_SUFFIX)
        if forest_type_dir is not None else None
        for path in files
    ]
    missing = [path for path in forest_type_paths if path is not None and not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} source-version forest-type rasters; first: {missing[0]}")
    summaries_by_index: list[pd.DataFrame | None] = [None] * len(files)
    if max_workers == 1:
        for index, path in enumerate(files):
            print(f"    [{index + 1}/{len(files)}] {path.name}", flush=True)
            summaries_by_index[index] = aggregate_tile(path, forest_type_path=forest_type_paths[index])
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(aggregate_tile, path, GEZ_SHP, GFW_GIBBS_STRIPE_ROWS, forest_type_paths[index]): (index, path)
                for index, path in enumerate(files)
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                index, path = futures[future]
                summaries_by_index[index] = future.result()
                print(f"    [{completed}/{len(files)}] {path.name}", flush=True)
    summaries = [summary for summary in summaries_by_index if summary is not None]
    rates = combine_tile_summaries(summaries)
    suffix = "_non_mangrove" if forest_type_dir is not None else ""
    write_table(rates, GIBBS_OUTPUT / f"gfw_gibbs_biome_rates{suffix}.csv")
    write_table(pd.concat(summaries, ignore_index=True), GIBBS_OUTPUT / f"gfw_gibbs_tile_rates{suffix}.csv")
    return rates
