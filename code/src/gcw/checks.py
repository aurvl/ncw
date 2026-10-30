"""Q: Are the intermediate and final tables internally consistent?

Outputs (data/derived/validation/):
- coverage.csv                  : which inputs each territory has
- biome_share_comparison.csv    : GEZ x forest mask shares versus FRA-reported shares
- global_checks.csv             : named checks with value, expectation and status
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, BCW_COUNTRY_CSV, CARBON_TO_CO2, FOREST_OUTPUT, SUMMARY, VALIDATION
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


def global_checks(forest_draws: dict, rates: pd.DataFrame, gcw: dict, ncw: dict) -> pd.DataFrame:
    checks = []

    def add(name, value, expected, ok, status=None):
        checks.append({"check": name, "value": value, "expected": expected, "status": status or ("ok" if ok else "REVIEW")})

    shares = pd.read_csv(SUMMARY / "biome_shares.csv")
    share_sums = shares.groupby("iso3")["share"].sum()
    add("biome shares sum to 1", float((share_sums - 1).abs().max()), "< 1e-6", bool((share_sums - 1).abs().max() < 1e-6))

    expected_biomes = {"tropical", "subtropical", "temperate", "boreal"}
    add("Gibbs/GFW rates cover four biomes exactly", len(rates) == 4 and set(rates["biome"]) == expected_biomes,
        sorted(expected_biomes), len(rates) == 4 and set(rates["biome"]) == expected_biomes)
    valid_rates = rates["rate_tc_ha_yr_mean"].ge(0).all() and rates["rate_tc_ha_yr_spatial_sd"].ge(0).all()
    add("Gibbs/GFW mean rates and spatial SD are non-negative", bool(valid_rates), "True", bool(valid_rates))

    areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    year = areas.loc[areas["year"].astype(str) == AREA_YEAR]
    add(f"countries where primary forest exceeds NRF ({AREA_YEAR}, descriptive)", int(year["primary_exceeds_nrf"].sum()), "0",
        int(year["primary_exceeds_nrf"].sum()) == 0)

    by_biome = pd.read_csv(FOREST_OUTPUT / "forest_area_by_biome.csv")
    main_area = by_biome.loc[by_biome["variant"] == "documented_overlap_removed"].copy()
    tropical = main_area.loc[main_area["biome"] == "tropical"]
    raw_overallocation = int(tropical["fra_mangroves_exceed_tropical_allocation"].sum())
    add(
        f"FRA mangrove category exceeds GEZ tropical allocation ({AREA_YEAR}; overlap unverified)",
        raw_overallocation,
        "audit only; do not subtract unverified category area",
        True,
        status="documented" if raw_overallocation else "ok",
    )
    documented_overallocation = int(tropical["documented_overlap_exceeds_tropical_allocation"].sum())
    add("report-documented Forest mangrove overlap exceeds tropical allocation", documented_overallocation, "0", documented_overallocation == 0)

    overlap_evidence = pd.read_csv(SUMMARY / "fra_mangrove_forest_overlap_2025.csv")
    documented = overlap_evidence.drop_duplicates("iso3").set_index("iso3")["documented_forest_mangrove_area_ha"]
    applicable = year.loc[year["iso3"].isin(main_area["iso3"])].drop_duplicates("iso3").set_index("iso3")
    expected_area = float(applicable["forest"].sum() - documented.reindex(applicable.index).fillna(0.0).sum())
    main_total_area = float(main_area["area_ha"].sum())
    add("country areas by biome sum to FRA forest minus documented Forest mangrove overlap (ha)", round(main_total_area),
        round(expected_area), abs(main_total_area - expected_area) <= 1e-6 * max(expected_area, 1.0))
    overlap_evidence = overlap_evidence.drop_duplicates("iso3")
    documented_total = float(overlap_evidence["documented_forest_mangrove_area_ha"].sum())
    fractions = overlap_evidence[
        [
            "documented_forest_fraction",
            "documented_other_wooded_land_fraction",
            "documented_remaining_land_fraction",
        ]
    ]
    valid_fractions = fractions.isna() | ((fractions >= 0) & (fractions <= 1))
    invalid_fraction_cells = int((~valid_fractions).to_numpy().sum())
    add(
        "FRA documented Forest/OWL/remaining fractions are between 0 and 1",
        invalid_fraction_cells,
        "0",
        bool(valid_fractions.to_numpy().all()),
    )
    classification_gap = (
        overlap_evidence["documented_forest_mangrove_area_ha"]
        + overlap_evidence["documented_other_wooded_land_area_ha"]
        + overlap_evidence["documented_remaining_land_area_ha"]
        + overlap_evidence["unresolved_mangrove_area_ha"]
        - overlap_evidence["fra_mangroves_2025_ha"]
    ).abs().max()
    add(
        "FRA mangrove category decomposes into Forest, OWL, remaining-land and unknown parts",
        classification_gap,
        "< 1e-6",
        classification_gap < 1e-6,
    )
    unresolved_total = float(overlap_evidence["unresolved_mangrove_area_ha"].sum())
    add("FRA mangrove area removed only for documented Forest overlap (ha)",
        round(documented_total), "derived from evidence table", True, status="documented")
    other_wooded_total = float(overlap_evidence["documented_other_wooded_land_area_ha"].sum())
    add("FRA mangrove area documented as Other wooded land (ha)",
        round(other_wooded_total), "derived from evidence table", True, status="documented")
    remaining_land_total = float(overlap_evidence["documented_remaining_land_area_ha"].sum())
    add("FRA mangrove area documented as Remaining land (ha)",
        round(remaining_land_total), "derived from evidence table", True, status="documented")
    add("FRA mangrove area with unknown Forest/OWL classification (ha)",
        round(unresolved_total), "reported for transparent scope", True, status="documented")

    merged = main_area.merge(rates[["biome", "rate_tc_ha_yr_mean"]], on="biome")
    merged["uptake_tc_yr"] = merged["area_ha"] * merged["rate_tc_ha_yr_mean"]
    recalculated = float(merged["uptake_tc_yr"].sum() * CARBON_TO_CO2)
    reported = float(np.nansum(forest_draws["documented_overlap_removed"], axis=0).mean())
    difference = abs(recalculated - reported) / max(abs(recalculated), 1.0)
    add("country-level forest flow reproduces area x biome-rate sum", difference, "< 1e-6", difference < 1e-6)

    add("GSCC mean (US$2015/tCO2)", round(float(gcw["gscc"].mean()), 2), "559.57", abs(gcw["gscc"].mean() - 559.57) < 0.1)

    alignment = pd.read_csv(SUMMARY / "bcw_draw_alignment.csv")
    unmatched = int(alignment["alignment"].eq("unmatched").sum())
    add("BCW draw rows not aligned", unmatched, "0", unmatched == 0)
    source_formula_error = float(alignment["area_rate_formula_max_relative_error"].max())
    add(
        "Hilmi et al. (2026) BCW reproduced from ecosystem areas × rates + BCP, valued with 44/12 and GSCC",
        source_formula_error,
        "< 1e-5",
        source_formula_error < 1e-5,
    )
    bcw_formula = ncw["bcw_sequestration_tco2_yr"] * gcw["gscc"][None, :]
    bcw_updated = ncw["bcw_usd2015_yr"]
    formula_cells = np.isfinite(bcw_formula) & np.isfinite(bcw_updated)
    relative_errors = np.abs(bcw_formula[formula_cells] - bcw_updated[formula_cells]) / np.maximum(
        np.abs(bcw_updated[formula_cells]), 1.0
    )
    selected_formula_error = float(relative_errors.max()) if relative_errors.size else 0.0
    add(
        "updated BCW equals total sequestration from selected mangrove area and other Hilmi inputs × GSCC (draw by draw)",
        selected_formula_error,
        "< 1e-5",
        selected_formula_error < 1e-5,
    )
    area_audit = pd.read_csv(SUMMARY / "bcw_mangrove_gmw_area_replacement.csv")
    source_counts = area_audit["mangrove_area_source"].value_counts().to_dict()
    fra_unreported_selection = int(
        (
            area_audit["mangrove_area_source"].eq("FRA_2025")
            & ~area_audit["fra_2025_mangroves_reported"].fillna(False).astype(bool)
        ).sum()
    )
    add(
        "FRA zero is selected only when the 2025 mangrove area was reported",
        fra_unreported_selection,
        "0",
        fra_unreported_selection == 0,
    )
    source_updated = int(area_audit["mangrove_area_source_updated_from_hilmi"].fillna(False).sum())
    area_changed = int(area_audit["mangrove_area_changed_from_hilmi"].fillna(False).sum())
    area_new_without_hilmi = int(area_audit["mangrove_area_new_where_hilmi_missing"].fillna(False).sum())
    comparable = int(area_audit["mangrove_area_comparable_to_hilmi"].fillna(False).sum())
    source_summary = "; ".join(f"{source}={count}" for source, count in sorted(source_counts.items()))
    add(
        "mangrove area-source selection and comparison with area reported by Hilmi et al. (2026)",
        f"{source_summary}; selected from a different source={source_updated}; changed area among units with both values={area_changed}/{comparable}; selected where Hilmi area was unavailable={area_new_without_hilmi}",
        "documented",
        True,
        status="documented",
    )

    mapping = pd.read_csv(SUMMARY / "bcw_territory_mapping.csv")
    add("BCW rows mapped to exactly one unit", int(mapping["bcw_code"].duplicated().sum()), "0",
        not mapping["bcw_code"].duplicated().any())
    territories = pd.read_csv(SUMMARY / "territories.csv")
    published = pd.read_csv(BCW_COUNTRY_CSV)["Population"].sum()
    add("world population: units vs published BCW rows (duplicated parts removed)",
        f"{territories['population'].sum():.4e} vs {published:.4e}", "units <= published", territories["population"].sum() <= published)

    has_gcw = ~np.isnan(ncw["gcw_usd2015_yr"]).all(axis=1)
    has_bcw = ~np.isnan(ncw["bcw_usd2015_yr"]).all(axis=1)
    complete = has_gcw & has_bcw
    any_component = has_gcw | has_bcw
    mismatch = int((any_component != ~np.isnan(ncw["ncw_usd2015_yr"]).all(axis=1)).sum())
    add(
        "national NCW sums available components and remains missing only when both are unavailable",
        mismatch,
        "0",
        mismatch == 0,
    )
    missing_bcw_with_value = int((~has_bcw & ~np.isnan(ncw["bcw_usd2015_yr"]).all(axis=1)).sum())
    add(
        "units without BCW data do not receive a numeric BCW account value",
        missing_bcw_with_value,
        "0",
        missing_bcw_with_value == 0,
    )
    ncw_complete = np.nansum(ncw["ncw_usd2015_yr"][complete], axis=0)
    parts_complete = (
        np.nansum(ncw["gcw_usd2015_yr"][complete], axis=0)
        + np.nansum(ncw["bcw_usd2015_yr"][complete], axis=0)
    )
    complete_gap = float(np.max(np.abs(ncw_complete - parts_complete) / np.maximum(np.abs(parts_complete), 1.0)))
    add(
        "complete-case national NCW equals GCW + BCW draw by draw",
        complete_gap,
        "< 1e-5",
        complete_gap < 1e-5,
    )
    # Account draw arrays are stored as float32 to keep the national archive
    # compact. Promote before aggregation so global totals use the same
    # double-precision summation as the manuscript table builder.
    global_gcw = np.nansum(np.asarray(ncw["gcw_usd2015_yr"], dtype=np.float64), axis=0)
    global_bcw = np.nansum(np.asarray(ncw["bcw_usd2015_yr"], dtype=np.float64), axis=0)
    global_ncw_additive = global_gcw + global_bcw
    global_ncw_from_archive = np.nansum(
        np.asarray(ncw["ncw_usd2015_yr"], dtype=np.float64), axis=0
    )
    global_additive_gap = float(
        np.max(np.abs(global_ncw_from_archive - global_ncw_additive)
               / np.maximum(np.abs(global_ncw_additive), 1.0))
    )
    add(
        "global additive NCW equals global available GCW + BCW draw by draw",
        {
            "relative_gap": global_additive_gap,
            "GCW_mean_trillion": float(global_gcw.mean() / 1e12),
            "BCW_mean_trillion": float(global_bcw.mean() / 1e12),
            "additive_NCW_mean_trillion": float(global_ncw_additive.mean() / 1e12),
            "archive_NCW_mean_trillion": float(global_ncw_from_archive.mean() / 1e12),
        },
        "relative gap < 1e-5; all available components on both sides",
        global_additive_gap < 1e-5,
    )
    return pd.DataFrame(checks)


def run(territories, gcw_table, ncw_table, forest_draws, rates, gcw, ncw) -> pd.DataFrame:
    write_table(coverage(territories, gcw_table, ncw_table), VALIDATION / "coverage.csv")
    write_table(share_comparison(), VALIDATION / "biome_share_comparison.csv")
    table = global_checks(forest_draws, rates, gcw, ncw)
    write_table(table, VALIDATION / "global_checks.csv")
    for _, row in table.iterrows():
        print(f"  [{row['status']:>6}] {row['check']}: {row['value']} (expected {row['expected']})")
    failures = table.loc[table["status"].eq("REVIEW"), "check"].tolist()
    if failures:
        raise ValueError(f"Pipeline validation failed: {failures}")
    return table
