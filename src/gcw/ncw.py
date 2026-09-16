"""Q: What is the Natural Carbon Wealth of each territory (forest + ocean)?

NCW_i = GCW_i (mangroves excluded from forest areas) + BCW_i, summed draw by draw (C7, C8).
Alternative kept for C7: GCW including mangroves + BCW - value of BCW mangrove uptake.

Outputs: output/country_level_ncw.csv, output/draws/ncw_draws.npz,
         data_source/summary/bcw_draw_alignment.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BCW_COUNTRY_CSV, BCW_DRAWS_NPZ, CARBON_TO_CO2, OUTPUT, SUMMARY
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
    report = pd.DataFrame({"iso3": bcw["ISO"], "bcw_name": bcw["country_name"], "alignment": status})
    return aligned, report


def build_ncw(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    bcw = pd.read_csv(BCW_COUNTRY_CSV)
    bcw = bcw.loc[bcw["ISO"].notna()].reset_index(drop=True)
    bcw_draws, alignment = align_bcw_draws(bcw)
    gscc = gcw_draws["gscc"][None, :]

    iso = sorted(set(bcw["ISO"]) | set(gcw_draws["iso3"]))
    position = {code: i for i, code in enumerate(iso)}
    n_draws = gscc.shape[1]

    def place(codes, matrix) -> np.ndarray:
        full = np.full((len(iso), n_draws), np.nan, dtype=np.float32)
        full[[position[c] for c in codes]] = matrix
        return full

    gcw = place(gcw_draws["iso3"], gcw_draws["gcw_usd2015_yr"])
    gcw_incl = place(gcw_draws["iso3"], gcw_draws["gcw_incl_mangroves_usd2015_yr"])
    bcw_full = place(bcw["ISO"], bcw_draws)
    mangrove_tco2 = bcw["uptake_mang_mean"].fillna(0.0).to_numpy(dtype=np.float32) * CARBON_TO_CO2
    mangrove_value = place(bcw["ISO"], mangrove_tco2[:, None] * gscc)

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
            summarise_draws(ncw_alt, "ncw_alt_mangroves_usd2015_yr")[["ncw_alt_mangroves_usd2015_yr_mean"]],
        ],
        axis=1,
    )
    table["has_gcw"] = ~np.isnan(gcw).all(axis=1)
    table["has_bcw"] = ~np.isnan(bcw_full).all(axis=1)
    info = territories[["iso3", "name", "continent", "fra_region", "groups", "population", "gdp"]]
    table = info.merge(table, on="iso3", how="right")
    table["name"] = table["name"].fillna(table["iso3"])
    table["ncw_per_capita_usd2015"] = table["ncw_usd2015_yr_mean"] / table["population"]
    table["ncw_share_of_gdp"] = table["ncw_usd2015_yr_mean"] / table["gdp"]
    table["forest_share_of_ncw"] = table["gcw_usd2015_yr_mean"] / table["ncw_usd2015_yr_mean"]
    table = table.sort_values("ncw_usd2015_yr_mean", ascending=False).reset_index(drop=True)

    draws = {"iso3": np.array(iso), "ncw_usd2015_yr": ncw, "gcw_usd2015_yr": gcw, "bcw_usd2015_yr": bcw_full}
    return table, draws, alignment


def run(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict]:
    table, draws, alignment = build_ncw(territories, gcw_draws)
    write_table(alignment, SUMMARY / "bcw_draw_alignment.csv")
    write_table(table, OUTPUT / "country_level_ncw.csv")
    np.savez_compressed(OUTPUT / "draws" / "ncw_draws.npz", **draws)
    return table, draws
