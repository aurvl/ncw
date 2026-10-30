"""Build the ten documented study tables from prepared pipeline outputs.

The script only reads the canonical source/derived products and writes the
public-facing table set under ``results/tables``. Heavy raster/source stages are
handled separately by ``main.py --rebuild-derived``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "results" / "tables"
DERIVED = ROOT / "data" / "derived"
VALIDATION = DERIVED / "validation"
BIOMES = ("tropical", "subtropical", "temperate", "boreal")
BCES = ("saltmarsh", "seagrass", "mangrove")
STATS = ("mean", "sd", "p05", "p50", "p95")
C_TO_CO2 = 44.0 / 12.0


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required pipeline output is missing: {path.relative_to(ROOT)}")
    return pd.read_csv(path, low_memory=False)


def summarize(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64).ravel()
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {stat: np.nan for stat in STATS}
    percentiles = np.percentile(finite, [5, 50, 95])
    # Avoid a tiny positive SD from floating-point reduction when every draw is
    # exactly the same; a deterministic component has zero draw dispersion.
    if finite.size < 2:
        sd = np.nan
    elif np.all(finite == finite[0]):
        sd = 0.0
    else:
        sd = float(np.std(finite, ddof=1))
    return {
        "mean": float(np.mean(finite)),
        "sd": sd,
        "p05": float(percentiles[0]),
        "p50": float(percentiles[1]),
        "p95": float(percentiles[2]),
    }


def draw_lookup(archive: np.lib.npyio.NpzFile, key: str) -> dict[str, np.ndarray]:
    entities = archive["iso3"].astype(str)
    values = np.asarray(archive[key], dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != len(entities):
        raise ValueError(f"Unexpected draw shape for {key}: {values.shape}")
    return {code: values[i] for i, code in enumerate(entities)}


def summarize_by_entity(lookup: dict[str, np.ndarray], codes: pd.Series, label: str) -> pd.DataFrame:
    rows = []
    for code in codes.astype(str):
        stats = summarize(lookup.get(code, np.array([np.nan])))
        rows.append({f"{label}_{stat}": stats[stat] for stat in STATS})
    return pd.DataFrame(rows, index=codes.index)


def summary_rows(lookup: dict[str, np.ndarray], codes, draw_count: int,
                 factor: float = 1.0) -> list[dict[str, float]]:
    """Summarize each entity's draw vector once, returning every statistic."""
    return [
        summarize(lookup.get(str(code), np.full(draw_count, np.nan)) * factor)
        for code in codes
    ]


def source_frames(master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv(ROOT / "data/raw/environmental/marine/bcw/output/country_level_bcw.csv")
    mapping = read_csv(DERIVED / "bcw_territory_mapping.csv")
    mapping = mapping.rename(columns={"bcw_code": "ISO", "bcw_name": "mapping_name"})
    # The two non-country BCW residual rows have no ISO in the source file.
    raw["ISO"] = raw["ISO"].fillna(raw["country_name"].map({
        "Joint Regimes": "BCW-JR", "Overlapping Claims": "BCW-OC",
    }))
    if mapping["ISO"].duplicated().any():
        raise ValueError("The BCW-to-entity crosswalk contains duplicate source codes.")
    source = raw.merge(mapping, on="ISO", how="left", validate="one_to_one")
    if source["unit_code"].isna().any():
        missing = source.loc[source["unit_code"].isna(), "ISO"].astype(str).tolist()
        raise ValueError(f"BCW source codes without an entity mapping: {missing[:10]}")
    entity = master.drop_duplicates("UNIT_CODE").set_index("UNIT_CODE", drop=False)
    return source, entity


def build_01_bcw(master: pd.DataFrame, ncw_archive: np.lib.npyio.NpzFile,
                 gscc: np.ndarray) -> pd.DataFrame:
    source, entity = source_frames(master)
    bcp_tc = draw_lookup(ncw_archive, "bcp_tco2_yr")
    salt_tco2 = draw_lookup(ncw_archive, "saltmarsh_tco2_yr")
    sea_tco2 = draw_lookup(ncw_archive, "seagrass_tco2_yr")
    mang_tco2 = draw_lookup(ncw_archive, "selected_mangrove_tco2_yr")
    blue_usd = draw_lookup(ncw_archive, "bcw_usd2015_yr")

    rename = {
        "country_name": "country_name", "TERRITORY1": "territory1", "ISO": "iso",
        "SOVEREIGN1": "sovereign1", "Continent": "continent", "Groups": "groups",
        "saltmarshes_area_km2": "saltmarsh_area_km2",
        "seagrasses_area_km2": "seagrass_area_km2",
        "mangroves_area_km2": "source_mang_area_km2",
        "uptake_salt_mean": "saltmarsh_sequestration_tc_yr_mean",
        "uptake_salt_se": "saltmarsh_sequestration_tc_yr_se",
        "uptake_seag_mean": "seagrass_sequestration_tc_yr_mean",
        "uptake_seag_se": "seagrass_sequestration_tc_yr_se",
    }
    keep_source = [column for column in rename if column in source.columns]
    out = source[["unit_code", "role", *keep_source]].rename(columns=rename)
    out = out.rename(columns={"unit_code": "account_unit_code", "role": "mapping_role"})
    out["account_summary_row"] = out["mapping_role"].isin(["unit_row", "main_part"])
    # Attach entity-level updated account values only once, on the row representing
    # the account itself; component records remain visible without double-counting.
    summary = out["account_summary_row"]
    codes = out.loc[summary, "account_unit_code"].astype(str)
    if codes.duplicated().any() or len(codes) != len(entity):
        raise ValueError("Expected exactly one primary BCW source row per harmonized entity.")
    row_to_entity = out["account_unit_code"].astype(str)
    out["updated_mangrove_area_km2"] = np.nan
    out["updated_mangrove_source"] = pd.NA
    out["mangrove_sequestration_tc_yr_mean"] = np.nan
    out["mangrove_sequestration_tc_yr_sd"] = np.nan
    out["coastal_bce_sequestration_tc_yr_mean"] = np.nan
    out["coastal_bce_sequestration_tc_yr_sd"] = np.nan
    out["bcp_sequestration_tc_yr"] = np.nan
    out["total_bcseq_tc_yr_mean"] = np.nan
    out["total_bcseq_tc_yr_sd"] = np.nan
    for account in ("coastal_bcw_usd2015_yr", "ocean_bcw_usd2015_yr", "bcw_usd2015_yr"):
        for stat in STATS:
            out[f"{account}_{stat}"] = np.nan
    for pos in out.index[summary]:
        code = str(row_to_entity.loc[pos])
        values = entity.loc[code]
        out.loc[pos, "updated_mangrove_area_km2"] = values["mangrove_area_selected_ha"] / 100.0
        out.loc[pos, "updated_mangrove_source"] = values["mangrove_area_source"]
        tco2_draws = mang_tco2.get(code, np.array([np.nan]))
        stats = summarize(tco2_draws * (12 / 44))
        out.loc[pos, "mangrove_sequestration_tc_yr_mean"] = stats["mean"]
        out.loc[pos, "mangrove_sequestration_tc_yr_sd"] = stats["sd"]
        coastal_draws = np.vstack([
            salt_tco2.get(code, np.array([np.nan])),
            sea_tco2.get(code, np.array([np.nan])),
            mang_tco2.get(code, np.array([np.nan])),
        ]) * (12 / 44)
        coastal = np.nansum(coastal_draws, axis=0)
        coastal[np.all(~np.isfinite(coastal_draws), axis=0)] = np.nan
        stats = summarize(coastal)
        out.loc[pos, "coastal_bce_sequestration_tc_yr_mean"] = stats["mean"]
        out.loc[pos, "coastal_bce_sequestration_tc_yr_sd"] = stats["sd"]
        bcp_draw = bcp_tc.get(code, np.array([np.nan])) * (12 / 44)
        bcp_stats = summarize(bcp_draw)
        out.loc[pos, "bcp_sequestration_tc_yr"] = bcp_stats["mean"]
        physical_draws = coastal + bcp_draw
        stats = summarize(physical_draws)
        out.loc[pos, "total_bcseq_tc_yr_mean"] = stats["mean"]
        out.loc[pos, "total_bcseq_tc_yr_sd"] = stats["sd"]
        for account, draws in [
            ("coastal_bcw_usd2015_yr", coastal * np.asarray(gscc, dtype=np.float64)),
            ("ocean_bcw_usd2015_yr", bcp_draw * np.asarray(gscc, dtype=np.float64)),
            ("bcw_usd2015_yr", blue_usd.get(code, np.array([np.nan]))),
        ]:
            stats = summarize(draws)
            for stat in STATS:
                out.loc[pos, f"{account}_{stat}"] = stats[stat]
    out["bcw_flux_inputs_complete"] = pd.NA
    for pos in out.index[summary]:
        out.loc[pos, "bcw_flux_inputs_complete"] = bool(entity.loc[str(row_to_entity.loc[pos]), "bcw_flux_inputs_complete"])
    return out


def build_02_gcw(master: pd.DataFrame, gcw_archive: np.lib.npyio.NpzFile) -> pd.DataFrame:
    out = pd.DataFrame({
        "unit_code": master["UNIT_CODE"], "iso3": master["ISO3"],
        "name": master["name"], "sovereign": master["sovereign"], "m49": master["m49"],
        "region": master["region"], "fra_region": master["fra_region"],
        "fra_subregion": master["fra_subregion"], "economic_group": master["groups"],
        "documented_forest_mangrove_area_ha": master["documented_forest_mangrove_area_ha"],
        "forest_area_total_ha": master["forest_area_allocated_total_ha"],
    })
    for biome in BIOMES:
        out[f"forest_share_{biome}"] = master[f"forest_biome_share_{biome}"]
    for biome in BIOMES:
        out[f"forest_area_{biome}_ha"] = master[f"forest_area_allocated_{biome}_ha"]
    for biome in BIOMES:
        out[f"forest_additions_{biome}_tc_yr"] = master[f"forest_additions_{biome}_tC_yr"]
        out[f"forest_additions_{biome}_tco2_yr"] = master[f"forest_additions_{biome}_tCO2_yr"]
    out["forest_additions_total_tc_yr"] = master["forest_additions_from_area_rates_tC_yr"]
    out["forest_additions_total_tco2_yr"] = master["forest_additions_from_area_rates_tCO2_yr"]
    gcw = draw_lookup(gcw_archive, "gcw_usd2015_yr")
    low = draw_lookup(gcw_archive, "gcw_spatial_sd_low_usd2015_yr")
    high = draw_lookup(gcw_archive, "gcw_spatial_sd_high_usd2015_yr")
    count = int(gcw_archive["gcw_usd2015_yr"].shape[1])
    statistics = summary_rows(gcw, master["iso3"].astype(str), count)
    for stat in STATS:
        out[f"gcw_usd2015_yr_{stat}"] = [item[stat] for item in statistics]
    out["gcw_spatial_sd_low_usd2015_yr_mean"] = [np.mean(low[code]) if code in low and np.isfinite(low[code]).any() else np.nan for code in master["iso3"].astype(str)]
    out["gcw_spatial_sd_high_usd2015_yr_mean"] = [np.mean(high[code]) if code in high and np.isfinite(high[code]).any() else np.nan for code in master["iso3"].astype(str)]
    out["gcw_status"] = np.where(master["has_gcw"].fillna(False), "available", "missing")
    return out


def build_03_ncw(master: pd.DataFrame, ncw_archive: np.lib.npyio.NpzFile,
                 gcw_archive: np.lib.npyio.NpzFile) -> pd.DataFrame:
    out = pd.DataFrame({
        "unit_code": master["UNIT_CODE"], "iso3": master["ISO3"],
        "country_or_territory": master["name"], "sovereign": master["sovereign"],
        "un_m49_code": master["m49"], "region": master["region"],
        "fra_region": master["fra_region"], "fra_subregion": master["fra_subregion"],
        "economic_group": master["groups"], "unit_class": master["unit_class"],
        "population": master["population_2024"], "population_year": master["population_source_year"],
        "gdp_usd2015_yr": master["gdp_2015usd_2024"], "gdp_year": master["gdp_source_year"],
        "gdp_per_capita_usd2015_person": master["gdp_per_capita_2024"],
        "co2_emissions_2024": master["co2_emissions_tco2_2024"],
        "eez_area_km2": master["bcw_source_eez_area_km2"],
        "forest_area_total_ha": master["forest_area_allocated_total_ha"],
    })
    for biome in BIOMES:
        out[f"forest_share_{biome}"] = master[f"forest_biome_share_{biome}"]
    for biome in BIOMES:
        out[f"forest_area_{biome}_ha"] = master[f"forest_area_allocated_{biome}_ha"]
    marine_area_map = {
        "saltmarsh_area_ha": ("saltmarsh_area_km2_hilmi_source", 100.0),
        "seagrass_area_ha": ("seagrass_area_km2_hilmi_source", 100.0),
        "mangrove_area_ha": ("mangrove_area_selected_ha", 1.0),
    }
    for output, (source, scale) in marine_area_map.items():
        out[output] = pd.to_numeric(master[source], errors="coerce") * scale
    out["bce_area_total_ha"] = out[["saltmarsh_area_ha", "seagrass_area_ha", "mangrove_area_ha"]].sum(axis=1, min_count=1)

    for biome in BIOMES:
        out[f"forest_additions_{biome}_tc_yr"] = master[f"forest_additions_{biome}_tC_yr"]
        out[f"forest_additions_{biome}_tco2_yr"] = master[f"forest_additions_{biome}_tCO2_yr"]
    out["forest_additions_total_tc_yr"] = master["forest_additions_from_area_rates_tC_yr"]
    physical_gcw = draw_lookup(gcw_archive, "uptake_tco2_yr")
    draw_count = int(ncw_archive["ncw_usd2015_yr"].shape[1])
    physical_stats = summary_rows(physical_gcw, master["iso3"].astype(str), draw_count)
    for stat in STATS:
        out[f"forest_additions_total_tco2_yr_{stat}"] = [item[stat] for item in physical_stats]
    out = out.copy()

    component_keys = {
        "saltmarsh": "saltmarsh_tco2_yr",
        "seagrass": "seagrass_tco2_yr",
        "mangrove": "selected_mangrove_tco2_yr",
        "bcp": "bcp_tco2_yr",
    }
    component_draws = {name: draw_lookup(ncw_archive, key) for name, key in component_keys.items()}
    codes = master["iso3"].astype(str).tolist()
    coast = {}
    blue = {}
    green = physical_gcw
    combined = {}
    for code in codes:
        arrays = {name: component_draws[name].get(code, np.array([np.nan])) for name in component_keys}
        for name in BCES:
            draws = arrays[name] * (12.0 / 44.0)
            # Component summaries are assigned from the draw lookup below.
        coast_components = np.vstack([arrays[name] for name in BCES])
        coast_draw = np.nansum(coast_components, axis=0)
        coast_draw[np.all(~np.isfinite(coast_components), axis=0)] = np.nan
        blue_draw = np.nansum(np.vstack([coast_draw, arrays["bcp"]]), axis=0)
        blue_draw[np.all(~np.isfinite(np.vstack([coast_draw, arrays["bcp"]])), axis=0)] = np.nan
        green_draw = physical_gcw.get(code, np.full(ncw_archive["ncw_usd2015_yr"].shape[1], np.nan))
        combined_components = np.vstack([green_draw, blue_draw])
        combined_draw = np.nansum(combined_components, axis=0)
        combined_draw[np.all(~np.isfinite(combined_components), axis=0)] = np.nan
        coast[code], blue[code], combined[code] = coast_draw, blue_draw, combined_draw

    component_stats = {
        name: summary_rows(component_draws[name], codes, draw_count)
        for name in BCES
    }
    for name in BCES:
        for unit in ("tc", "tco2"):
            factor = (12.0 / 44.0) if unit == "tc" else 1.0
            for stat in STATS:
                out[f"bce_sequestration_{name}_{unit}_yr_{stat}"] = [item[stat] * factor for item in component_stats[name]]
    for group_name, lookup in [("bce_sequestration_total", coast), ("blue_sequestration_total", blue),
                               ("combined_removals", combined)]:
        for unit in ("tc", "tco2"):
            factor = (12.0 / 44.0) if unit == "tc" else 1.0
            group_stats = [summarize(lookup[code]) for code in codes]
            for stat in STATS:
                out[f"{group_name}_{unit}_yr_{stat}"] = [item[stat] * factor for item in group_stats]
    bcp_lookup = component_draws["bcp"]
    for unit in ("tc", "tco2"):
        factor = (12.0 / 44.0) if unit == "tc" else 1.0
        bcp_stats = summary_rows(bcp_lookup, codes, draw_count)
        for stat in STATS:
            out[f"bcp_sequestration_{unit}_yr_{stat}"] = [item[stat] * factor for item in bcp_stats]

    monetary = {name: draw_lookup(ncw_archive, key) for name, key in {
        "gcw": "gcw_usd2015_yr", "bcw": "bcw_usd2015_yr", "ncw": "ncw_usd2015_yr",
    }.items()}
    for account, lookup in monetary.items():
        account_stats = summary_rows(lookup, codes, draw_count)
        for stat in STATS:
            out[f"{account}_usd2015_yr_{stat}"] = [item[stat] for item in account_stats]
    out = out.copy()
    out["has_gcw"] = master["has_gcw"]
    out["has_bcw"] = master["has_bcw"]
    out["bcw_flux_inputs_complete"] = master["bcw_flux_inputs_complete"]
    out["ncw_status"] = np.select(
        [master["has_gcw"].fillna(False) & master["has_bcw"].fillna(False),
         master["has_gcw"].fillna(False), master["has_bcw"].fillna(False)],
        ["both_accounts", "gcw_only", "bcw_only"], default="no_account",
    )
    pop = pd.to_numeric(out["population"], errors="coerce").replace(0, np.nan)
    gdp = pd.to_numeric(out["gdp_usd2015_yr"], errors="coerce").replace(0, np.nan)
    for account in ("gcw", "bcw", "ncw"):
        out[f"{account}_per_capita_usd2015_yr"] = out[f"{account}_usd2015_yr_mean"] / pop
        for stat in STATS:
            out[f"{account}_share_of_gdp_{stat}"] = out[f"{account}_usd2015_yr_{stat}"] / gdp
    gcw_draws_by_entity = monetary["gcw"]
    ncw_draws_by_entity = monetary["ncw"]
    gcw_ncw_ratio_stats = []
    for code in codes:
        numerator = gcw_draws_by_entity.get(code, np.full(draw_count, np.nan))
        denominator = ncw_draws_by_entity.get(code, np.full(draw_count, np.nan))
        ratio = np.divide(
            numerator, denominator,
            out=np.full(draw_count, np.nan, dtype=np.float64),
            where=np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0),
        )
        gcw_ncw_ratio_stats.append(summarize(ratio))
    for stat in STATS:
        out[f"gcw_share_of_ncw_{stat}"] = [item[stat] for item in gcw_ncw_ratio_stats]
        emissions = pd.to_numeric(out["co2_emissions_2024"], errors="coerce").replace(0, np.nan)
        out[f"forest_additions_to_emissions_ratio_{stat}"] = out[f"forest_additions_total_tco2_yr_{stat}"] / emissions
        out[f"combined_removals_to_emissions_ratio_{stat}"] = out[f"combined_removals_tco2_yr_{stat}"] / emissions
    out["allocation_2pct_gcw_usd2015_yr"] = master["our_2pct_gcw_allocation_usd2015_yr"]
    loss = read_csv(VALIDATION / "deforestation_capacity_country_rate.csv")
    loss = loss.drop_duplicates("UNIT_CODE").set_index("UNIT_CODE")
    out["deforestation_period"] = master["UNIT_CODE"].map(loss["loss_period_selected"])
    out["annual_deforestation_ha_yr"] = master["UNIT_CODE"].map(loss["loss_area_ha_yr"])
    out["lost_capacity_tco2_yr"] = master["loss_tco2_mean"]
    for stat, source in [("mean", "loss_value_usd2015_yr_mean"), ("p05", "loss_value_usd2015_yr_p05"), ("p95", "loss_value_usd2015_yr_p95")]:
        out[f"lost_value_usd2015_yr_{stat}"] = master[source]
    out["erosion_pct_of_gcw"] = master["erosion_pct_of_gcw"]
    out["restoration_target_discounted_30yr_tco2"] = master["target_discounted_30yr_tco2"]
    out["restoration_available_discounted_30yr_tco2"] = master["available_discounted_tco2"]
    out["restoration_target_coverage_pct"] = master["target_coverage_pct"]
    out["restoration_marginal_cost_usd2015_tco2"] = master["marginal_effective_cost_usd2015_per_discounted_tco2"]
    out["restoration_cost_net_usd2015"] = master["net_economic_cost_pv_usd2015"]
    out["restoration_status"] = master["busch_scenario_status"]
    return out


def build_04_deforestation(master: pd.DataFrame) -> pd.DataFrame:
    loss = read_csv(VALIDATION / "deforestation_capacity_country_rate.csv")
    wanted = [
        "UNIT_CODE", "ISO3", "name", "region", "groups", "reported_deforestation",
        "loss_period_selected", "loss_area_2010_2015_ha_yr", "loss_area_2015_2020_ha_yr",
        "loss_area_2020_2025_ha_yr", "loss_area_ha_yr", "forest_area_total_ha",
        "forest_rate_tco2_ha_yr", "loss_tco2_mean", "loss_spatial_sd_low_tco2_yr",
        "loss_spatial_sd_high_tco2_yr", "loss_usd_mean", "loss_usd_p05", "loss_usd_p95",
        "erosion_pct_of_gcw", "loss_pct_of_gdp",
    ]
    loss_columns = [column for column in wanted if column in loss and column not in {
        "ISO3", "name", "region", "groups", "reported_deforestation",
    }]
    out = master[["UNIT_CODE", "ISO3", "name", "region", "groups", "reported_deforestation"]].merge(
        loss[loss_columns], on="UNIT_CODE", how="left", validate="one_to_one",
    )
    out = out.rename(columns={
        "UNIT_CODE": "unit_code", "ISO3": "iso3", "name": "country_or_territory",
        "groups": "economic_group", "loss_period_selected": "deforestation_period",
        "loss_area_ha_yr": "annual_deforestation_ha_yr",
        "loss_tco2_mean": "lost_capacity_tco2_yr",
        "loss_usd_mean": "lost_value_usd2015_yr_mean",
        "loss_usd_p05": "lost_value_usd2015_yr_p05", "loss_usd_p95": "lost_value_usd2015_yr_p95",
    })
    master_index = master.set_index("UNIT_CODE")
    out["forest_area_total_ha"] = out["unit_code"].map(master_index["forest_area_allocated_total_ha"])
    forest_rate = master_index["uptake_tco2_yr_mean"] / master_index["forest_area_allocated_total_ha"].replace(0, np.nan)
    out["forest_rate_tco2_ha_yr"] = out["unit_code"].map(forest_rate)
    # Keep the established README field names alongside the period-specific
    # fields used to show every FRA reporting period.
    out["name"] = out["country_or_territory"]
    out["fra_deforestation_rate_1000ha_yr"] = out["annual_deforestation_ha_yr"] / 1000.0
    out["gcw_average_rate_tco2_ha_yr"] = out["forest_rate_tco2_ha_yr"]
    out["scenario"] = "latest_available_fra_period"
    out["data_status"] = np.where(out["reported_deforestation"].eq(True), "reported", "not_reported")
    return out


def build_05_restoration(master: pd.DataFrame) -> pd.DataFrame:
    scenario_country = read_csv(DERIVED / "busch_reconstruction" / "busch_all_dta_soil_sensitivity_country.csv")
    scenario_coverage = read_csv(DERIVED / "busch_reconstruction" / "busch_all_dta_soil_sensitivity_coverage.csv")
    key_columns = ["iso3", "soil_scenario"]
    if scenario_coverage.duplicated(key_columns).any():
        raise ValueError("The Busch soil-sensitivity coverage file has duplicate entity/scenario rows.")
    scenarios = scenario_country[[
        "iso3", "soil_scenario", "nr_soil_rate_tC_ha_yr",
        "plantation_soil_rate_tC_ha_yr", "natural_regeneration_cells_selected",
        "plantation_cells_selected", "method_switches_vs_reference", "available_discounted_tco2",
    ]]
    coverage_fields = [
        "iso3", "soil_scenario", "target_coverage_pct", "priced_cells", "status",
        "marginal_effective_cost_usd2015_per_discounted_tco2", "net_economic_cost_pv_usd2015",
        "positive_project_cost_pv_usd2015", "uniform_carbon_payment_pv_usd2015",
        "net_economic_cost_annual_usd2015", "positive_project_cost_annual_usd2015",
        "uniform_carbon_payment_annual_usd2015",
    ]
    scenario_costs = scenario_coverage[[column for column in coverage_fields if column in scenario_coverage]]
    entities = master[[
        "UNIT_CODE", "iso3", "name", "region", "groups", "reported_deforestation",
        "loss_tco2_mean", "our_2pct_gcw_allocation_usd2015_yr", "target_discounted_30yr_tco2",
    ]].copy()
    entities = entities.rename(columns={
        "UNIT_CODE": "unit_code", "name": "country_or_territory",
        "groups": "economic_group", "loss_tco2_mean": "annual_lost_capacity_tco2_yr",
        "our_2pct_gcw_allocation_usd2015_yr": "allocation_2pct_gcw_usd2015_yr",
        "target_discounted_30yr_tco2": "restoration_target_discounted_30yr_tco2",
    })
    scenario_names = sorted(scenarios["soil_scenario"].dropna().unique())
    expanded = entities.assign(_join=1).merge(
        pd.DataFrame({"soil_scenario": scenario_names, "_join": 1}), on="_join", how="inner"
    ).drop(columns="_join")
    out = expanded.merge(scenarios, on=key_columns, how="left", validate="one_to_one")
    out = out.merge(scenario_costs, on=key_columns, how="left", validate="one_to_one")
    out = out.rename(columns={
        "available_discounted_tco2": "available_discounted_30yr_tco2",
        "marginal_effective_cost_usd2015_per_discounted_tco2": "restoration_marginal_cost_usd2015_tco2",
        "net_economic_cost_pv_usd2015": "restoration_cost_net_pv_usd2015",
        "positive_project_cost_pv_usd2015": "restoration_cost_positive_pv_usd2015",
        "uniform_carbon_payment_pv_usd2015": "restoration_cost_uniform_pv_usd2015",
        "net_economic_cost_annual_usd2015": "restoration_cost_net_annual_usd2015",
        "positive_project_cost_annual_usd2015": "restoration_cost_positive_annual_usd2015",
        "uniform_carbon_payment_annual_usd2015": "restoration_cost_uniform_annual_usd2015",
        "status": "restoration_status",
    })
    # These aliases are part of the selected table dictionary; keep them in
    # sync with the more explicit method-specific fields above.
    out["name"] = out["country_or_territory"]
    out["soil_rate_tc_ha_yr"] = out["nr_soil_rate_tC_ha_yr"]
    out["target_discounted_30yr_tco2"] = out["restoration_target_discounted_30yr_tco2"]
    out["selected_cells"] = out[[
        "natural_regeneration_cells_selected", "plantation_cells_selected",
    ]].sum(axis=1, min_count=1)
    out["marginal_cost_usd2015_per_tco2"] = out["restoration_marginal_cost_usd2015_tco2"]
    for short, explicit in {
        "net_cost_pv_usd2015": "restoration_cost_net_pv_usd2015",
        "positive_project_cost_pv_usd2015": "restoration_cost_positive_pv_usd2015",
        "uniform_payment_pv_usd2015": "restoration_cost_uniform_pv_usd2015",
        "net_cost_annual_usd2015_yr": "restoration_cost_net_annual_usd2015",
        "positive_project_cost_annual_usd2015_yr": "restoration_cost_positive_annual_usd2015",
        "uniform_payment_annual_usd2015_yr": "restoration_cost_uniform_annual_usd2015",
    }.items():
        out[short] = out[explicit]
    out["status"] = out["restoration_status"]
    return out


def build_06_curves() -> pd.DataFrame:
    folder = DERIVED / "busch_reconstruction"
    price_base = read_csv(folder / "busch_all_dta_25_price_curves.csv")
    price_base.insert(1, "soil_scenario", "busch_reference")
    price_base.insert(2, "curve_type", "price_supply")
    scenario_rates = read_csv(folder / "busch_all_dta_soil_sensitivity_country.csv")
    reference_rates = scenario_rates.loc[
        scenario_rates["soil_scenario"].eq("busch_reference"), ["iso3", "nr_soil_rate_tC_ha_yr"]
    ]
    price_base = price_base.merge(reference_rates, on="iso3", how="left", validate="many_to_one")
    price_sensitivity = read_csv(folder / "busch_all_dta_soil_sensitivity_price_curves.csv")
    price_sensitivity = price_sensitivity[price_sensitivity["soil_scenario"].ne("busch_reference")].copy()
    price_sensitivity.insert(2, "curve_type", "price_supply")

    cost_base = read_csv(folder / "busch_all_dta_effective_cost_curves.csv")
    cost_base.insert(1, "soil_scenario", "busch_reference")
    cost_base.insert(2, "curve_type", "effective_cost")
    cost_base = cost_base.merge(reference_rates, on="iso3", how="left", validate="many_to_one")
    cost_sensitivity = read_csv(folder / "busch_all_dta_soil_sensitivity_effective_cost_curves.csv")
    cost_sensitivity = cost_sensitivity[cost_sensitivity["soil_scenario"].ne("busch_reference")].copy()
    cost_sensitivity.insert(2, "curve_type", "effective_cost")
    curves = pd.concat([price_base, price_sensitivity, cost_base, cost_sensitivity], ignore_index=True, sort=False)
    names = read_csv(folder / "busch_all_dta_soil_sensitivity_coverage.csv")[["iso3", "name"]]
    names = names.drop_duplicates("iso3", keep="first")
    curves = curves.merge(names, on="iso3", how="left", validate="many_to_one")
    curves["quantity_offered_discounted_30yr_tco2"] = curves["cell_supply_discounted_tco2"]
    curves["quantity_cumulative_discounted_30yr_tco2"] = curves[
        "cumulative_supply_discounted_tco2"
    ].combine_first(curves["cumulative_discounted_tco2"])
    curves["cumulative_cost_usd2015"] = curves["cumulative_net_project_cost_pv_usd2015"]
    return curves


def build_07_profiles(ncw: pd.DataFrame, ncw_archive: np.lib.npyio.NpzFile) -> tuple[pd.DataFrame, pd.DataFrame]:
    account_draws = {name: draw_lookup(ncw_archive, key) for name, key in {
        "gcw": "gcw_usd2015_yr", "bcw": "bcw_usd2015_yr", "ncw": "ncw_usd2015_yr",
    }.items()}
    physical_draws = {name: draw_lookup(ncw_archive, key) for name, key in {
        "saltmarsh": "saltmarsh_tco2_yr", "seagrass": "seagrass_tco2_yr",
        "mangrove": "selected_mangrove_tco2_yr", "bcp": "bcp_tco2_yr",
    }.items()}
    draw_count = int(ncw_archive["ncw_usd2015_yr"].shape[1])
    additive = [
        "population", "gdp_usd2015_yr", "co2_emissions_2024", "eez_area_km2",
        "forest_area_total_ha", *[f"forest_area_{b}_ha" for b in BIOMES],
        *[f"{bce}_area_ha" for bce in BCES], "bce_area_total_ha",
        *[f"forest_additions_{b}_tco2_yr" for b in BIOMES],
        "forest_additions_total_tco2_yr_mean",
        *[f"bce_sequestration_{bce}_tco2_yr_mean" for bce in BCES],
        "bce_sequestration_total_tco2_yr_mean", "bcp_sequestration_tco2_yr_mean",
        "blue_sequestration_total_tco2_yr_mean",
        "combined_removals_tco2_yr_mean", "annual_deforestation_ha_yr", "lost_capacity_tco2_yr",
        "lost_value_usd2015_yr_mean", "allocation_2pct_gcw_usd2015_yr", "restoration_target_discounted_30yr_tco2",
        "restoration_available_discounted_30yr_tco2", "restoration_cost_net_usd2015",
    ]
    def aggregate(profile_col: str) -> pd.DataFrame:
        rows = []
        for label, frame in ncw.groupby(profile_col, dropna=False, sort=True):
            row: dict[str, object] = {profile_col: "Unclassified" if pd.isna(label) else label,
                                      "n_entities": int(frame["unit_code"].nunique())}
            for col in additive:
                if col in frame:
                    row[col] = pd.to_numeric(frame[col], errors="coerce").sum(min_count=1)
            forest_total = row.get("forest_area_total_ha", np.nan)
            for biome in BIOMES:
                area = row.get(f"forest_area_{biome}_ha", np.nan)
                row[f"forest_share_{biome}"] = area / forest_total if pd.notna(area) and pd.notna(forest_total) and forest_total else np.nan
                flow = row.get(f"forest_additions_{biome}_tco2_yr", np.nan)
                row[f"forest_additions_{biome}_tc_yr"] = flow / C_TO_CO2 if pd.notna(flow) else np.nan
            forest_flow = row.get("forest_additions_total_tco2_yr_mean", np.nan)
            row["forest_additions_total_tc_yr"] = forest_flow / C_TO_CO2 if pd.notna(forest_flow) else np.nan

            def group_draws(component_names: tuple[str, ...], *, include_forest: bool = False) -> np.ndarray:
                arrays = [
                    physical_draws[name].get(code, np.full(draw_count, np.nan))
                    for code in frame["unit_code"].astype(str)
                    for name in component_names
                ]
                if include_forest:
                    arrays.extend(
                        np.full(draw_count, value, dtype=np.float64)
                        for value in pd.to_numeric(
                            frame["forest_additions_total_tco2_yr_mean"], errors="coerce"
                        )
                    )
                stacked = np.vstack(arrays) if arrays else np.full((0, draw_count), np.nan)
                total = np.nansum(stacked, axis=0)
                total[np.all(~np.isfinite(stacked), axis=0)] = np.nan
                return total

            def add_physical_statistics(prefix: str, values_tco2: np.ndarray) -> None:
                for unit, factor in (("tco2", 1.0), ("tc", 12.0 / 44.0)):
                    for stat, value in summarize(values_tco2 * factor).items():
                        row[f"{prefix}_{unit}_yr_{stat}"] = value

            for bce in BCES:
                add_physical_statistics(
                    f"bce_sequestration_{bce}", group_draws((bce,))
                )
            coastal_draws = group_draws(tuple(BCES))
            add_physical_statistics("bce_sequestration_total", coastal_draws)
            bcp_group_draws = group_draws(("bcp",))
            add_physical_statistics("bcp_sequestration", bcp_group_draws)
            blue_components = np.vstack([coastal_draws, bcp_group_draws])
            blue_group_draws = np.nansum(blue_components, axis=0)
            blue_group_draws[np.all(~np.isfinite(blue_components), axis=0)] = np.nan
            add_physical_statistics("blue_sequestration_total", blue_group_draws)
            forest_group_draws = group_draws((), include_forest=True)
            combined_components = np.vstack([forest_group_draws, blue_group_draws])
            combined_group_draws = np.nansum(combined_components, axis=0)
            combined_group_draws[np.all(~np.isfinite(combined_components), axis=0)] = np.nan
            add_physical_statistics("combined_removals", combined_group_draws)
            pop = row.get("population", np.nan)
            gdp = row.get("gdp_usd2015_yr", np.nan)
            for account in ("gcw", "bcw", "ncw"):
                draws = [account_draws[account].get(code, np.full(draw_count, np.nan))
                         for code in frame["unit_code"].astype(str)]
                if draws:
                    stacked = np.vstack(draws)
                    total = np.nansum(stacked, axis=0)
                    total[np.all(~np.isfinite(stacked), axis=0)] = np.nan
                    for stat, value in summarize(total).items():
                        row[f"{account}_usd2015_yr_{stat}"] = value
                    row[f"{account}_per_capita_usd2015_yr"] = row[f"{account}_usd2015_yr_mean"] / pop if pd.notna(pop) and pop else np.nan
                    for stat in STATS:
                        row[f"{account}_share_of_gdp_{stat}"] = row[f"{account}_usd2015_yr_{stat}"] / gdp if pd.notna(gdp) and gdp else np.nan
            draw_totals: dict[str, np.ndarray] = {}
            for account in ("gcw", "bcw", "ncw"):
                arrays = [account_draws[account].get(code, np.full(draw_count, np.nan))
                          for code in frame["unit_code"].astype(str)]
                stacked = np.vstack(arrays)
                total = np.nansum(stacked, axis=0)
                total[np.all(~np.isfinite(stacked), axis=0)] = np.nan
                draw_totals[account] = total
            for stat, value in summarize(draw_totals["gcw"] / draw_totals["ncw"]).items():
                row[f"gcw_share_of_ncw_{stat}"] = value
            emissions = row.get("co2_emissions_2024", np.nan)
            if pd.notna(emissions) and emissions != 0:
                for stat, value in summarize(forest_group_draws / emissions).items():
                    row[f"forest_additions_to_emissions_ratio_{stat}"] = value
                for stat, value in summarize(combined_group_draws / emissions).items():
                    row[f"combined_removals_to_emissions_ratio_{stat}"] = value
                row["forest_additions_to_emissions_ratio"] = row["forest_additions_to_emissions_ratio_mean"]
                row["combined_removals_to_emissions_ratio"] = row["combined_removals_to_emissions_ratio_mean"]
            else:
                for stat in STATS:
                    row[f"forest_additions_to_emissions_ratio_{stat}"] = np.nan
                    row[f"combined_removals_to_emissions_ratio_{stat}"] = np.nan
                row["forest_additions_to_emissions_ratio"] = np.nan
                row["combined_removals_to_emissions_ratio"] = np.nan
            row["erosion_pct_of_gcw"] = 100 * row.get("lost_value_usd2015_yr_mean", np.nan) / row.get("gcw_usd2015_yr_mean", np.nan) if row.get("gcw_usd2015_yr_mean", 0) else np.nan
            row["gdp_per_capita_usd2015_person"] = gdp / pop if pd.notna(gdp) and pd.notna(pop) and pop else np.nan
            for status_col, output_col in [
                ("has_gcw", "units_with_gcw"), ("has_bcw", "units_with_bcw"),
                ("has_both", "units_with_both_accounts"), ("has_gdp", "units_with_gdp"),
                ("has_co2_emissions_2024", "units_with_co2_emissions_2024"),
                ("has_forest_account", "units_with_forest_account"), ("has_blue_account", "units_with_blue_account"),
                ("has_deforestation", "units_with_deforestation"), ("has_restoration", "units_with_restoration"),
                ("bcw_flux_inputs_complete", "units_with_complete_bcw_flux_inputs"),
            ]:
                source_col = status_col
                if source_col == "has_both":
                    values = frame["has_gcw"].fillna(False).astype(bool) & frame["has_bcw"].fillna(False).astype(bool)
                elif source_col == "has_gdp":
                    values = frame["gdp_usd2015_yr"].notna()
                elif source_col == "has_co2_emissions_2024":
                    values = frame["co2_emissions_2024"].notna()
                elif source_col == "has_forest_account":
                    values = frame["forest_additions_total_tco2_yr_mean"].notna()
                elif source_col == "has_blue_account":
                    values = frame["bcw_usd2015_yr_mean"].notna()
                elif source_col == "has_deforestation":
                    values = frame["annual_deforestation_ha_yr"].notna()
                elif source_col == "has_restoration":
                    values = frame["restoration_target_discounted_30yr_tco2"].notna()
                else:
                    values = frame[source_col].fillna(False).astype(bool)
                row[output_col] = int(values.sum())
            for year in (2024, 2023, 2022):
                row[f"units_with_gdp_{year}"] = int(frame["gdp_year"].eq(year).sum())
            for status in ("both_accounts", "gcw_only", "bcw_only", "no_account"):
                row[f"units_by_ncw_status_{status}"] = int(frame["ncw_status"].eq(status).sum())
            row["units_with_deforestation_period"] = int(frame["deforestation_period"].notna().sum())
            periods = sorted(frame["deforestation_period"].dropna().astype(str).unique())
            row["deforestation_periods"] = ", ".join(periods) if periods else pd.NA
            for period in ("2010-2015", "2015-2020", "2020-2025"):
                encoded = period.replace("-", "_")
                row[f"units_with_deforestation_period_{encoded}"] = int(frame["deforestation_period"].eq(period).sum())
            both_accounts = frame["has_gcw"].fillna(False).astype(bool) & frame["has_bcw"].fillna(False).astype(bool)
            row["green_dominant_units"] = int((both_accounts & frame["gcw_usd2015_yr_mean"].gt(frame["bcw_usd2015_yr_mean"])).sum())
            row["blue_dominant_units"] = int((both_accounts & frame["bcw_usd2015_yr_mean"].gt(frame["gcw_usd2015_yr_mean"])).sum())
            row["mixed_units"] = int((both_accounts & frame["bcw_usd2015_yr_mean"].eq(frame["gcw_usd2015_yr_mean"])).sum())
            row["restoration_reached_units"] = int(frame["restoration_target_coverage_pct"].ge(100).sum())
            row["restoration_partially_reached_units"] = int(frame["restoration_target_coverage_pct"].between(0, 100, inclusive="left").sum())
            row["restoration_not_quantifiable_units"] = int(frame["restoration_target_coverage_pct"].isna().sum())
            restoration_target = row.get("restoration_target_discounted_30yr_tco2", np.nan)
            restoration_supply = row.get("restoration_available_discounted_30yr_tco2", np.nan)
            row["restoration_target_coverage_pct"] = 100 * restoration_supply / restoration_target if pd.notna(restoration_target) and restoration_target else np.nan
            row["median_restoration_marginal_cost_usd2015_tco2"] = pd.to_numeric(frame["restoration_marginal_cost_usd2015_tco2"], errors="coerce").median()
            rows.append(row)
        result = pd.DataFrame(rows)
        # Put all coverage counters last, as requested for the profiles.
        coverage_cols = [c for c in result if c.startswith(("units_with_", "units_by_", "green_dominant_", "blue_dominant_", "mixed_", "restoration_reached_", "restoration_partially_", "restoration_not_"))]
        other = [c for c in result if c not in coverage_cols]
        return result[other + coverage_cols]
    return aggregate("region"), aggregate("economic_group")


def build_08_global(ncw: pd.DataFrame, gcw_archive: np.lib.npyio.NpzFile,
                    ncw_archive: np.lib.npyio.NpzFile) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    # Draw archives use the pipeline entity key, which also covers territories
    # without a standard ISO3 code; keep ISO3 blank for those records in outputs.
    codes = ncw["unit_code"].astype(str).tolist()
    draw_count = int(ncw_archive["ncw_usd2015_yr"].shape[1])
    gscc = np.asarray(gcw_archive["gscc"], dtype=np.float64)

    def sum_draws(lookup: dict[str, np.ndarray]) -> np.ndarray:
        arrays = [lookup.get(code, np.full(draw_count, np.nan)) for code in codes]
        matrix = np.vstack(arrays)
        total = np.nansum(matrix, axis=0)
        total[np.all(~np.isfinite(matrix), axis=0)] = np.nan
        return total

    def add(component: str, area_col: str | None = None, flow_col: str | None = None,
            flow_lookup: dict[str, np.ndarray] | None = None,
            account_lookup: dict[str, np.ndarray] | None = None,
            n_mask: pd.Series | None = None) -> None:
        row: dict[str, object] = {
            "scope": "world", "component": component,
            "biome_or_bce": component if component in {*BIOMES, *BCES, "bcp"} else pd.NA,
            "n_entities": int(ncw["unit_code"].nunique()),
            "n_entities_with_data": int(n_mask.sum()) if n_mask is not None else (
                int(ncw[area_col].notna().sum()) if area_col else int(ncw[flow_col].notna().sum()) if flow_col else np.nan
            ),
            "area_ha": pd.to_numeric(ncw[area_col], errors="coerce").sum(min_count=1) if area_col else np.nan,
        }
        row["area_km2"] = row["area_ha"] / 100.0 if pd.notna(row["area_ha"]) else np.nan
        if flow_lookup is not None:
            physical = sum_draws(flow_lookup)
        elif flow_col:
            total = pd.to_numeric(ncw[flow_col], errors="coerce").sum(min_count=1)
            physical = np.full(draw_count, total, dtype=np.float64)
        else:
            physical = None
        if physical is not None:
            for stat, value in summarize(physical * (12.0 / 44.0)).items():
                row[f"sequestration_tc_yr_{stat}"] = value
            for stat, value in summarize(physical).items():
                row[f"sequestration_tco2_yr_{stat}"] = value
        if account_lookup is not None:
            wealth = sum_draws(account_lookup)
        elif physical is not None:
            wealth = physical * gscc
        else:
            wealth = None
        if wealth is not None:
            for stat, value in summarize(wealth).items():
                row[f"wealth_usd2015_yr_{stat}"] = value
        rows.append(row)

    # Component rows by forest biome.
    for biome in BIOMES:
        add(biome, f"forest_area_{biome}_ha", f"forest_additions_{biome}_tco2_yr")
    # Component rows by coastal BCE plus the open-ocean pump.
    component_keys = {
        "saltmarsh": "saltmarsh_tco2_yr", "seagrass": "seagrass_tco2_yr",
        "mangrove": "selected_mangrove_tco2_yr", "bcp": "bcp_tco2_yr",
    }
    component_draws = {name: draw_lookup(ncw_archive, key) for name, key in component_keys.items()}
    for bce in BCES:
        add(bce, f"{bce}_area_ha", flow_lookup=component_draws[bce],
            n_mask=ncw[f"bce_sequestration_{bce}_tco2_yr_mean"].notna())
    add("bcp", flow_lookup=component_draws["bcp"],
        n_mask=ncw["bcp_sequestration_tco2_yr_mean"].notna())
    coastal = {}
    for code in codes:
        matrix = np.vstack([component_draws[name][code] for name in BCES])
        total = np.nansum(matrix, axis=0)
        total[np.all(~np.isfinite(matrix), axis=0)] = np.nan
        coastal[code] = total
    add("coastal_bce_total", "bce_area_total_ha", flow_lookup=coastal,
        n_mask=ncw["bce_sequestration_total_tco2_yr_mean"].notna())
    blue = {}
    for code in codes:
        matrix = np.vstack([coastal[code], component_draws["bcp"][code]])
        total = np.nansum(matrix, axis=0)
        total[np.all(~np.isfinite(matrix), axis=0)] = np.nan
        blue[code] = total
    add("blue_physical_total", "bce_area_total_ha", flow_lookup=blue,
        n_mask=ncw["blue_sequestration_total_tco2_yr_mean"].notna())
    green = draw_lookup(gcw_archive, "uptake_tco2_yr")
    green_wealth = draw_lookup(ncw_archive, "gcw_usd2015_yr")
    blue_wealth = draw_lookup(ncw_archive, "bcw_usd2015_yr")
    ncw_wealth = draw_lookup(ncw_archive, "ncw_usd2015_yr")
    add("green_carbon_wealth", "forest_area_total_ha", flow_lookup=green,
        account_lookup=green_wealth, n_mask=ncw["has_gcw"].fillna(False).astype(bool))
    add("blue_carbon_wealth", "bce_area_total_ha", flow_lookup=draw_lookup(ncw_archive, "bcw_sequestration_tco2_yr"),
        account_lookup=blue_wealth, n_mask=ncw["has_bcw"].fillna(False).astype(bool))
    combined_physical = {}
    for code in codes:
        matrix = np.vstack([green.get(code, np.full(draw_count, np.nan)), blue[code]])
        total = np.nansum(matrix, axis=0)
        total[np.all(~np.isfinite(matrix), axis=0)] = np.nan
        combined_physical[code] = total
    add("combined_physical_removals", flow_lookup=combined_physical,
        n_mask=ncw["combined_removals_tco2_yr_mean"].notna())
    add("natural_carbon_wealth", account_lookup=ncw_wealth,
        n_mask=ncw["ncw_status"].ne("no_account"))
    ncw_mean = rows[-1].get("wealth_usd2015_yr_mean", np.nan)
    for row in rows:
        value = row.get("wealth_usd2015_yr_mean", np.nan)
        row["share_of_ncw_pct"] = 100.0 * value / ncw_mean if pd.notna(value) and pd.notna(ncw_mean) and ncw_mean else np.nan
    return pd.DataFrame(rows)


def build_09_spatial() -> pd.DataFrame:
    sources = {
        "spatial_emissions_2024_model_fit.csv": "model_fit",
        "spatial_emissions_2024_model_coefficients.csv": "coefficient",
        "spatial_emissions_2024_focus_coefficients.csv": "focus_coefficient",
        "spatial_emissions_2024_model_selection_evidence.csv": "selection_evidence",
        "spatial_emissions_2024_step1_moran.csv": "moran_diagnostic",
        "spatial_emissions_2024_step2_lm_tests.csv": "lm_diagnostic",
        "spatial_emissions_2024_step3_nested_tests.csv": "nested_model_test",
        "spatial_emissions_2024_predictor_block_tests.csv": "predictor_block_test",
        "spatial_emissions_2024_predictor_correlations.csv": "predictor_correlation",
        "spatial_emissions_2024_predictor_vif.csv": "predictor_vif",
        "spatial_emissions_2024_sample_audit.csv": "sample_audit",
        "spatial_sequence_model_fit.csv": "model_fit",
        "spatial_sequence_model_coefficients.csv": "coefficient",
        "spatial_sequence_step1_moran.csv": "moran_diagnostic",
        "spatial_sequence_step2_lm_tests.csv": "lm_diagnostic",
        "spatial_sequence_step3_nested_tests.csv": "nested_model_test",
        "spatial_sequence_sample_audit.csv": "sample_audit",
        "spatial_model_decision_template.csv": "decision_template",
    }
    rows = []
    for filename, result_type in sources.items():
        path = VALIDATION / filename
        if not path.is_file():
            continue
        frame = pd.read_csv(path, low_memory=False)
        for record in frame.to_dict("records"):
            def first(*names):
                for name in names:
                    value = record.get(name)
                    if value is not None and pd.notna(value):
                        return value
                return np.nan
            rows.append({
                "result_type": result_type, "source_file": filename,
                "specification": first("specification"),
                "outcome": first("outcome", "outcome_sample"),
                "w_id": first("weight", "w_id"),
                "model": first("model"), "selected_model": first("final_model_selected"),
                "comparison": first("comparison", "restricted_specification", "test"),
                "term": first("term", "predictor", "predictor_1"),
                "estimate": first("coefficient", "estimate", "moran_i", "lr_statistic", "statistic"),
                "std_error": first("std_error_ml", "std_error"),
                "p_value": first("p_value", "p_wald_ml", "p_permutation_two_sided"),
                "ci_lower": first("ci_lower"), "ci_upper": first("ci_upper"),
                "effect_type": first("effect_type"),
                "effect_estimate": first("effect_estimate", "direct_effect", "indirect_effect", "total_effect"),
                "effect_std_error": first("effect_std_error"),
                "residual_moran_i": (
                    first("moran_i") if first("measure") == "ols_residual" else first("residual_moran_i")
                ),
                "residual_moran_p": (
                    first("p_permutation_two_sided", "p_randomization")
                    if first("measure") == "ols_residual" else first("residual_moran_p")
                ),
                "heteroskedasticity_p": first("heteroskedasticity_p"),
                "normality_p": first("normality_p"),
                "n_observations": first("n", "sample_n"),
                "log_likelihood": first("log_likelihood"), "aic": first("aic"), "bic": first("bic"),
                "model_status": first("test_status", "covariance_status", "optimizer_success", "status"),
                "details_json": json.dumps(record, ensure_ascii=False, default=str),
            })
    return pd.DataFrame(rows)


def build_10_coverage(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks = [
        ("01", "mapped BCW source records", "01_bcw_hilmi_updated.csv", "account_unit_code", "source BCW records"),
        ("02", "forest account", "02_gcw_by_entity.csv", "gcw_status", "FRA 2025 and Gibbs/GFW"),
        ("03", "NCW account", "03_country_level_ncw.csv", "ncw_status", "BCW and GCW accounts"),
        ("03", "population", "03_country_level_ncw.csv", "population", "World Bank"),
        ("03", "GDP", "03_country_level_ncw.csv", "gdp_usd2015_yr", "World Bank"),
        ("04", "reported forest loss", "04_deforestation_by_entity.csv", "annual_deforestation_ha_yr", "FRA 2025"),
        ("05", "restoration cost", "05_restoration_costs_by_entity.csv", "restoration_marginal_cost_usd2015_tco2", "Busch cell-level reconstruction"),
        ("09", "spatial model results", "09_spatial_model_results.csv", "result_type", "Spatial analysis outputs"),
    ]
    output = []
    for table_id, group, filename, column, source in checks:
        frame = tables[filename]
        expected = len(frame)
        if column == "gcw_status":
            available = int(frame[column].eq("available").sum())
        elif column == "ncw_status":
            available = int(frame[column].ne("no_account").sum())
        else:
            available = int(frame[column].notna().sum()) if column in frame else 0
        pct = 100.0 * available / expected if expected else np.nan
        output.append({
            "table_id": table_id, "variable_group": group, "source": source,
            "expected_records": expected, "records_with_data": available,
            "records_missing": expected - available, "coverage_pct": pct,
            "status": "complete" if available == expected else "partial" if available else "unavailable",
        })
    curves = tables["06_restoration_supply_curves.csv"]
    for curve_type, label, column in [
        ("price_supply", "price-based supply curve points", "cumulative_supply_discounted_tco2"),
        ("effective_cost", "effective-cost curve points", "marginal_effective_cost_usd2015_per_tco2"),
    ]:
        frame = curves.loc[curves["curve_type"].eq(curve_type)]
        expected = len(frame)
        available = int(frame[column].notna().sum())
        output.append({
            "table_id": "06", "variable_group": label,
            "source": "Busch cell-level reconstruction",
            "expected_records": expected, "records_with_data": available,
            "records_missing": expected - available,
            "coverage_pct": 100.0 * available / expected if expected else np.nan,
            "status": "complete" if available == expected else "partial" if available else "unavailable",
        })
    for code, group, sheet, source in [("07", "region profiles", "Region", "Entity identifiers"),
                                       ("07", "economic-group profiles", "Economic group", "Economic-group identifiers")]:
        frame = tables["07_geographic_economic_profiles.xlsx"][sheet]
        available = int(frame.iloc[:, 0].notna().sum())
        output.append({"table_id": code, "variable_group": group, "source": source,
                       "expected_records": len(frame), "records_with_data": available,
                       "records_missing": len(frame) - available,
                       "coverage_pct": 100.0 * available / len(frame) if len(frame) else np.nan,
                       "status": "complete" if available == len(frame) else "partial"})
    return pd.DataFrame(output)


def validate_outputs(outputs: dict[str, pd.DataFrame]) -> None:
    ncw = outputs["03_country_level_ncw.csv"]
    if len(ncw) != 266 or ncw["unit_code"].nunique() != len(ncw):
        raise ValueError(f"03 must contain one row for each of the 266 harmonized entities; got {len(ncw)} rows.")
    source = outputs["01_bcw_hilmi_updated.csv"]
    if len(source) != 296 or source["iso"].nunique() != len(source):
        raise ValueError(f"01 must retain all 296 BCW source records; got {len(source)} rows.")
    profiles = outputs["07_geographic_economic_profiles.xlsx"]
    if not set(profiles).issuperset({"Region", "Economic group"}):
        raise ValueError("07 profile workbook must contain Region and Economic group sheets.")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    master = read_csv(VALIDATION / "country_level_results_master.csv")
    with np.load(DERIVED / "draws" / "ncw_draws.npz", allow_pickle=True) as archive:
        ncw_archive = {key: archive[key] for key in archive.files}
    with np.load(DERIVED / "draws" / "gcw_draws.npz", allow_pickle=True) as archive:
        gcw_archive = {key: archive[key] for key in archive.files}
    ncw_npz = np.load(DERIVED / "draws" / "ncw_draws.npz", allow_pickle=True)
    gcw_npz = np.load(DERIVED / "draws" / "gcw_draws.npz", allow_pickle=True)

    outputs: dict[str, pd.DataFrame] = {}
    outputs["01_bcw_hilmi_updated.csv"] = build_01_bcw(master, ncw_npz, gcw_npz["gscc"])
    outputs["02_gcw_by_entity.csv"] = build_02_gcw(master, gcw_npz)
    outputs["03_country_level_ncw.csv"] = build_03_ncw(master, ncw_npz, gcw_npz)
    outputs["04_deforestation_by_entity.csv"] = build_04_deforestation(master)
    outputs["05_restoration_costs_by_entity.csv"] = build_05_restoration(master)
    outputs["06_restoration_supply_curves.csv"] = build_06_curves()
    region, group = build_07_profiles(outputs["03_country_level_ncw.csv"], ncw_npz)
    outputs["07_geographic_economic_profiles.xlsx"] = {"Region": region, "Economic group": group}
    outputs["08_global_accounts_summary.csv"] = build_08_global(outputs["03_country_level_ncw.csv"], gcw_npz, ncw_npz)
    outputs["09_spatial_model_results.csv"] = build_09_spatial()
    outputs["10_results_coverage.csv"] = build_10_coverage(outputs)
    validate_outputs(outputs)

    for name, frame in outputs.items():
        path = TABLES / name
        if name.endswith(".xlsx"):
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for sheet, sheet_frame in frame.items():
                    sheet_frame.to_excel(writer, sheet_name=sheet, index=False)
        else:
            frame.to_csv(path, index=False, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)} ({len(frame) if isinstance(frame, pd.DataFrame) else sum(len(x) for x in frame.values())} rows)")

    submitted = TABLES / "submitted" / "Supplementary_Table.csv"
    submitted.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TABLES / "03_country_level_ncw.csv", submitted)
    print(f"Wrote {submitted.relative_to(ROOT)} (copy of 03_country_level_ncw.csv)")


if __name__ == "__main__":
    main()
