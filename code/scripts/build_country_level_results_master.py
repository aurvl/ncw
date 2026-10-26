"""Build a joined country-level dataset for the Results drafting workflow.

The table is keyed to the 267 rows in ``results/country_level_ncw.csv``. It joins
the current forest and marine accounts, source-area data, 2024 socioeconomic
data, deforestation outcomes, climate-finance scenarios, and the 2024 emissions
accounting comparison. It keeps component fluxes separate because the forest,
coastal, and open-ocean quantities have different physical boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "results"
VALIDATION = OUTPUT / "validation"
SUMMARY = ROOT / "data" / "derived"
DATE = "2026-10-20"
CARBON_TO_CO2 = 44.0 / 12.0
BIOMES = ("tropical", "subtropical", "temperate", "boreal")


def read_unique_csv(path: Path, key: str = "iso3") -> pd.DataFrame:
    """Read a CSV and require one record per accounting unit."""
    frame = pd.read_csv(path)
    if key not in frame:
        raise KeyError(f"{path} has no {key!r} column")
    duplicated = frame.loc[frame[key].duplicated(), key].astype(str).unique().tolist()
    if duplicated:
        raise ValueError(f"{path} has duplicate {key} values: {duplicated[:10]}")
    return frame


def merge_one_to_one(base: pd.DataFrame, addition: pd.DataFrame, source: str) -> pd.DataFrame:
    """Merge one unit-level table and fail if columns or keys are ambiguous."""
    overlap = (set(base.columns) & set(addition.columns)) - {"iso3"}
    if overlap:
        raise ValueError(f"Column collision while joining {source}: {sorted(overlap)}")
    return base.merge(addition, on="iso3", how="left", validate="one_to_one")


def build_bcw_source_by_unit() -> pd.DataFrame:
    """Aggregate source marine areas and component fluxes using the project crosswalk."""
    raw_path = ROOT / "data" / "raw" / "environmental" / "marine" / "bcw" / "output" / "country_level_bcw.csv"
    raw = pd.read_csv(raw_path)
    raw["bcw_code"] = raw["ISO"].astype("string")
    missing_code_map = {"Joint Regimes": "BCW-JR", "Overlapping Claims": "BCW-OC"}
    missing = raw["bcw_code"].isna()
    raw.loc[missing, "bcw_code"] = raw.loc[missing, "country_name"].map(missing_code_map)
    if raw["bcw_code"].isna().any():
        raise ValueError("A BCW source row has no resolvable code")

    crosswalk = pd.read_csv(ROOT / "data" / "derived" / "bcw_territory_mapping.csv")
    if crosswalk["bcw_code"].duplicated().any():
        raise ValueError("BCW territory crosswalk is not unique by source code")
    mapped = raw.merge(
        crosswalk[["bcw_code", "unit_code"]],
        on="bcw_code",
        how="left",
        validate="one_to_one",
    )
    mapped["unit_code"] = mapped["unit_code"].fillna(mapped["bcw_code"])

    additive_columns = {
        "Area_EEZ_KM2": "bcw_source_eez_area_km2",
        "saltmarshes_area_km2": "saltmarsh_area_km2_hilmi_source",
        "seagrasses_area_km2": "seagrass_area_km2_hilmi_source",
        "mangroves_area_km2": "mangrove_area_km2_hilmi_source",
        "uptake_salt_mean": "saltmarsh_uptake_tC_yr_source_mean",
        "uptake_seag_mean": "seagrass_uptake_tC_yr_source_mean",
        "uptake_mang_mean": "mangrove_uptake_tC_yr_hilmi_source_mean",
        "uptake_total_mean": "coastal_uptake_tC_yr_hilmi_source_mean",
        "BCP Seq (tC)": "open_ocean_bcp_tC_yr_source",
        "Total BCseq": "total_bcw_physical_flux_tC_yr_source",
    }
    grouped = mapped.groupby("unit_code", as_index=False)[list(additive_columns)].sum(min_count=1)
    return grouped.rename(columns={"unit_code": "iso3", **additive_columns})


def build_forest_area_and_rates() -> pd.DataFrame:
    """Pivot FRA/GEZ forest areas and attach Gibbs/GFW non-mangrove rates."""
    area_path = SUMMARY / "forest_area_by_biome.csv"
    area = pd.read_csv(area_path)
    area = area.loc[area["variant"].eq("documented_overlap_removed")].copy()
    if area.duplicated(["iso3", "biome"]).any():
        raise ValueError("Documented-overlap forest areas are not unique by unit and biome")

    wide_area = area.pivot(index="iso3", columns="biome", values="area_ha")
    wide_share = area.pivot(index="iso3", columns="biome", values="share")
    wide_area = wide_area.reindex(columns=BIOMES).add_prefix("forest_area_allocated_").reset_index()
    wide_area = wide_area.rename(
        columns={f"forest_area_allocated_{biome}": f"forest_area_allocated_{biome}_ha" for biome in BIOMES}
    )
    wide_share = wide_share.reindex(columns=BIOMES).add_prefix("forest_biome_share_").reset_index()
    result = wide_area.merge(wide_share, on="iso3", validate="one_to_one")

    source = pd.read_csv(SUMMARY / "gfw_gibbs_biome_rates_non_mangrove.csv")
    if source["biome"].duplicated().any() or set(source["biome"]) != set(BIOMES):
        raise ValueError("Expected one Gibbs/GFW non-mangrove rate for each of four biomes")
    for biome in BIOMES:
        rate = source.loc[source["biome"].eq(biome)].iloc[0]
        area_column = f"forest_area_allocated_{biome}_ha"
        result[f"forest_rate_{biome}_tC_ha_yr"] = float(rate["rate_tc_ha_yr_mean"])
        result[f"forest_rate_{biome}_spatial_sd_tC_ha_yr"] = float(rate["rate_tc_ha_yr_spatial_sd"])
        result[f"forest_additions_{biome}_tC_yr"] = result[area_column] * float(rate["rate_tc_ha_yr_mean"])
        result[f"forest_additions_{biome}_tCO2_yr"] = result[f"forest_additions_{biome}_tC_yr"] * CARBON_TO_CO2
    area_columns = [f"forest_area_allocated_{biome}_ha" for biome in BIOMES]
    tc_columns = [f"forest_additions_{biome}_tC_yr" for biome in BIOMES]
    tco2_columns = [f"forest_additions_{biome}_tCO2_yr" for biome in BIOMES]
    result["forest_area_allocated_total_ha"] = result[area_columns].sum(axis=1, min_count=1)
    result["forest_additions_from_area_rates_tC_yr"] = result[tc_columns].sum(axis=1, min_count=1)
    result["forest_additions_from_area_rates_tCO2_yr"] = result[tco2_columns].sum(axis=1, min_count=1)
    result["forest_warm_biome_share"] = np.where(
        result["forest_area_allocated_total_ha"].gt(0),
        (
            result["forest_area_allocated_tropical_ha"].fillna(0)
            + result["forest_area_allocated_subtropical_ha"].fillna(0)
        )
        / result["forest_area_allocated_total_ha"],
        np.nan,
    )
    return result


def build_gmw_mangrove_flux() -> pd.DataFrame:
    """Summarise GMW-2025 mangrove carbon additions from the applied rate draws."""
    areas = read_unique_csv(SUMMARY / "bcw_mangrove_gmw_area_replacement.csv")
    archive_path = ROOT / "data" / "raw" / "environmental" / "marine" / "bcw" / "output" / "draws.npz"
    with np.load(archive_path, allow_pickle=True) as archive:
        rate_draws = np.asarray(archive["bce_rates_draws"][2], dtype=float)
    area_km2 = areas["gmw_2025_mangroves_ha"].to_numpy(dtype=float) / 100.0
    flux_tc_draws = area_km2[:, None] * rate_draws[None, :]
    summaries: dict[str, np.ndarray] = {
        "gmw_mangrove_uptake_tC_yr_mean": np.mean(flux_tc_draws, axis=1),
        "gmw_mangrove_uptake_tC_yr_sd": np.std(flux_tc_draws, axis=1, ddof=1),
        "gmw_mangrove_uptake_tC_yr_p05": np.percentile(flux_tc_draws, 5, axis=1),
        "gmw_mangrove_uptake_tC_yr_p50": np.percentile(flux_tc_draws, 50, axis=1),
        "gmw_mangrove_uptake_tC_yr_p95": np.percentile(flux_tc_draws, 95, axis=1),
    }
    result = areas[["iso3", "bcw_mangroves_before_gmw_ha", "gmw_2025_mangroves_ha", "delta_mangroves_ha"]].copy()
    for column, values in summaries.items():
        result[column] = values
        result[column.replace("_tC_", "_tCO2_")] = values * CARBON_TO_CO2
    return result.rename(
        columns={
            "gmw_2025_mangroves_ha": "gmw_2025_mangrove_area_applied_ha",
            "delta_mangroves_ha": "gmw_minus_preupdate_mangrove_area_ha",
        }
    )


def build_fra_mangrove_audit() -> pd.DataFrame:
    """Keep the country-level FRA mangrove classification evidence used in GCW."""
    audit = read_unique_csv(SUMMARY / "fra_mangrove_forest_overlap_2025.csv")
    columns = [
        "iso3",
        "fra_mangroves_2025_ha",
        "documented_forest_fraction",
        "documented_forest_mangrove_area_ha",
        "overlap_status",
        "desk_study",
        "fra_report_handle",
    ]
    return audit[columns]


def build_master_table() -> tuple[pd.DataFrame, dict[str, object]]:
    """Join available country and territory data while preserving all NCW rows."""
    ncw = read_unique_csv(OUTPUT / "country_level_ncw.csv")
    territories = read_unique_csv(SUMMARY / "territories.csv")
    identity_columns = [
        "iso3",
        "UNIT_CODE",
        "ISO3",
        "m49",
        "in_fra",
        "in_bcw",
        "n_bcw_rows",
        "fra_name",
        "bcw_name",
        "sovereign",
        "fra_subregion",
        "region",
        "group_source",
    ]
    identity = territories[identity_columns].copy()
    master = merge_one_to_one(ncw, identity, "territorial identifiers")
    # The GMW allocation adds ATF_GI to NCW without a FRA/BCW territory row.
    # Keep its accounting identifier without inventing an ISO code or group.
    master["UNIT_CODE"] = master["UNIT_CODE"].fillna(master["iso3"])
    master["region"] = master["region"].fillna(master["continent"])
    master["group_source"] = master["group_source"].fillna("unclassified")

    master = merge_one_to_one(master, read_unique_csv(OUTPUT / "country_level_gcw.csv").drop(
        columns=["name", "continent", "fra_region", "groups", "population", "gdp", "gcw_usd2015_yr_mean",
                 "gcw_usd2015_yr_sd", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p50", "gcw_usd2015_yr_p95",
                 "gcw_per_capita_usd2015", "gcw_share_of_gdp"]), "GCW physical flux and FAOSTAT comparator")

    forest_areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    forest_areas = forest_areas.loc[forest_areas["year"].eq(2025)].rename(
        columns={
            "forest": "fra_total_forest_area_2025_ha",
            "mangroves": "fra_mangrove_category_2025_ha",
            "nrf": "fra_other_wooded_land_2025_ha",
            "planted": "fra_planted_forest_2025_ha",
            "primary": "fra_primary_forest_2025_ha",
        }
    )
    forest_areas = forest_areas[[
        "iso3", "fra_total_forest_area_2025_ha", "fra_mangrove_category_2025_ha",
        "fra_other_wooded_land_2025_ha", "fra_planted_forest_2025_ha", "fra_primary_forest_2025_ha",
    ]]
    if forest_areas["iso3"].duplicated().any():
        raise ValueError("FRA 2025 forest areas are not unique by accounting unit")
    master = merge_one_to_one(master, forest_areas, "FRA 2025 area totals")
    master = merge_one_to_one(master, build_forest_area_and_rates(), "four-biome forest areas and Gibbs/GFW rates")
    master = merge_one_to_one(master, build_fra_mangrove_audit(), "FRA mangrove report audit")
    master = merge_one_to_one(master, build_bcw_source_by_unit(), "marine source areas and published fluxes")
    master = merge_one_to_one(master, build_gmw_mangrove_flux(), "applied GMW-2025 mangrove area and flux")

    socio = read_unique_csv(SUMMARY / "socioeconomic_2024_by_unit.csv")
    socio_columns = [
        "iso3", "gcb_name", "gcb_2023_mtC_yr", "gcb_2024_mtC_yr", "gcb_2023_mtco2_yr",
        "gcb_2024_mtco2_yr", "population_2024", "gdp_2015usd_2024", "co2_emissions_tco2_2024",
        "co2_emissions_tco2_2023_gcb2025", "gdp_per_capita_2024", "emissions_2024_match_status",
    ]
    master = merge_one_to_one(master, socio[socio_columns], "GCB and WDI 2024 socioeconomic data")

    erosion = read_unique_csv(OUTPUT / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv")
    erosion_columns = [
        "iso3", "loss_tco2_mean", "loss_usd_mean", "loss_usd_p05", "loss_usd_p95",
        "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
        "loss_spatial_sd_low_usd2015_yr", "loss_spatial_sd_high_usd2015_yr",
        "reported_deforestation", "erosion_pct_of_gcw", "loss_pct_of_gdp",
    ]
    erosion = erosion[erosion_columns].rename(
        columns={
            "loss_usd_mean": "loss_value_usd2015_yr_mean",
            "loss_usd_p05": "loss_value_usd2015_yr_p05",
            "loss_usd_p95": "loss_value_usd2015_yr_p95",
        }
    )
    master = merge_one_to_one(master, erosion, "reported deforestation outcomes")

    balance = read_unique_csv(VALIDATION / "emissions_2024_accounting_balance_by_unit.csv")
    balance_columns = [
        "iso3", "co2_emissions_tco2_2024", "gcw_additions_tco2_yr",
        "gcw_accounting_balance_mean_tco2_yr", "gcw_accounting_balance_p05_tco2_yr",
        "gcw_accounting_balance_p50_tco2_yr", "gcw_accounting_balance_p95_tco2_yr",
        "ncw_accounting_balance_mean_tco2_yr", "ncw_accounting_balance_p05_tco2_yr",
        "ncw_accounting_balance_p50_tco2_yr", "ncw_accounting_balance_p95_tco2_yr",
        "gcw_additions_to_emissions_ratio",
    ]
    master = merge_one_to_one(
        master,
        balance[balance_columns].rename(columns={"co2_emissions_tco2_2024": "balance_emissions_tco2_2024"}),
        "2024 emissions balance",
    )

    ibrahim = read_unique_csv(VALIDATION / "ibrahim_2pct_and_pledge_allocations.csv")
    ibrahim_columns = [
        "iso3", "ibrahim_2pct_usd2015_yr", "gcw_share_global_pct",
        "share_of_30yr_100bn_pledge_usd_cumulative", "lost_capacity_discounted_30yr_tco2",
    ]
    master = merge_one_to_one(master, ibrahim[ibrahim_columns], "Ibrahim allocation scenario")

    busch = read_unique_csv(VALIDATION / "busch_action_curve_country_scenarios.csv")
    busch_columns = [
        "iso3", "target_discounted_30yr_tco2", "busch_curve_available",
        "source_quantity_at_minus20_tco2_pv", "source_quantity_at_zero_tco2_pv",
        "source_quantity_at_100_tco2_pv", "marginal_price_lower_usd2020_tco2",
        "marginal_price_upper_usd2020_tco2", "status",
        "annualized_uniform_price_payment_lower_usd2015_yr_partial",
        "annualized_uniform_price_payment_upper_usd2015_yr_partial",
    ]
    master = merge_one_to_one(
        master,
        busch[busch_columns].rename(columns={"status": "busch_scenario_status"}),
        "Busch action-cost comparison",
    )

    in_fra = master["in_fra"].map(lambda value: bool(value) if pd.notna(value) else False)
    in_bcw = master["in_bcw"].map(lambda value: bool(value) if pd.notna(value) else False)
    master["unit_class"] = np.select(
        [
            master["iso3"].isin(["BCW-JR", "BCW-OC"]),
            in_fra,
            in_bcw,
        ],
        ["BCW aggregate / non-country row", "FRA country or territory", "BCW-only accounting unit"],
        default="other accounting unit",
    )
    master["exclude_from_country_sum"] = master["iso3"].isin(["BCW-JR", "BCW-OC"])
    master["spatial_outcome_lost_capacity_tco2_yr"] = master["loss_tco2_mean"]
    master["spatial_outcome_lost_capacity_mtco2_yr"] = master["loss_tco2_mean"] / 1e6
    master["spatial_outcome_erosion_pct_of_gcw"] = master["erosion_pct_of_gcw"]
    master["spatial_outcome_gcw_gdp_pct_2024"] = (
        100.0 * master["gcw_usd2015_yr_mean"] / master["gdp_2015usd_2024"]
    )
    master["spatial_predictor_log_gdp_per_capita_2024"] = np.log(master["gdp_per_capita_2024"])
    master["spatial_predictor_log_forest_area_mha"] = np.log1p(master["forest_area_allocated_total_ha"] / 1e6)
    master["spatial_predictor_log_emissions_mtco2_2024"] = np.log1p(master["co2_emissions_tco2_2024"] / 1e6)
    master["spatial_predictor_log_population_2024"] = np.log(master["population_2024"])
    master["spatial_predictor_log1p_lost_capacity_mtco2_yr"] = np.log1p(
        master["spatial_outcome_lost_capacity_mtco2_yr"]
    )
    master["spatial_predictor_log1p_erosion_pct_of_gcw"] = np.log1p(
        master["spatial_outcome_erosion_pct_of_gcw"]
    )
    master["spatial_predictor_log1p_gcw_gdp_pct_2024"] = np.log1p(
        master["spatial_outcome_gcw_gdp_pct_2024"]
    )

    source_flux_columns = [
        "saltmarsh_uptake_tC_yr_source_mean",
        "seagrass_uptake_tC_yr_source_mean",
        "gmw_mangrove_uptake_tC_yr_mean",
    ]
    master["coastal_component_uptake_tC_yr_current_area"] = master[source_flux_columns].sum(axis=1, min_count=1)
    master["coastal_component_uptake_tCO2_yr_current_area"] = (
        master["coastal_component_uptake_tC_yr_current_area"] * CARBON_TO_CO2
    )
    master["open_ocean_bcp_tCO2_yr_source"] = master["open_ocean_bcp_tC_yr_source"] * CARBON_TO_CO2

    # Use the exact code lists recorded by the spatial script, not a reconstructed
    # approximation that could ignore geometry availability or its sample filters.
    sample_audit = pd.read_csv(VALIDATION / "spatial_emissions_2024_sample_audit.csv")
    inclusion_columns: list[str] = []
    sample_counts: dict[str, int] = {}
    for _, sample_row in sample_audit.iterrows():
        sample_label = f"{sample_row['specification']}__{sample_row['outcome']}"
        column = "spatial_sample_" + sample_label
        included_codes = {
            code for code in str(sample_row["matched_sample_hash_codes"]).split(";") if code
        }
        master[column] = master["iso3"].isin(included_codes)
        observed = int(master[column].sum())
        expected = int(sample_row["n"])
        if observed != expected:
            raise ValueError(f"Sample membership for {sample_label} has {observed} rows, expected {expected}")
        inclusion_columns.append(column)
        sample_counts[column] = observed
    master["spatial_sample_any_2024"] = master[inclusion_columns].any(axis=1)

    master = master.rename(
        columns={
            "population": "population_bcw_reference",
            "gdp": "gdp_2015usd_bcw_reference",
            "ncw_per_capita_usd2015": "ncw_per_capita_usd2015_bcw_reference",
            "ncw_share_of_gdp": "ncw_share_of_gdp_bcw_reference",
        }
    )
    master = master.sort_values("iso3").reset_index(drop=True)
    if len(master) != 267 or master["iso3"].duplicated().any():
        raise ValueError(f"Master table must preserve the 267 unique NCW units; got {len(master)} rows")
    master[["UNIT_CODE", "ISO3", "name", "sovereign", "groups", "group_source"]].to_csv(
        VALIDATION / "economic_group_assignment_by_unit.csv", index=False,
    )

    area_rate = master["forest_additions_from_area_rates_tCO2_yr"]
    model_flux = master["uptake_tco2_yr_mean"]
    compared = area_rate.notna() & model_flux.notna()
    relative_difference = (
        (area_rate[compared] - model_flux[compared]).abs()
        / model_flux[compared].abs().clip(lower=1.0)
    )
    if relative_difference.max() > 1e-6:
        raise ValueError(f"Area × rate forest flux does not reconcile to country GCW physical flux: {relative_difference.max()}")

    audit = {
        "created_on": DATE,
        "source_key_table": "results/country_level_ncw.csv",
        "rows": int(len(master)),
        "columns": int(len(master.columns)),
        "unique_unit_codes": int(master["iso3"].nunique()),
        "fra_units": int(in_fra.sum()),
        "bcw_units": int(in_bcw.sum()),
        "bcw_aggregate_rows_excluded_from_country_sums": int(master["exclude_from_country_sum"].sum()),
        "spatial_complete_case_counts": sample_counts,
        "area_rate_vs_country_flux_max_relative_difference": float(relative_difference.max()),
        "columns": master.columns.tolist(),
        "notes": [
        "Debt is excluded; the current spatial models use 2024 emissions, population and GDP where matched.",
        "The three current outcomes are also retained as log1p-transformed predictors for the three additional emissions-as-outcome relationships.",
            "GMW mangrove flux summaries propagate the published mangrove-rate draws; mapped hectares are fixed.",
            "Forest pixel spatial SD is a dispersion sensitivity, not a confidence interval.",
            "Saltmarsh, seagrass, mangrove-sediment and open-ocean BCP flows remain separately labelled.",
            "BCW-JR and BCW-OC are retained for traceability but flagged against country-level sums.",
        ],
    }
    return master, audit


def write_data_dictionary(audit: dict[str, object]) -> None:
    """Write concise provenance and unit guidance for the wide table."""
    path = ROOT.parent / "NEXT" / "COUNTRY_LEVEL_RESULTS_MASTER_DATA_DICTIONARY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Table pays et territoires pour la rédaction des Results",
        "",
        "Fichier : `results/validation/country_level_results_master.csv`.",
        f"Table : {audit['rows']} lignes, {audit['columns']} colonnes, une ligne par unité de `country_level_ncw.csv`.",
        "",
        "## Contenu et sources",
        "",
        "- Identifiants et groupes : `data/derived/territories.csv`; les lignes `BCW-JR` et `BCW-OC` sont des agrégats BCW conservés pour traçabilité et marqués `exclude_from_country_sum=true`.",
        "- GCW et flux forestier : `results/country_level_gcw.csv`, surfaces FRA/GEZ dans `data/derived/forest_area_by_biome.csv`, taux non-mangrove dans `gfw_gibbs_biome_rates_non_mangrove.csv`.",
        "- Écosystèmes et EEZ : `data/raw/environmental/marine/bcw/output/country_level_bcw.csv`, agrégé avec `bcw_territory_mapping.csv`. Les superficies côtières sont en km² selon la source BCW; l’aire GMW corrigée appliquée à BCW est en ha.",
        "- Mangroves GMW : `bcw_mangrove_gmw_area_replacement.csv`; le flux physique est calculé à partir de l’aire GMW 2025 et des tirages du taux d’enfouissement Hilmi/Alongi. Il concerne les sédiments, pas la biomasse des arbres.",
        "- FRA mangroves : `fra_mangrove_forest_overlap_2025.csv`; le statut et le rapport source sont gardés séparément de l’aire GMW.",
        "- Données économiques et émissions : `socioeconomic_2024_by_unit.csv`; population et PIB WDI 2024, émissions fossiles et industrielles GCB 2024. Les champs d’émissions 2023 sont conservés pour la comparaison de millésime. La dette n’est pas incluse.",
        "- Déforestation : `Supplementary_country_level_erosion.csv`; les valeurs manquantes signifient non déclaré/non couvert, jamais zéro par défaut.",
        "- Finance : scénario Ibrahim 2 % du GCW et table de comparaison de courbes d’action Busch. Les statuts Busch sont manquants quand une courbe nationale n’est pas disponible.",
        "- Solde 2024 : table de comparaison comptable nationale avec émissions fixes et tirages de valeur déjà disponibles.",
        "",
        "## Lecture des variables",
        "",
        "- Les colonnes suffixées `_tC_yr` et `_tCO2_yr` sont des flux annuels. Les hectares, km² et dollars sont explicités dans le nom des colonnes.",
        "- `forest_area_allocated_*_ha` désigne les surfaces FRA réparties par biome et selon la convention de chevauchement FRA documentée utilisée dans GCW. `forest_additions_*` est le produit surface × taux moyen Gibbs/GFW, pas une mesure nationale observée.",
        "- `forest_rate_*_spatial_sd` décrit la dispersion des pixels dans le biome; elle n’est pas un écart-type d’incertitude des taux.",
        "- Les colonnes `spatial_predictor_log1p_*` donnent les transformations utilisées quand une variable de résultat antérieure entre comme X dans un modèle avec les émissions comme Y.",
        "- Les flux saltmarsh, seagrass, mangrove-sédiments et BCP océanique sont séparés. Leur somme physique n’est pas présentée comme un flux homogène dans le code.",
        "- `ncw_usd2015_yr_*`, `gcw_usd2015_yr_*` et `bcw_usd2015_yr_*` sont des valeurs monétaires annuelles aux prix de 2015. Les P05/P50/P95 ne propagent pas l’incertitude de toutes les surfaces et taux forestiers.",
        "- Les colonnes `spatial_sample_*` reproduisent les échantillons complets de la séquence économétrique 2024; elles ne déclarent pas qu’un modèle final a été choisi.",
        "",
        "## Audit de construction",
        "",
        f"- Lignes FRA : {audit['fra_units']}; unités BCW : {audit['bcw_units']}; lignes agrégées exclues des sommes nationales : {audit['bcw_aggregate_rows_excluded_from_country_sums']}.",
        f"- Écart relatif maximum entre surface × taux et flux physique GCW existant : {audit['area_rate_vs_country_flux_max_relative_difference']:.3g}.",
        f"- Effectifs spatiaux attendus et retrouvés : `{json.dumps(audit['spatial_complete_case_counts'], ensure_ascii=False)}`.",
        "- `population_bcw_reference`, `gdp_2015usd_bcw_reference`, `ncw_per_capita_usd2015_bcw_reference` et `ncw_share_of_gdp_bcw_reference` viennent de la table de référence BCW; les variables WDI 2024 portent le suffixe `_2024`.",
        "- Les champs sans valeur restent vides dans le CSV, sauf les indicateurs booléens d’appartenance au périmètre. Un zéro observé reste distinct d’une valeur manquante.",
        "",
        "La table est un fichier analytique large, pas une table prête à publier. Les limites de définition et de couverture sont détaillées dans `docs/METHODS.md` et `docs/DATA_AUDIT.md`.",
        "",
    ]
    body = [
        line.replace("`code/", "`../repo/code/")
        .replace("`data/", "`../repo/data/")
        .replace("`docs/", "`../repo/docs/")
        .replace("`results/", "`../repo/results/")
        for line in body
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def main() -> None:
    """Build the master CSV, audit JSON, and data dictionary."""
    master, audit = build_master_table()
    csv_path = VALIDATION / "country_level_results_master.csv"
    json_path = VALIDATION / "country_level_results_master_audit.json"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(csv_path, index=False, float_format="%.10g")
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    write_data_dictionary(audit)
    print(
        json.dumps(
            {
                "csv": str(csv_path),
                "rows": audit["rows"],
                "columns": audit["columns"],
                "spatial_complete_case_counts": audit["spatial_complete_case_counts"],
                "max_relative_flux_difference": audit["area_rate_vs_country_flux_max_relative_difference"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
