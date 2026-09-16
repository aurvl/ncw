"""Q (Route B): How much CO2 does each country's forest absorb per year (area x Pan rate)?

Outputs:
- data_source/summary/forest_area_by_biome.csv : ha per country x biome x forest type (FRA AREA_YEAR)
- data_source/summary/forest_uptake_pan.csv    : tCO2/yr per country (mean, sd, percentiles)
- data_source/summary/draws/forest_uptake_pan.npz : (N, B) tCO2/yr draws, with and without mangroves

Rates are drawn once per rate (normal, truncated at zero) and shared by every country,
so countries in the same biome are perfectly correlated (C8).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AREA_YEAR, CARBON_TO_CO2, FOREST_TYPES, SEED, SUMMARY
from .validation import summarise_draws, write_table


def area_by_biome(forest_areas: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    year = forest_areas.loc[forest_areas["year"].astype(str) == AREA_YEAR]
    year = year[["iso3", "nrf", "nrf_excl_mangroves", "planted", "mangroves"]]
    merged = shares[["iso3", "biome", "share", "source"]].merge(year, on="iso3", how="inner")
    records = []
    for variant, nrf_column in [("excl_mangroves", "nrf_excl_mangroves"), ("incl_mangroves", "nrf")]:
        for forest_type, column in [("nrf", nrf_column), ("planted", "planted")]:
            part = merged[["iso3", "biome", "source"]].copy()
            part["forest_type"] = forest_type
            part["variant"] = variant
            part["area_ha"] = merged["share"] * merged[column]
            records.append(part)
    return pd.concat(records, ignore_index=True).rename(columns={"source": "share_source"})


def draw_rates(rates: pd.DataFrame, n_draws: int) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(SEED)
    unique = rates.drop_duplicates("rate_key")
    keys = unique["rate_key"].tolist()
    draws = rng.normal(
        unique["rate_tc_ha_yr_mean"].to_numpy()[:, None],
        unique["rate_tc_ha_yr_sd"].to_numpy()[:, None],
        size=(len(keys), n_draws),
    )
    return keys, np.clip(draws, 0.0, None)


def uptake_draws(areas: pd.DataFrame, rates: pd.DataFrame, rate_keys: list[str], rate_draws: np.ndarray,
                 variant: str, countries: list[str]) -> np.ndarray:
    selected = areas.loc[areas["variant"] == variant].merge(
        rates[["biome", "forest_type", "rate_key"]], on=["biome", "forest_type"], how="left", validate="many_to_one"
    )
    matrix = (
        selected.pivot_table(index="iso3", columns="rate_key", values="area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=countries, columns=rate_keys, fill_value=0.0)
        .to_numpy()
    )
    return (matrix @ rate_draws) * CARBON_TO_CO2  # tC/yr -> tCO2/yr


def run(forest_areas: pd.DataFrame, shares: pd.DataFrame, rates: pd.DataFrame, n_draws: int) -> tuple[pd.DataFrame, dict]:
    areas = area_by_biome(forest_areas, shares)
    write_table(areas, SUMMARY / "forest_area_by_biome.csv")
    assert set(areas["forest_type"]) <= set(FOREST_TYPES)

    countries = sorted(areas["iso3"].unique())
    rate_keys, rate_draws = draw_rates(rates, n_draws)
    draws = {
        variant: uptake_draws(areas, rates, rate_keys, rate_draws, variant, countries).astype(np.float32)
        for variant in ["excl_mangroves", "incl_mangroves"]
    }

    table = pd.DataFrame({"iso3": countries})
    for variant, matrix in draws.items():
        table = pd.concat([table, summarise_draws(matrix, f"uptake_tco2_yr_{variant}")], axis=1)
    write_table(table, SUMMARY / "forest_uptake_pan.csv")

    path = SUMMARY / "draws" / "forest_uptake_pan.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, iso3=np.array(countries), rate_keys=np.array(rate_keys), **draws)
    return table, {"iso3": countries, **draws}
