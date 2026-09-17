"""Q: Are the intermediate and final tables internally consistent?

Outputs (output/validation/):
- coverage.csv                  : which inputs each territory has
- biome_share_comparison.csv    : GEZ x forest mask shares versus FRA-reported shares
- global_checks.csv             : named checks with value, expectation and status
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, BCW_COUNTRY_CSV, CARBON_TO_CO2, SUMMARY, VALIDATION
from .validation import write_table


def coverage(territories: pd.DataFrame, gcw_table: pd.DataFrame, ncw_table: pd.DataFrame) -> pd.DataFrame:
    shares = pd.read_csv(SUMMARY / "biome_shares.csv").groupby("iso3")["source"].first().rename("biome_share_source")
    table = territories[["iso3", "name", "in_fra", "in_bcw"]].merge(shares, on="iso3", how="outer")
    table = table.merge(gcw_table[["iso3", "uptake_tco2_yr_mean", "faostat_net_uptake_tco2_yr"]], on="iso3", how="outer")
    table = table.merge(ncw_table[["iso3", "has_gcw", "has_bcw"]], on="iso3", how="outer")
    mapping = pd.read_csv(SUMMARY / "bcw_territory_mapping.csv")[["bcw_code", "unit_code"]]
    alignment = pd.read_csv(SUMMARY / "bcw_draw_alignment.csv").merge(mapping, on="bcw_code")
    status = alignment.groupby("unit_code")["alignment"].agg(lambda s: ";".join(sorted(set(s)))).rename("bcw_alignment")
    return table.merge(status, left_on="iso3", right_index=True, how="left").sort_values("iso3")


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

    rate_checks = pd.read_csv(SUMMARY / "pan_rate_checks.csv")
    for _, row in rate_checks.iterrows():
        add(row["check"], round(float(row["value"]), 4), round(float(row["reference"]), 4), bool(row["ok"]))

    areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    year = areas.loc[areas["year"].astype(str) == AREA_YEAR]
    add(f"countries where primary forest exceeds NRF ({AREA_YEAR}, descriptive)", int(year["primary_exceeds_nrf"].sum()), "0",
        int(year["primary_exceeds_nrf"].sum()) == 0)

    by_biome = pd.read_csv(SUMMARY / "forest_area_by_biome.csv")
    excl = by_biome.loc[by_biome["variant"] == "excl_mangroves"]
    add(f"countries where FRA mangroves exceed the tropical forest area ({AREA_YEAR})",
        int(excl["mangroves_exceed_tropical_area"].sum()), "0", int(excl["mangroves_exceed_tropical_area"].sum()) == 0)
    fra_forest = year.loc[year["iso3"].isin(excl["iso3"]), "forest"].sum() - year.loc[year["iso3"].isin(excl["iso3"]), "mangroves"].sum()
    add("country areas by biome sum to FRA forest minus mangroves (ha)", round(float(excl["area_ha"].sum())),
        round(float(fra_forest)), abs(excl["area_ha"].sum() - fra_forest) <= 1e-6 * fra_forest + year["mangroves"].sum() * 0.01)

    merged = excl.merge(rates[["pan_biome", "rate_tc_ha_yr_mean", "flux_pgc_yr_mean", "pan_area_ha"]], on="pan_biome")
    merged["uptake_pgc_yr"] = merged["area_ha"] * merged["rate_tc_ha_yr_mean"] / 1e9
    for biome, group in merged.groupby("pan_biome"):
        info = f"{group['area_ha'].sum() / 1e6:.0f} Mha FRA x GEZ vs {group['pan_area_ha'].iloc[0] / 1e6:.0f} Mha Pan"
        add(f"{biome}: FRA x GEZ uptake vs Pan flux (Pg C/yr; {info})", round(group["uptake_pgc_yr"].sum(), 3),
            round(group["flux_pgc_yr_mean"].iloc[0], 3), True)

    world_tc = float(np.nansum(pan_draws["excl_mangroves"], axis=0).mean() / CARBON_TO_CO2 / 1e9)
    add("global forest uptake Route B (Pg C/yr, mean)", round(world_tc, 3), "Pan gross sink 3.53 (areas differ)", True)

    add("GSCC mean (US$2015/tCO2)", round(float(gcw["gscc"].mean()), 2), "559.57", abs(gcw["gscc"].mean() - 559.57) < 0.1)

    alignment = pd.read_csv(SUMMARY / "bcw_draw_alignment.csv")["alignment"]
    add("BCW draw rows not aligned", int((alignment == "unmatched").sum()), "0", int((alignment == "unmatched").sum()) == 0)

    bcw_units_world = np.nansum(ncw["bcw_usd2015_yr"], axis=0)
    bcw_rows_world = np.nansum(ncw["bcw_published_rows_usd2015_yr"], axis=0) + np.nansum(ncw["bcw_mangrove_gapfill_usd2015_yr"], axis=0)
    gap = float(np.max(np.abs(bcw_units_world - bcw_rows_world) / np.abs(bcw_rows_world)))
    add("world BCW = published BCW rows + mangrove gap-fill (draw by draw, C12, C18)", gap, "< 1e-5", gap < 1e-5)
    gapfill = pd.read_csv(SUMMARY / "bcw_mangrove_gapfill.csv")
    add("units with FRA mangroves but no BCW mangroves, gap-filled (C18)",
        f"{len(gapfill)} units, {gapfill['fra_mangroves_km2'].sum():,.0f} km2", "documented", True)

    mapping = pd.read_csv(SUMMARY / "bcw_territory_mapping.csv")
    add("BCW rows mapped to exactly one unit", int(mapping["bcw_code"].duplicated().sum()), "0",
        not mapping["bcw_code"].duplicated().any())
    territories = pd.read_csv(SUMMARY / "territories.csv")
    published = pd.read_csv(BCW_COUNTRY_CSV)["Population"].sum()
    add("world population: units vs published BCW rows (duplicated parts removed, C12)",
        f"{territories['population'].sum():.4e} vs {published:.4e}", "units <= published", territories["population"].sum() <= published)

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
