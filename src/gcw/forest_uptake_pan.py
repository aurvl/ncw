"""Q (Route B): How much CO2 does each country's forest absorb per year?

For country i (C17):
    A_i,T  = forest_i x (s_i,tropical + s_i,subtropical)  - mangroves_i   (C7)
    A_i,Te = forest_i x s_i,temperate
    A_i,B  = forest_i x s_i,boreal
    C_i    = A_i,T q_T + A_i,Te q_Te + A_i,B q_B   (tC/yr),   U_i = C_i x 44/12   (tCO2/yr)

Mangroves, counted in BCW, are removed from the tropical area (they only occur in tropical and
subtropical zones); a variant keeps them for the C7 alternative.

Outputs:
- data_source/summary/forest_area_by_biome.csv    : ha per country x Pan biome x variant (FRA AREA_YEAR)
- data_source/summary/forest_uptake_pan.csv       : tCO2/yr per country (mean, sd, percentiles)
- data_source/summary/draws/forest_uptake_pan.npz : (N, B) tCO2/yr draws, with and without mangroves

Each rate is drawn once per draw from a normal distribution truncated at zero (C15) and shared by
all countries, so countries in the same biome are perfectly correlated (C8).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, CARBON_TO_CO2, PAN_BIOME_MEMBERS, SEED, SUMMARY
from .validation import summarise_draws, write_table

VARIANTS = ["excl_mangroves", "incl_mangroves"]


def area_by_biome(forest_areas: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    year = forest_areas.loc[forest_areas["year"].astype(str) == AREA_YEAR, ["iso3", "forest", "mangroves"]]
    member_of = {member: biome for biome, members in PAN_BIOME_MEMBERS.items() for member in members}
    grouped = (
        shares.assign(pan_biome=shares["biome"].map(member_of))
        .groupby(["iso3", "pan_biome"], as_index=False)
        .agg(share=("share", "sum"), share_source=("source", "first"))
        .merge(year, on="iso3", how="inner")
    )
    grouped["area_incl_mangroves_ha"] = grouped["share"] * grouped["forest"]
    tropical = grouped["pan_biome"] == "tropical"
    grouped["area_excl_mangroves_ha"] = grouped["area_incl_mangroves_ha"]
    grouped.loc[tropical, "area_excl_mangroves_ha"] = (
        grouped.loc[tropical, "area_incl_mangroves_ha"] - grouped.loc[tropical, "mangroves"]
    ).clip(lower=0.0)
    grouped["mangroves_exceed_tropical_area"] = tropical & (grouped["mangroves"] > grouped["area_incl_mangroves_ha"])
    records = []
    for variant in VARIANTS:
        part = grouped[["iso3", "pan_biome", "share", "share_source", "mangroves_exceed_tropical_area"]].copy()
        part["variant"] = variant
        part["area_ha"] = grouped[f"area_{variant}_ha"]
        records.append(part)
    return pd.concat(records, ignore_index=True)


def draw_rates(rates: pd.DataFrame, n_draws: int) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(SEED)
    biomes = rates["pan_biome"].tolist()
    draws = rng.normal(
        rates["rate_tc_ha_yr_mean"].to_numpy()[:, None], rates["rate_tc_ha_yr_sd"].to_numpy()[:, None], size=(len(biomes), n_draws)
    )
    return biomes, np.clip(draws, 0.0, None)


def uptake_draws(areas: pd.DataFrame, biomes: list[str], rate_draws: np.ndarray, variant: str, countries: list[str]) -> np.ndarray:
    matrix = (
        areas.loc[areas["variant"] == variant]
        .pivot_table(index="iso3", columns="pan_biome", values="area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=countries, columns=biomes, fill_value=0.0)
        .to_numpy()
    )
    return (matrix @ rate_draws) * CARBON_TO_CO2  # tC/yr -> tCO2/yr


def run(forest_areas: pd.DataFrame, shares: pd.DataFrame, rates: pd.DataFrame, n_draws: int) -> tuple[pd.DataFrame, dict]:
    areas = area_by_biome(forest_areas, shares)
    write_table(areas, SUMMARY / "forest_area_by_biome.csv")

    countries = sorted(areas["iso3"].unique())
    biomes, rate_draws = draw_rates(rates, n_draws)
    draws = {variant: uptake_draws(areas, biomes, rate_draws, variant, countries).astype(np.float32) for variant in VARIANTS}

    table = pd.DataFrame({"iso3": countries})
    for variant, matrix in draws.items():
        table = pd.concat([table, summarise_draws(matrix, f"uptake_tco2_yr_{variant}")], axis=1)
    write_table(table, SUMMARY / "forest_uptake_pan.csv")

    path = SUMMARY / "draws" / "forest_uptake_pan.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, iso3=np.array(countries), pan_biomes=np.array(biomes), **draws)
    return table, {"iso3": countries, **draws}
