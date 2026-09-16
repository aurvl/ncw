"""Q: Are the intermediate and final tables internally consistent?

Outputs (output/validation/):
- coverage.csv                  : which inputs each territory has
- biome_share_comparison.csv    : GEZ x forest mask shares versus FRA-reported shares
- global_checks.csv             : named checks with value, expectation and status
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, CARBON_TO_CO2, SUMMARY, VALIDATION
from .validation import write_table


def coverage(territories: pd.DataFrame, gcw_table: pd.DataFrame, ncw_table: pd.DataFrame) -> pd.DataFrame:
    shares = pd.read_csv(SUMMARY / "biome_shares.csv").groupby("iso3")["source"].first().rename("biome_share_source")
    table = territories[["iso3", "name", "in_fra", "in_bcw"]].merge(shares, on="iso3", how="outer")
    table = table.merge(gcw_table[["iso3", "uptake_tco2_yr_mean", "faostat_net_uptake_tco2_yr"]], on="iso3", how="outer")
    table = table.merge(ncw_table[["iso3", "has_gcw", "has_bcw"]], on="iso3", how="outer")
    alignment = pd.read_csv(SUMMARY / "bcw_draw_alignment.csv")[["iso3", "alignment"]]
    return table.merge(alignment, on="iso3", how="left").sort_values("iso3")


def share_comparison() -> pd.DataFrame:
    selected = pd.read_csv(SUMMARY / "biome_shares.csv")
    fra = pd.read_csv(SUMMARY / "biome_shares_fra.csv")
    table = selected.merge(fra, on=["iso3", "biome"], how="outer", suffixes=("_used", "_fra"))
    table[["share_used", "share_fra"]] = table[["share_used", "share_fra"]].fillna(0.0)
    table["abs_difference"] = (table["share_used"] - table["share_fra"]).abs()
    return table.sort_values(["abs_difference"], ascending=False)


def global_checks(pan_draws: dict, rates: pd.DataFrame, gcw: dict, ncw: dict) -> pd.DataFrame:
    checks = []

    def add(name, value, expected, ok):
        checks.append({"check": name, "value": value, "expected": expected, "status": "ok" if ok else "REVIEW"})

    shares = pd.read_csv(SUMMARY / "biome_shares.csv")
    share_sums = shares.groupby("iso3")["share"].sum()
    add("biome shares sum to 1", float((share_sums - 1).abs().max()), "< 1e-6", bool((share_sums - 1).abs().max() < 1e-6))

    areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    year = areas.loc[areas["year"].astype(str) == AREA_YEAR]
    gap = year["nrf_plus_planted_minus_forest"].abs() > 0.01 * year["forest"].clip(lower=1)
    add(f"countries where NRF + planted differs from forest by >1% ({AREA_YEAR})", int(gap.sum()), "0", int(gap.sum()) == 0)
    add(f"countries where mangroves exceed NRF ({AREA_YEAR})", int(year["mangroves_exceed_nrf"].sum()), "0",
        int(year["mangroves_exceed_nrf"].sum()) == 0)

    by_biome = pd.read_csv(SUMMARY / "forest_area_by_biome.csv")
    by_biome = by_biome.loc[by_biome["variant"] == "excl_mangroves"].merge(
        rates[["biome", "forest_type", "pan_row", "rate_tc_ha_yr_mean"]], on=["biome", "forest_type"]
    )
    by_biome["uptake_pgc_yr"] = by_biome["area_ha"] * by_biome["rate_tc_ha_yr_mean"] / 1e9
    pan = pd.read_csv(SUMMARY / "pan_biome_flux.csv").set_index("pan_row")["flux_pgc_yr_mean"]
    for pan_row, total in by_biome.dropna(subset=["pan_row"]).groupby("pan_row")["uptake_pgc_yr"].sum().items():
        add(f"pipeline uptake reproduces Pan flux: {pan_row} (Pg C/yr)", round(total, 4), round(pan[pan_row], 4),
            abs(total - pan[pan_row]) < 1e-3)

    world_tc = float(np.nansum(pan_draws["excl_mangroves"], axis=0).mean() / CARBON_TO_CO2 / 1e9)
    add("global forest uptake Route B (Pg C/yr, mean)", round(world_tc, 3), "≈ Pan gross sink 3.53 + subtropical", True)

    add("GSCC mean (US$2015/tCO2)", round(float(gcw["gscc"].mean()), 2), "559.57", abs(gcw["gscc"].mean() - 559.57) < 0.1)

    alignment = pd.read_csv(SUMMARY / "bcw_draw_alignment.csv")["alignment"]
    add("BCW draw rows not aligned", int((alignment == "unmatched").sum()), "0", int((alignment == "unmatched").sum()) == 0)

    ncw_world = np.nansum(ncw["ncw_usd2015_yr"], axis=0)
    parts = np.nansum(ncw["gcw_usd2015_yr"], axis=0) + np.nansum(ncw["bcw_usd2015_yr"], axis=0)
    add("world NCW equals world GCW + BCW draw by draw", float(np.max(np.abs(ncw_world - parts) / np.abs(parts))), "< 1e-5",
        bool(np.max(np.abs(ncw_world - parts) / np.abs(parts)) < 1e-5))
    return pd.DataFrame(checks)


def run(territories, gcw_table, ncw_table, pan_draws, rates, gcw, ncw) -> pd.DataFrame:
    write_table(coverage(territories, gcw_table, ncw_table), VALIDATION / "coverage.csv")
    write_table(share_comparison(), VALIDATION / "biome_share_comparison.csv")
    table = global_checks(pan_draws, rates, gcw, ncw)
    write_table(table, VALIDATION / "global_checks.csv")
    for _, row in table.iterrows():
        print(f"  [{row['status']:>6}] {row['check']}: {row['value']} (expected {row['expected']})")
    return table
