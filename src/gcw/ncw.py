"""Q: What is the Natural Carbon Wealth of each territory (forest + ocean)?

NCW_i = GCW_i (mangroves excluded from forest areas) + BCW_i, summed draw by draw (C7, C8).
Units are the GCW (FRA) units: BCW rows are first summed draw by draw into their unit (C12).
Alternative kept for C7: GCW including mangroves + BCW - value of BCW mangrove uptake.
Gap-fill (C18): units with FRA mangroves but no BCW mangroves receive a BCW mangrove component
estimated with the BCW framework: FRA mangrove area (km2) x BCW mangrove rate draws (tC/km2/yr).

Outputs: output/country_level_ncw.csv, output/draws/ncw_draws.npz,
         data_source/summary/bcw_draw_alignment.csv, data_source/summary/bcw_mangrove_gapfill.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BCW_DRAWS_NPZ, BCW_MANGROVE_RATE_ROW, CARBON_TO_CO2, GAPFILL_AREA_YEAR, OUTPUT, SUMMARY
from .territories import bcw_mapping, read_bcw_table
from .validation import summarise_draws, write_table


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
    """Units with FRA mangroves but no BCW mangroves: FRA area x BCW mangrove rate draws (C18)."""
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


def build_ncw(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    bcw = read_bcw_table()
    bcw_row_draws, alignment = align_bcw_draws(bcw)
    bcw_units, bcw_unit_draws, bcw_mangroves = aggregate_bcw_to_units(bcw, bcw_row_draws)
    gscc = gcw_draws["gscc"][None, :]
    gapfill, gapfill_tc = mangrove_gapfill(bcw_mangroves, gscc.shape[1])
    gapfill["gapfill_bcw_usd2015_yr_mean"] = (gapfill_tc * CARBON_TO_CO2 * gscc).mean(axis=1)

    iso = sorted(set(bcw_units) | set(gcw_draws["iso3"]) | set(gapfill["iso3"]))
    position = {code: i for i, code in enumerate(iso)}
    n_draws = gscc.shape[1]

    def place(codes, matrix) -> np.ndarray:
        full = np.full((len(iso), n_draws), np.nan, dtype=np.float32)
        full[[position[c] for c in codes]] = matrix
        return full

    gcw = place(gcw_draws["iso3"], gcw_draws["gcw_usd2015_yr"])
    gcw_incl = place(gcw_draws["iso3"], gcw_draws["gcw_incl_mangroves_usd2015_yr"])
    bcw_published = place(bcw_units, bcw_unit_draws)
    gapfill_value = place(gapfill["iso3"], (gapfill_tc * CARBON_TO_CO2 * gscc).astype(np.float32))
    gapfill_tco2 = place(gapfill["iso3"], (gapfill_tc * CARBON_TO_CO2).astype(np.float32))
    no_bcw = np.isnan(bcw_published) & np.isnan(gapfill_value)
    bcw_full = np.where(no_bcw, np.nan, np.nan_to_num(bcw_published) + np.nan_to_num(gapfill_value)).astype(np.float32)
    mangrove_tc = bcw_mangroves.set_index("iso3")["bcw_mangrove_uptake_tc_yr"]
    mangrove_value = place(list(mangrove_tc.index), (mangrove_tc.to_numpy() * CARBON_TO_CO2).astype(np.float32)[:, None] * gscc)
    mangrove_value = np.nan_to_num(mangrove_value) + np.nan_to_num(gapfill_value)

    both_missing = np.isnan(gcw) & np.isnan(bcw_full)
    ncw = np.where(both_missing, np.nan, np.nan_to_num(gcw) + np.nan_to_num(bcw_full))
    ncw_alt = np.where(
        both_missing, np.nan, np.nan_to_num(gcw_incl) + np.nan_to_num(bcw_full) - np.nan_to_num(mangrove_value)
    )

    table = pd.concat(
        [
            pd.DataFrame({"iso3": iso}),
            summarise_draws(ncw, "ncw_usd2015_yr"),
            summarise_draws(gcw, "gcw_usd2015_yr")[["gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95"]],
            summarise_draws(bcw_full, "bcw_usd2015_yr")[["bcw_usd2015_yr_mean", "bcw_usd2015_yr_p05", "bcw_usd2015_yr_p95"]],
            summarise_draws(bcw_published, "bcw_published_usd2015_yr")[["bcw_published_usd2015_yr_mean"]],
            summarise_draws(gapfill_value, "bcw_mangrove_gapfill_usd2015_yr")[["bcw_mangrove_gapfill_usd2015_yr_mean"]],
            summarise_draws(ncw_alt, "ncw_alt_mangroves_usd2015_yr")[["ncw_alt_mangroves_usd2015_yr_mean"]],
        ],
        axis=1,
    )
    table["has_gcw"] = ~np.isnan(gcw).all(axis=1)
    table["has_bcw"] = ~np.isnan(bcw_full).all(axis=1)
    table["bcw_mangrove_gapfilled"] = table["iso3"].isin(gapfill["iso3"])
    info = territories[["iso3", "name", "bcw_codes", "continent", "fra_region", "groups", "population", "gdp"]]
    table = info.merge(table, on="iso3", how="right")
    table["name"] = table["name"].fillna(table["iso3"])
    table["ncw_per_capita_usd2015"] = table["ncw_usd2015_yr_mean"] / table["population"]
    table["ncw_share_of_gdp"] = table["ncw_usd2015_yr_mean"] / table["gdp"]
    table["forest_share_of_ncw"] = table["gcw_usd2015_yr_mean"] / table["ncw_usd2015_yr_mean"]
    table = table.sort_values("ncw_usd2015_yr_mean", ascending=False).reset_index(drop=True)

    draws = {
        "iso3": np.array(iso), "ncw_usd2015_yr": ncw, "gcw_usd2015_yr": gcw, "bcw_usd2015_yr": bcw_full,
        "bcw_published_rows_usd2015_yr": bcw_row_draws, "bcw_codes": bcw["bcw_code"].to_numpy(),
        "bcw_mangrove_gapfill_usd2015_yr": gapfill_value, "bcw_mangrove_gapfill_tco2_yr": gapfill_tco2,
    }
    return table, draws, alignment, gapfill


def run(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict]:
    table, draws, alignment, gapfill = build_ncw(territories, gcw_draws)
    write_table(alignment, SUMMARY / "bcw_draw_alignment.csv")
    write_table(gapfill, SUMMARY / "bcw_mangrove_gapfill.csv")
    write_table(table, OUTPUT / "country_level_ncw.csv")
    np.savez_compressed(OUTPUT / "draws" / "ncw_draws.npz", **draws)
    return table, draws
