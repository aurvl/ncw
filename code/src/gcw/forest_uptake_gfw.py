"""Country gross additions to living forest biomass using Gibbs/GFW rates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, BIOMES, CARBON_TO_CO2, SUMMARY
from .validation import summarise_draws, write_table

VARIANTS = ["documented_overlap_removed", "no_overlap_removed"]


def area_by_biome(
    forest_areas: pd.DataFrame,
    shares: pd.DataFrame,
    overlap_evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Allocate forest area by biome and remove only report-documented mangrove overlap."""
    if overlap_evidence is None:
        overlap_evidence = pd.read_csv(SUMMARY / "fra_mangrove_forest_overlap_2025.csv")
    overlap_columns = ["iso3", "documented_forest_mangrove_area_ha"]
    for optional in (
        "overlap_status",
        "fra_mangroves_2025_ha",
        "documented_other_wooded_land_area_ha",
        "documented_remaining_land_area_ha",
        "unresolved_mangrove_area_ha",
    ):
        if optional in overlap_evidence.columns:
            overlap_columns.append(optional)
    overlap = overlap_evidence[overlap_columns].copy()
    year = forest_areas.loc[forest_areas["year"].astype(str) == AREA_YEAR].copy()
    if "mangroves_reported" not in year:
        year["mangroves_reported"] = year["mangroves"].notna()
    year = year[["iso3", "forest", "mangroves", "mangroves_reported"]]
    grouped = (
        shares.loc[shares["biome"].isin(BIOMES)]
        .groupby(["iso3", "biome"], as_index=False)
        .agg(share=("share", "sum"), share_source=("source", "first"))
        .merge(year, on="iso3", how="inner")
        .merge(overlap, on="iso3", how="left")
    )
    grouped["documented_forest_mangrove_area_ha"] = grouped["documented_forest_mangrove_area_ha"].fillna(0.0)
    for column in ("documented_other_wooded_land_area_ha", "documented_remaining_land_area_ha"):
        if column not in grouped.columns:
            grouped[column] = 0.0
        else:
            grouped[column] = grouped[column].fillna(0.0)
    if "unresolved_mangrove_area_ha" in grouped.columns:
        grouped["unresolved_fra_mangrove_category_ha"] = grouped["unresolved_mangrove_area_ha"].fillna(0.0)
    else:
        grouped["unresolved_fra_mangrove_category_ha"] = (
            grouped["mangroves"] - grouped["documented_forest_mangrove_area_ha"]
        ).clip(lower=0.0)
        if "overlap_status" in grouped.columns:
            grouped.loc[grouped["overlap_status"] == "documented_all_other_wooded_land", "unresolved_fra_mangrove_category_ha"] = 0.0
    grouped["area_incl_mangroves_ha"] = grouped["share"] * grouped["forest"]
    tropical = grouped["biome"].eq("tropical")
    grouped["area_documented_overlap_removed_ha"] = grouped["area_incl_mangroves_ha"]
    grouped.loc[tropical, "area_documented_overlap_removed_ha"] -= grouped.loc[
        tropical, "documented_forest_mangrove_area_ha"
    ]
    if (grouped["area_documented_overlap_removed_ha"] < -1e-6).any():
        raise ValueError("Report-documented forest mangrove area exceeds the allocated tropical forest area")
    grouped["area_no_overlap_removed_ha"] = grouped["area_incl_mangroves_ha"]
    grouped["fra_mangroves_exceed_tropical_allocation"] = tropical & (
        grouped["mangroves"] > grouped["area_incl_mangroves_ha"]
    )
    grouped["documented_overlap_exceeds_tropical_allocation"] = tropical & (
        grouped["documented_forest_mangrove_area_ha"] > grouped["area_incl_mangroves_ha"]
    )
    records = []
    for variant in VARIANTS:
        part = grouped[
            [
                "iso3",
                "biome",
                "share",
                "share_source",
                "documented_forest_mangrove_area_ha",
                "documented_other_wooded_land_area_ha",
                "documented_remaining_land_area_ha",
                "unresolved_fra_mangrove_category_ha",
                "fra_mangroves_exceed_tropical_allocation",
                "documented_overlap_exceeds_tropical_allocation",
                "mangroves_reported",
            ]
        ].copy()
        part["variant"] = variant
        part["area_ha"] = grouped[f"area_{variant}_ha"]
        records.append(part)
    return pd.concat(records, ignore_index=True)


def uptake_for_rates(areas: pd.DataFrame, rates: pd.DataFrame, variant: str) -> tuple[list[str], np.ndarray]:
    biomes = list(rates["biome"])
    countries = sorted(areas["iso3"].unique())
    area_matrix = (
        areas.loc[areas["variant"] == variant]
        .pivot_table(index="iso3", columns="biome", values="area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=countries, columns=biomes, fill_value=0.0)
        .to_numpy(dtype=np.float64)
    )
    rate_vector = rates.set_index("biome").loc[biomes, "rate_tc_ha_yr_mean"].to_numpy(dtype=np.float64)
    return countries, area_matrix @ rate_vector * CARBON_TO_CO2


def sensitivity_uptake(areas: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Deterministic mean ± one spatial SD scenarios, not probabilistic intervals."""
    biome_order = list(rates["biome"])
    indexed = rates.set_index("biome").loc[biome_order]
    central = indexed["rate_tc_ha_yr_mean"].to_numpy(dtype=np.float64)
    spatial_sd = indexed["rate_tc_ha_yr_spatial_sd"].to_numpy(dtype=np.float64)
    scenarios = {
        "central": central,
        "spatial_sd_low": np.maximum(central - spatial_sd, 0.0),
        "spatial_sd_high": central + spatial_sd,
    }
    main_areas = areas.loc[areas["variant"] == "documented_overlap_removed"]
    countries = sorted(main_areas["iso3"].unique())
    area_matrix = (
        main_areas.pivot_table(index="iso3", columns="biome", values="area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=countries, columns=biome_order, fill_value=0.0)
        .to_numpy(dtype=np.float64)
    )
    rows = []
    for name, q in scenarios.items():
        tco2 = area_matrix @ q * CARBON_TO_CO2
        rows.append(pd.DataFrame({"iso3": countries, "scenario": name, "uptake_tco2_yr": tco2}))
    return pd.concat(rows, ignore_index=True)


def run(forest_areas: pd.DataFrame, shares: pd.DataFrame, rates: pd.DataFrame, n_draws: int) -> tuple[pd.DataFrame, dict]:
    if set(rates["biome"]) != set(BIOMES):
        raise ValueError(f"Expected one Gibbs/GFW rate for each biome {BIOMES}; got {rates['biome'].tolist()}")
    areas = area_by_biome(forest_areas, shares)
    write_table(areas, SUMMARY / "forest_area_by_biome.csv")

    sensitivity = sensitivity_uptake(areas, rates)
    write_table(sensitivity, SUMMARY / "forest_uptake_spatial_sensitivity.csv")
    countries, central_tco2 = uptake_for_rates(areas, rates, "documented_overlap_removed")
    _, including_tco2 = uptake_for_rates(areas, rates, "no_overlap_removed")
    sensitivity_by_country = {
        scenario: dict(zip(group["iso3"], group["uptake_tco2_yr"]))
        for scenario, group in sensitivity.groupby("scenario", sort=False)
    }
    draws = {
        "iso3": np.array(countries),
        "documented_overlap_removed": np.broadcast_to(central_tco2[:, None], (len(countries), n_draws)).astype(np.float32).copy(),
        "no_overlap_removed": np.broadcast_to(including_tco2[:, None], (len(countries), n_draws)).astype(np.float32).copy(),
        "spatial_sd_low": np.broadcast_to(
            np.array([sensitivity_by_country["spatial_sd_low"][c] for c in countries])[:, None], (len(countries), n_draws)
        ).astype(np.float32).copy(),
        "spatial_sd_high": np.broadcast_to(
            np.array([sensitivity_by_country["spatial_sd_high"][c] for c in countries])[:, None], (len(countries), n_draws)
        ).astype(np.float32).copy(),
    }
    table = pd.DataFrame({"iso3": countries})
    table = pd.concat([table, summarise_draws(draws["documented_overlap_removed"], "uptake_tco2_yr")], axis=1)
    write_table(table, SUMMARY / "forest_uptake_gfw.csv")
    path = SUMMARY / "draws" / "forest_uptake_gfw.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, biomes=np.array(rates["biome"]), **draws)
    return table, draws
