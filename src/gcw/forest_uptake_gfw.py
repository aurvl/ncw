"""Country gross additions to living forest biomass using Gibbs/GFW rates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, BIOMES, CARBON_TO_CO2, SUMMARY
from .validation import summarise_draws, write_table

VARIANTS = ["excl_mangroves", "incl_mangroves"]


def area_by_biome(forest_areas: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    """Allocate FRA 2025 forest area using four biome shares; remove mangroves from tropical."""
    year = forest_areas.loc[forest_areas["year"].astype(str) == AREA_YEAR, ["iso3", "forest", "mangroves"]]
    grouped = (
        shares.loc[shares["biome"].isin(BIOMES)]
        .groupby(["iso3", "biome"], as_index=False)
        .agg(share=("share", "sum"), share_source=("source", "first"))
        .merge(year, on="iso3", how="inner")
    )
    grouped["area_incl_mangroves_ha"] = grouped["share"] * grouped["forest"]
    tropical = grouped["biome"] == "tropical"
    grouped["area_excl_mangroves_ha"] = grouped["area_incl_mangroves_ha"]
    grouped.loc[tropical, "area_excl_mangroves_ha"] = (
        grouped.loc[tropical, "area_incl_mangroves_ha"] - grouped.loc[tropical, "mangroves"]
    ).clip(lower=0.0)
    grouped["mangroves_exceed_tropical_area"] = tropical & (
        grouped["mangroves"] > grouped["area_incl_mangroves_ha"]
    )
    records = []
    for variant in VARIANTS:
        part = grouped[["iso3", "biome", "share", "share_source", "mangroves_exceed_tropical_area"]].copy()
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
    main_areas = areas.loc[areas["variant"] == "excl_mangroves"]
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
    countries, central_tco2 = uptake_for_rates(areas, rates, "excl_mangroves")
    _, including_tco2 = uptake_for_rates(areas, rates, "incl_mangroves")
    sensitivity_by_country = {
        scenario: dict(zip(group["iso3"], group["uptake_tco2_yr"]))
        for scenario, group in sensitivity.groupby("scenario", sort=False)
    }
    draws = {
        "iso3": np.array(countries),
        "excl_mangroves": np.broadcast_to(central_tco2[:, None], (len(countries), n_draws)).astype(np.float32).copy(),
        "incl_mangroves": np.broadcast_to(including_tco2[:, None], (len(countries), n_draws)).astype(np.float32).copy(),
        "spatial_sd_low": np.broadcast_to(
            np.array([sensitivity_by_country["spatial_sd_low"][c] for c in countries])[:, None], (len(countries), n_draws)
        ).astype(np.float32).copy(),
        "spatial_sd_high": np.broadcast_to(
            np.array([sensitivity_by_country["spatial_sd_high"][c] for c in countries])[:, None], (len(countries), n_draws)
        ).astype(np.float32).copy(),
    }
    table = pd.DataFrame({"iso3": countries})
    table = pd.concat([table, summarise_draws(draws["excl_mangroves"], "uptake_tco2_yr")], axis=1)
    write_table(table, SUMMARY / "forest_uptake_gfw.csv")
    path = SUMMARY / "draws" / "forest_uptake_gfw.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, biomes=np.array(rates["biome"]), **draws)
    return table, draws
