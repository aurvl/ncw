"""Q: What is the Natural Carbon Wealth of each territory (forest + ocean)?

NCW_i = GCW_i (documented FRA forest-mangrove overlap removed) + BCW_i, summed draw by draw.
Units are the GCW (FRA) units: BCW rows are first summed draw by draw into their unit.
Alternative: GCW including mangroves + BCW - value of BCW mangrove uptake.
Gap-fill: units with FRA mangroves but no BCW mangroves receive a BCW mangrove component
estimated with the BCW framework: FRA mangrove area (km2) x BCW mangrove rate draws (tC/km2/yr).

Outputs: results/country_level_ncw.csv, results/draws/ncw_draws.npz,
         data/derived/bcw_draw_alignment.csv, data/derived/bcw_mangrove_gapfill.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    BCW_DRAWS_NPZ,
    BCW_MANGROVE_RATE_ROW,
    CARBON_TO_CO2,
    GAPFILL_AREA_YEAR,
    GMW_MANGROVE_AREA_CSV,
    OUTPUT,
    SUMMARY,
)
from .territories import bcw_mapping, read_bcw_table
from .validation import summarise_draws, write_npz_atomic, write_table


def align_bcw_draws(bcw: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Match BCW draw rows to the published BCW table.

    The BCW release saves draw rows in computation order and the CSV sorted by name, so rows are
    matched on their mean and Monte Carlo standard error (the BCW `_se` column is sd / sqrt(B)).
    """
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        draws = archive["bcw_draws"]
    n_draws = draws.shape[1]
    with np.errstate(invalid="ignore"):
        means = np.nanmean(draws, axis=1)
        mc_se = np.nanstd(draws, axis=1, ddof=1) / np.sqrt(n_draws)
    aligned = np.full((len(bcw), n_draws), np.nan, dtype=np.float32)
    used: set[int] = set()
    status = []
    for position, (value, se) in enumerate(zip(bcw["Total BCW"], bcw["Total BCW_se"])):
        if np.isnan(value):
            status.append("no_bcw_value")
            continue
        candidates = [
            i for i in np.flatnonzero(np.isclose(means, value, rtol=1e-5) & np.isclose(mc_se, se, rtol=1e-3))
            if i not in used
        ]
        if not candidates:
            status.append("unmatched")
            continue
        used.add(candidates[0])
        aligned[position] = draws[candidates[0]]
        status.append("matched" if len(candidates) == 1 else "matched_first_of_identical")
    report = pd.DataFrame({"bcw_code": bcw["bcw_code"], "bcw_name": bcw["country_name"], "alignment": status})
    return aligned, report


def aggregate_bcw_to_units(bcw: pd.DataFrame, draws: np.ndarray) -> tuple[list[str], np.ndarray, pd.DataFrame]:
    """Sum BCW draws, mangrove uptake and mangrove area of the rows mapped to each unit."""
    mapping = bcw_mapping(bcw).set_index("bcw_code")["unit_code"]
    unit_of_row = bcw["bcw_code"].map(mapping).to_numpy()
    units = sorted(set(unit_of_row))
    unit_draws = np.full((len(units), draws.shape[1]), np.nan, dtype=np.float32)
    mangroves = []
    for position, unit in enumerate(units):
        rows = unit_of_row == unit
        block = draws[rows]
        if not np.isnan(block).all():
            unit_draws[position] = np.nansum(block, axis=0)
        mangroves.append({
            "iso3": unit,
            "bcw_mangroves_km2": bcw.loc[rows, "mangroves_area_km2"].fillna(0.0).sum(),
            "bcw_mangrove_uptake_tc_yr": bcw.loc[rows, "uptake_mang_mean"].fillna(0.0).sum(),
        })
    return units, unit_draws, pd.DataFrame(mangroves)


def mangrove_gapfill(bcw_mangroves: pd.DataFrame, n_draws: int) -> tuple[pd.DataFrame, np.ndarray]:
    """Units with FRA mangroves but no BCW mangroves: FRA area x BCW mangrove rate draws."""
    areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    fra = areas.loc[areas["year"].astype(str) == GAPFILL_AREA_YEAR, ["iso3", "mangroves"]]
    fra = fra.assign(fra_mangroves_km2=fra["mangroves"] / 100.0).drop(columns="mangroves")
    table = fra.merge(bcw_mangroves, on="iso3", how="left").fillna({"bcw_mangroves_km2": 0.0, "bcw_mangrove_uptake_tc_yr": 0.0})
    table = table.loc[(table["fra_mangroves_km2"] > 0) & (table["bcw_mangroves_km2"] <= 0)].reset_index(drop=True)
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        rate = archive["bce_rates_draws"][BCW_MANGROVE_RATE_ROW][:n_draws].astype(np.float64)  # tC/km2/yr
    uptake_tc = table["fra_mangroves_km2"].to_numpy()[:, None] * rate[None, :]
    table["rate_tc_km2_yr_mean"] = rate.mean()
    table["gapfill_uptake_tc_yr_mean"] = uptake_tc.mean(axis=1)
    table["gapfill_uptake_tco2_yr_mean"] = table["gapfill_uptake_tc_yr_mean"] * CARBON_TO_CO2
    return table, uptake_tc


def combine_complete_accounts(gcw: np.ndarray, bcw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return national NCW only where both ecosystem accounts have observations."""
    gcw = np.asarray(gcw, dtype=np.float64)
    bcw = np.asarray(bcw, dtype=np.float64)
    if gcw.shape != bcw.shape or gcw.ndim != 2:
        raise ValueError("GCW and BCW must be same-shaped two-dimensional draw arrays")
    has_gcw = ~np.isnan(gcw).all(axis=1)
    has_bcw = ~np.isnan(bcw).all(axis=1)
    complete = has_gcw & has_bcw
    ncw = np.full(gcw.shape, np.nan, dtype=np.float64)
    ncw[complete] = np.nan_to_num(gcw[complete]) + np.nan_to_num(bcw[complete])
    return ncw, has_gcw, has_bcw, complete


def forest_share_for_composition(
    gcw_mean: np.ndarray,
    ncw_mean: np.ndarray,
    has_gcw: np.ndarray,
    has_bcw: np.ndarray,
) -> np.ndarray:
    """Forest share for map composition: missing BCW is NA; BCW-only is 0%."""
    gcw_mean = np.asarray(gcw_mean, dtype=np.float64)
    ncw_mean = np.asarray(ncw_mean, dtype=np.float64)
    has_gcw = np.asarray(has_gcw, dtype=bool)
    has_bcw = np.asarray(has_bcw, dtype=bool)
    if not (gcw_mean.shape == ncw_mean.shape == has_gcw.shape == has_bcw.shape):
        raise ValueError("Composition inputs must have identical shapes")
    share = np.full(gcw_mean.shape, np.nan, dtype=np.float64)
    complete = has_gcw & has_bcw & np.isfinite(ncw_mean) & (ncw_mean != 0)
    share[complete] = gcw_mean[complete] / ncw_mean[complete]
    share[~has_gcw & has_bcw] = 0.0
    return share


def build_ncw(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bcw = read_bcw_table()
    bcw_row_draws, alignment = align_bcw_draws(bcw)
    bcw_units, bcw_unit_draws, bcw_mangroves = aggregate_bcw_to_units(bcw, bcw_row_draws)
    gscc = gcw_draws["gscc"][None, :]
    gapfill, gapfill_tc = mangrove_gapfill(bcw_mangroves, gscc.shape[1])

    # A mapped mangrove area cannot turn a missing national BCW account into a
    # complete account. Keep the gap-fill only for units with a published BCW total.
    source_bcw_available = dict(zip(bcw_units, ~np.isnan(bcw_unit_draws).all(axis=1)))
    keep_gapfill = gapfill["iso3"].map(source_bcw_available).fillna(False).to_numpy(dtype=bool)
    gapfill = gapfill.loc[keep_gapfill].reset_index(drop=True)
    gapfill_tc = gapfill_tc[keep_gapfill]
    gapfill["gapfill_bcw_usd2015_yr_mean"] = (gapfill_tc * CARBON_TO_CO2 * gscc).mean(axis=1)

    gmw_areas = pd.read_csv(GMW_MANGROVE_AREA_CSV)
    if gmw_areas["iso3"].duplicated().any() or (gmw_areas["gmw_2025_mangrove_area_ha"] < 0).any():
        raise ValueError("GMW 2025 mangrove areas must be unique by unit and non-negative")
    iso = sorted(set(bcw_units) | set(gcw_draws["iso3"]) | set(gapfill["iso3"]) | set(gmw_areas["iso3"]))
    position = {code: i for i, code in enumerate(iso)}
    n_draws = gscc.shape[1]

    def place(codes, matrix) -> np.ndarray:
        full = np.full((len(iso), n_draws), np.nan, dtype=np.float32)
        full[[position[c] for c in codes]] = matrix
        return full

    gcw = place(gcw_draws["iso3"], gcw_draws["gcw_usd2015_yr"])
    gcw_spatial_low = place(gcw_draws["iso3"], gcw_draws["gcw_spatial_sd_low_usd2015_yr"])
    gcw_spatial_high = place(gcw_draws["iso3"], gcw_draws["gcw_spatial_sd_high_usd2015_yr"])
    gcw_no_overlap_removed = place(gcw_draws["iso3"], gcw_draws["gcw_no_overlap_removed_usd2015_yr"])
    bcw_published = place(bcw_units, bcw_unit_draws)
    gapfill_value = place(gapfill["iso3"], (gapfill_tc * CARBON_TO_CO2 * gscc).astype(np.float32))
    gapfill_tco2 = place(gapfill["iso3"], (gapfill_tc * CARBON_TO_CO2).astype(np.float32))
    no_bcw = np.isnan(bcw_published) & np.isnan(gapfill_value)
    bcw_current = np.where(no_bcw, np.nan, np.nan_to_num(bcw_published) + np.nan_to_num(gapfill_value)).astype(np.float32)

    # Keep the published BCW rate/price draws, but replace mangrove area with
    # GMW 2025 polygons allocated to the same territorial units as the BCW account.
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        mangrove_rate = archive["bce_rates_draws"][BCW_MANGROVE_RATE_ROW][:n_draws].astype(np.float64)
    gmw_area = gmw_areas.set_index("iso3")["gmw_2025_mangrove_area_ha"].reindex(iso, fill_value=0.0)
    current_area = pd.Series(0.0, index=iso)
    current_area = current_area.add(
        bcw_mangroves.set_index("iso3")["bcw_mangroves_km2"].mul(100.0), fill_value=0.0
    )
    if not gapfill.empty:
        current_area = current_area.add(
            gapfill.set_index("iso3")["fra_mangroves_km2"].mul(100.0), fill_value=0.0
        )
    area_delta = gmw_area - current_area
    gmw_adjustment = (
        area_delta.to_numpy(dtype=np.float64)[:, None] / 100.0
        * mangrove_rate[None, :] * CARBON_TO_CO2 * gscc
    ).astype(np.float32)
    has_published_bcw = ~np.isnan(bcw_published).all(axis=1)
    gmw_adjustment[~has_published_bcw] = np.nan
    bcw_gmw = np.full_like(bcw_current, np.nan)
    valid_bcw = has_published_bcw & ~np.isnan(bcw_current).all(axis=1)
    bcw_gmw[valid_bcw] = bcw_current[valid_bcw] + gmw_adjustment[valid_bcw]
    gmw_mangrove_value = (
        gmw_area.to_numpy(dtype=np.float64)[:, None] / 100.0
        * mangrove_rate[None, :] * CARBON_TO_CO2 * gscc
    ).astype(np.float32)
    gmw_mangrove_tco2 = (
        gmw_area.to_numpy(dtype=np.float64)[:, None] / 100.0
        * mangrove_rate[None, :] * CARBON_TO_CO2
    ).astype(np.float32)
    mangrove_area_audit = pd.DataFrame(
        {
            "iso3": iso,
            "bcw_mangroves_before_gmw_ha": current_area.to_numpy(),
            "gmw_2025_mangroves_ha": gmw_area.to_numpy(),
            "delta_mangroves_ha": area_delta.to_numpy(),
        }
    )

    ncw, has_gcw, has_bcw, complete_accounts = combine_complete_accounts(gcw, bcw_gmw)
    ncw_spatial_low = np.full_like(ncw, np.nan)
    ncw_spatial_high = np.full_like(ncw, np.nan)
    ncw_alt = np.full_like(ncw, np.nan)
    ncw_spatial_low[complete_accounts] = (
        np.nan_to_num(gcw_spatial_low[complete_accounts]) + np.nan_to_num(bcw_gmw[complete_accounts])
    )
    ncw_spatial_high[complete_accounts] = (
        np.nan_to_num(gcw_spatial_high[complete_accounts]) + np.nan_to_num(bcw_gmw[complete_accounts])
    )
    ncw_alt[complete_accounts] = (
        np.nan_to_num(gcw_no_overlap_removed[complete_accounts])
        + np.nan_to_num(bcw_gmw[complete_accounts])
        - np.nan_to_num(gmw_mangrove_value[complete_accounts])
    )

    table = pd.concat(
        [
            pd.DataFrame({"iso3": iso}),
            summarise_draws(ncw, "ncw_usd2015_yr"),
            summarise_draws(ncw_spatial_low, "ncw_spatial_sd_low_usd2015_yr")["ncw_spatial_sd_low_usd2015_yr_mean"].to_frame(),
            summarise_draws(ncw_spatial_high, "ncw_spatial_sd_high_usd2015_yr")["ncw_spatial_sd_high_usd2015_yr_mean"].to_frame(),
            summarise_draws(gcw, "gcw_usd2015_yr")[["gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95"]],
            summarise_draws(bcw_gmw, "bcw_usd2015_yr")[["bcw_usd2015_yr_mean", "bcw_usd2015_yr_p05", "bcw_usd2015_yr_p95"]],
            summarise_draws(bcw_published, "bcw_published_usd2015_yr")[["bcw_published_usd2015_yr_mean"]],
            summarise_draws(gapfill_value, "bcw_mangrove_gapfill_usd2015_yr")[["bcw_mangrove_gapfill_usd2015_yr_mean"]],
            summarise_draws(gmw_mangrove_value, "bcw_gmw_mangroves_usd2015_yr")[["bcw_gmw_mangroves_usd2015_yr_mean"]],
            summarise_draws(ncw_alt, "ncw_alt_mangroves_usd2015_yr")[["ncw_alt_mangroves_usd2015_yr_mean"]],
        ],
        axis=1,
    )
    table["has_gcw"] = has_gcw
    table["has_bcw"] = has_bcw
    table["bcw_mangrove_gapfilled"] = table["iso3"].isin(gapfill["iso3"])
    info = territories[["iso3", "name", "bcw_codes", "continent", "fra_region", "groups", "population", "gdp"]]
    table = info.merge(table, on="iso3", how="right")
    table["name"] = table["name"].fillna(table["iso3"])
    table["ncw_per_capita_usd2015"] = table["ncw_usd2015_yr_mean"] / table["population"]
    table["ncw_share_of_gdp"] = table["ncw_usd2015_yr_mean"] / table["gdp"]
    table["forest_share_of_ncw"] = forest_share_for_composition(
        table["gcw_usd2015_yr_mean"].to_numpy(),
        table["ncw_usd2015_yr_mean"].to_numpy(),
        has_gcw,
        has_bcw,
    )
    table = table.sort_values("ncw_usd2015_yr_mean", ascending=False).reset_index(drop=True)

    draws = {
        "iso3": np.array(iso), "ncw_usd2015_yr": ncw, "ncw_spatial_sd_low_usd2015_yr": ncw_spatial_low,
        "ncw_spatial_sd_high_usd2015_yr": ncw_spatial_high, "gcw_usd2015_yr": gcw, "bcw_usd2015_yr": bcw_gmw,
        "bcw_published_rows_usd2015_yr": bcw_row_draws, "bcw_codes": bcw["bcw_code"].to_numpy(),
        "bcw_mangrove_gapfill_usd2015_yr": gapfill_value, "bcw_mangrove_gapfill_tco2_yr": gapfill_tco2,
        "bcw_gmw_mangrove_adjustment_usd2015_yr": gmw_adjustment,
        "gmw_mangrove_value_usd2015_yr": gmw_mangrove_value,
        "gmw_mangrove_tco2_yr": gmw_mangrove_tco2,
    }
    return table, draws, alignment, gapfill, mangrove_area_audit


def run(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict]:
    table, draws, alignment, gapfill, mangrove_area_audit = build_ncw(territories, gcw_draws)
    write_table(alignment, SUMMARY / "bcw_draw_alignment.csv")
    write_table(gapfill, SUMMARY / "bcw_mangrove_gapfill.csv")
    write_table(mangrove_area_audit, SUMMARY / "bcw_mangrove_gmw_area_replacement.csv")
    write_table(table, OUTPUT / "country_level_ncw.csv")
    write_npz_atomic(OUTPUT / "draws" / "ncw_draws.npz", **draws)
    return table, draws
