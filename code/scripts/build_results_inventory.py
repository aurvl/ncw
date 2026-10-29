"""Build the canonical inventory of current manuscript and analysis outputs.

The inventory intentionally excludes superseded country emissions, pre-GMW
mangrove results, old cost-price scenarios, and alternative forest-rate
estimates other than the retained Pan comparison. Historical source files and
old exports remain available for audit outside the canonical inventory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
NEXT = ROOT.parent / "NEXT"
RESULTS = ROOT / "results"
DEST = NEXT / "RESULTS_INVENTORY.txt"

CSV_GROUPS = {
    "Main manuscript tables": [
        ("Table 1 - Global carbon wealth distributions", "tables/manuscript/Table1_global_carbon_wealth.csv"),
        ("Table 2 - Geographic and economic profiles", "tables/manuscript/Table2_geographic_economic_profiles.csv"),
        ("Table 3 - Forest capacity erosion by economic group", "tables/manuscript/Table3_forest_capacity_erosion.csv"),
        ("Table 4 - Our 2% GCW allocation", "tables/manuscript/Table4_our_2pct_gcw_allocation.csv"),
    ],
    "Current physical, geographic, and country-account results": [
        ("Table S1 - Paper-ready four-biome forest additions", "tables/manuscript/TableS1_forest_biome_additions.csv"),
        ("Detailed four-biome forest additions and Gibbs/GFW rates", "tables/manuscript/Supplementary_forest_biome_accounting.csv"),
        ("Pan forest-rate comparison - only retained rate comparator", "tables/manuscript/Supplementary_Pan_rate_comparison.csv"),
        ("Country/territory account with current 2024 fields", "tables/manuscript/Supplementary_country_level_accounts_2024.csv"),
        ("Economic-group assignment and provenance for all study units", "validation/economic_group_assignment_by_unit.csv"),
        ("Regional profiles using current accounts and 2024 GDP", "tables/manuscript/Supplementary_region_profiles_2024.csv"),
        ("National top-ten values using current 2024 accounts", "tables/manuscript/Supplementary_national_top10_2024.csv"),
        ("Account concentration statistics", "tables/manuscript/Supplementary_account_concentration_2024.csv"),
        ("Mangrove area source selection and FRA evidence", "tables/manuscript/Supplementary_mangrove_reconciliation.csv"),
    ],
    "Balances, deforestation, and carbon-account comparisons": [
        ("2024 green/blue accounting-balance transitions", "tables/manuscript/Supplementary_accounting_balance_transitions.csv"),
        ("2024 accounting balances by unit", "tables/manuscript/Supplementary_accounting_balances_2024_by_unit.csv"),
        ("2024 accounting balances by economic group", "validation/emissions_2024_accounting_balance_groups.csv"),
        ("Country-level reported forest-capacity loss", "tables/manuscript/Supplementary_country_level_erosion.csv"),
        ("Deforestation trend in the FRA reporting periods", "tables/manuscript/Supplementary_deforestation_trend.csv"),
        ("Capacity-loss projection and capitalisation scenarios", "tables/manuscript/Supplementary_deforestation_scenarios.csv"),
        ("GCW/GDP group comparison tests", "tables/manuscript/Supplementary_GCW_GDP_group_tests_2024.csv"),
        ("GCW versus relative erosion descriptive association", "tables/manuscript/Supplementary_GCW_erosion_association.csv"),
    ],
    "Spatial analysis - nine relationships and their full evidence": [
        ("Spatial relationship/model/weight review dossier", "tables/manuscript/Supplementary_spatial_selection_dossier.csv"),
        ("Standardized coefficients for the three primary relationships, all candidates", "tables/manuscript/Supplementary_spatial_candidate_standardized_coefficients.csv"),
        ("Moran, LM, nested LR, and fit-selection evidence", "tables/manuscript/Supplementary_spatial_model_selection_evidence.csv"),
        ("Coefficient estimates for every fitted spatial candidate", "tables/manuscript/Supplementary_spatial_coefficients_all_candidates.csv"),
        ("Spatial sample audit", "validation/spatial_emissions_2024_sample_audit.csv"),
        ("Step 1 - Moran tests on outcomes and OLS residuals", "validation/spatial_emissions_2024_step1_moran.csv"),
        ("Step 2 - LM and robust LM tests", "validation/spatial_emissions_2024_step2_lm_tests.csv"),
        ("Step 3 - nested likelihood-ratio tests", "validation/spatial_emissions_2024_step3_nested_tests.csv"),
        ("Fit statistics for all estimated spatial models", "validation/spatial_emissions_2024_model_fit.csv"),
        ("Full spatial coefficient table", "validation/spatial_emissions_2024_model_coefficients.csv"),
        ("Predictor-block tests on matched samples", "validation/spatial_emissions_2024_predictor_block_tests.csv"),
        ("Predictor correlations", "validation/spatial_emissions_2024_predictor_correlations.csv"),
        ("Variance-inflation factors", "validation/spatial_emissions_2024_predictor_vif.csv"),
        ("Human decision template - no model auto-selected", "validation/spatial_model_decision_template.csv"),
    ],
    "Climate-finance analyses - separate estimands": [
        ("Our 2% GCW allocation by group", "tables/manuscript/Table4_our_2pct_gcw_allocation.csv"),
        ("Busch action-curve coverage classes", "tables/manuscript/Supplementary_Busch_action_cost_coverage.csv"),
        ("Busch country-level action-cost results", "tables/manuscript/Supplementary_Busch_action_cost_by_unit.csv"),
        ("GSCC valuation-fraction sensitivity by world draw", "validation/gcw_valuation_fraction_sensitivity_world.csv"),
        ("GSCC valuation-fraction sensitivity by unit", "validation/gcw_valuation_fraction_sensitivity_by_unit.csv"),
    ],
}

JSON_FILES = [
    ("2024 socioeconomic source coverage audit", "validation/socioeconomic_2024_coverage_audit.json"),
    ("2024 emissions accounting summary", "validation/emissions_2024_accounting_balance_summary.json"),
    ("Spatial 2024 diagnostics summary", "validation/spatial_emissions_2024_diagnostics.json"),
    ("Figure 4 readiness status", "figures/manuscript/Figure4_spatial_associations_status.json"),
]


def read_csv(relative: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / relative, low_memory=False)


def csv_block(title: str, relative: str) -> str:
    path = (RESULTS / relative).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Missing current inventory input: {path}")
    frame = pd.read_csv(path, low_memory=False)
    # Keep artifact provenance explicit even for a path outside results/.
    source = path.relative_to(ROOT).as_posix()
    body = frame.to_csv(index=False, sep="\t", float_format="%.8g", na_rep="NA", lineterminator="\n").rstrip()
    return f"### {title}\nSource: `{source}` | {len(frame)} rows x {len(frame.columns)} columns\n\n{body}"


def json_block(title: str, relative: str) -> str:
    path = RESULTS / relative
    payload = json.loads(path.read_text(encoding="utf-8"))
    return f"### {title}\nSource: `{path.relative_to(ROOT).as_posix()}`\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


def validate_current_outputs() -> tuple[pd.DataFrame, dict[str, int], pd.DataFrame]:
    country = read_csv("tables/manuscript/Supplementary_country_level_accounts_2024.csv")
    if "UNIT_CODE" not in country or country["UNIT_CODE"].duplicated().any():
        raise ValueError("The current country/territory table must have unique unit identifiers.")
    if "ISO3" not in country or "region" not in country:
        raise ValueError("The current country/territory table needs validated ISO3 and region fields.")
    obsolete_markers = ("2023", "faostat_", "preupdate", "before_gmw", "hilmi_source_mean", "mangrove_area_km2_hilmi_source")
    stale_columns = [
        name for name in country.columns if any(marker in name.lower() for marker in obsolete_markers)
    ]
    if stale_columns:
        raise ValueError(f"Superseded fields remain in the canonical country table: {stale_columns}")
    deforestation = read_csv("tables/manuscript/Supplementary_country_level_erosion.csv")
    transitions = read_csv("tables/manuscript/Supplementary_accounting_balance_transitions.csv")
    counts = {
        "gcw_units": int(country["has_gcw"].fillna(False).astype(bool).sum()),
        "both_accounts": int(
            (country["has_gcw"].fillna(False).astype(bool) & country["has_bcw"].fillna(False).astype(bool)).sum()
        ),
        "balance_common_sample": int(transitions["common_sample_n"].max()),
        "deforestation_reporters": int(deforestation["reported_deforestation"].fillna(False).astype(bool).sum()),
        "positive_loss_units": int(
            (
                deforestation["reported_deforestation"].fillna(False).astype(bool)
                & pd.to_numeric(deforestation["loss_tco2_mean"], errors="coerce").gt(0)
            ).sum()
        ),
        "units_with_2024_gdp": int(country["gdp_2015usd_2024"].notna().sum()),
        "units_with_2024_emissions": int(country["co2_emissions_tco2_2024"].notna().sum()),
        "units_with_all_2024_socioeconomics": int(
            country[["population_2024", "gdp_2015usd_2024", "co2_emissions_tco2_2024"]].notna().all(axis=1).sum()
        ),
    }
    expected = {
        "gcw_units": 236,
        "both_accounts": 174,
        "balance_common_sample": 161,
        "deforestation_reporters": 139,
        "positive_loss_units": 105,
        "units_with_2024_gdp": 196,
        "units_with_2024_emissions": 210,
        "units_with_all_2024_socioeconomics": 193,
    }
    if counts != expected:
        raise ValueError(f"Canonical sample or 2024 coverage changed: {counts}")
    spatial = read_csv("tables/manuscript/Supplementary_spatial_selection_dossier.csv")
    if spatial["relationship"].nunique() != 9 or len(spatial) != 108:
        raise ValueError("Expected six candidate models x two weights x nine primary relationships.")
    return country, counts, spatial


def build_inventory() -> str:
    country, counts, spatial = validate_current_outputs()
    wealth = read_csv("tables/manuscript/Table1_global_carbon_wealth.csv")
    biome = read_csv("tables/manuscript/Supplementary_forest_biome_accounting.csv")
    table3 = read_csv("tables/manuscript/Table3_forest_capacity_erosion.csv")
    table4 = read_csv("tables/manuscript/Table4_our_2pct_gcw_allocation.csv")
    busch = read_csv("tables/manuscript/Supplementary_Busch_action_cost_coverage.csv")
    figure_status = json.loads(
        (RESULTS / "figures/manuscript/Figure4_spatial_associations_status.json").read_text(encoding="utf-8")
    )
    world_flow = float(biome.loc[biome["biome"].eq("Total"), "gross_additions_gtco2_yr"].iloc[0])
    total_loss = float(table3.loc[table3["group"].eq("Total"), "lost_capacity_mtco2_yr"].iloc[0])
    total_lost_value = float(table3.loc[table3["group"].eq("Total"), "lost_gcw_billion_usd2015_yr"].iloc[0])
    allocation_total = float(table4.loc[table4["group"].eq("Total"), "annual_allocation_billion_usd2015"].iloc[0])
    busch_units = int(busch["units"].sum())

    lines = [
        "# Canonical Results Inventory - Natural Carbon Wealth",
        "",
        "Generated from the current manuscript and analysis outputs. Superseded emissions/mangrove versions and non-Pan alternative forest-rate comparisons are excluded from this canonical inventory; old exports are held separately for audit.",
        "",
        "## Canonical data versions and coverage",
        "- Forest rates: Gibbs/GFW gross additions to living above- and below-ground biomass, mean annual period 2001-2023, with mangrove pixels excluded; four FAO GEZ domains; FRA 2025 forest area.",
        "- Marine mangrove area: GMW v4.1.12, map year 2025, directly intersected with EEZ UNION geometries in Mollweide, multiplied by GMW's global 0.9775 accuracy factor, then assigned under the current BCW unit crosswalk; other published BCW components and rates are retained.",
        "- Emissions: Global Carbon Budget 2025 national fossil and industrial-process series through 2024. Population and GDP: WDI 2024. Debt is not used.",
        "- Pan is the only alternative forest-rate estimate retained as a comparison in the current supplementary tables.",
        "- The canonical country table is one row per study unit. Validation of obsolete columns is performed before this inventory is written.",
        "",
        "## Results navigation (from supporting evidence to main findings)",
        "This is an order for reading and drafting, not a ranking of statistical significance.",
        "- Supporting evidence: source coverage, group tests, concentration measures, top-ten lists, spatial diagnostics and candidate comparisons; use these to qualify the main findings.",
        "- National and group distribution: current study-unit country table, regional profiles, economic-group profiles and green/mixed/blue account types.",
        "- Main global estimates: four biome rates and physical forest additions, followed by GCW, BCW and NCW distributions.",
        "- Carbon-balance comparison: green/blue account composition and transitions relative to 2024 emissions on the 161-unit common sample.",
        "- Forest-loss implications: reported deforestation coverage, 105 positive capacity-loss estimates, group differences, relative erosion and scenario values.",
        "- Spatial relationships: three primary outcomes and six emissions extensions, with candidate diagnostics and no final model automatically selected.",
        "- Climate finance: our stipulated 2% GCW allocation, with Busch action costs as a complementary analysis with partial coverage; neither is conflated with the 2% discount rate.",
        "",
        "## Headline values and agreed samples",
        f"- Annual forest additions: {world_flow:.6f} GtCO2/year.",
        f"- GCW mean: {wealth.loc[wealth.component.eq('Green carbon wealth'), 'value_mean_trillion_usd2015_yr'].iloc[0]:.6f} trillion US$2015/year; BCW mean: {wealth.loc[wealth.component.eq('Blue carbon wealth'), 'value_mean_trillion_usd2015_yr'].iloc[0]:.6f}; NCW mean: {wealth.loc[wealth.component.eq('Natural carbon wealth'), 'value_mean_trillion_usd2015_yr'].iloc[0]:.6f}.",
        f"- Reported deforestation capacity loss: {total_loss:.6f} MtCO2/year; corresponding annual lost GCW value: {total_lost_value:.6f} billion US$2015/year.",
        f"- Our allocation rule: 2% of current annual GCW = {allocation_total:.6f} billion US$2015/year. It is not observed finance or an estimated funding need.",
        f"- Unit counts: {counts['gcw_units']} GCW; {counts['both_accounts']} with both accounts; {counts['balance_common_sample']} in the common 2024 balance comparison; {counts['deforestation_reporters']} deforestation reporters, including {counts['positive_loss_units']} with positive estimated loss.",
        f"- 2024 coverage across the study units: GDP {counts['units_with_2024_gdp']}; emissions {counts['units_with_2024_emissions']}; all population/GDP/emissions {counts['units_with_all_2024_socioeconomics']}. Missing values are not replaced with zero.",
        "- Monetary P05-P95 intervals propagate GSCC draws. Pixel spatial standard deviation is a separate sensitivity, not a confidence interval for the biome rates.",
        "- The 2% allocation rate and the 2% discount rate used for the perpetuity scenario are separate inputs. Busch action costs are a separate, partially covered analysis.",
        f"- Busch classification contains {busch_units} positive-loss cases in disjoint coverage categories. The categories at prices above -20 through 0 and at/below -20 are separate groups.",
        f"- Spatial analysis covers {spatial['relationship'].nunique()} primary relationships, each estimated with six model families under two weights ({len(spatial)} fit records in the selection dossier). No final model is auto-selected.",
        f"- Figures 1-3 are generated. Figure 4 status: {figure_status['status']}. The final model/weight decisions remain in `data/outputs/validation/spatial_model_decision_template.csv`.",
        "",
        "## Full outputs by topic",
    ]
    for section, files in CSV_GROUPS.items():
        lines.extend(["", f"## {section}"])
        for title, relative in files:
            lines.extend(["", csv_block(title, relative)])
    lines.extend(["", "## Validation and source audits"])
    for title, relative in JSON_FILES:
        lines.extend(["", json_block(title, relative)])
    extra_csvs = [
        ("2024 emissions accounting balances by unit", "validation/emissions_2024_accounting_balance_by_unit.csv"),
        ("2024 emissions accounting balance summary by group", "validation/emissions_2024_accounting_balance_groups.csv"),
        ("2024 accounting-balance summary values", "validation/emissions_2024_accounting_balance_summary.json"),
    ]
    for title, relative in extra_csvs:
        path = (RESULTS / relative).resolve()
        if path.suffix.lower() == ".json":
            lines.extend(["", json_block(title, relative)])
        else:
            lines.extend(["", csv_block(title, relative)])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    NEXT.mkdir(parents=True, exist_ok=True)
    content = build_inventory()
    temporary = DEST.with_suffix(".txt.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(DEST)
    print(json.dumps({"path": str(DEST), "bytes": DEST.stat().st_size, "lines": len(content.splitlines())}, indent=2))


if __name__ == "__main__":
    main()
