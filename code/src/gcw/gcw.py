"""Q: What is the annual Green Carbon Wealth of each country?

GCW_i (US$2015/yr) = forest CO2 uptake_i (tCO2/yr) x GSCC (US$2015/tCO2), computed draw by draw.
- Main estimate: FRA biome area x Gibbs/GFW gross living-biomass rate, mangroves excluded.
- Route A (complementary): FAOSTAT net flux; only the GSCC is uncertain.

Outputs: data/outputs/accounts/country_level_gcw.csv, data/outputs/draws/gcw_draws.npz
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ACCOUNTS, DRAWS
from .validation import summarise_draws, write_npz_atomic, write_table


def build_gcw(territories: pd.DataFrame, forest: dict, faostat: pd.DataFrame, gscc: np.ndarray) -> tuple[pd.DataFrame, dict]:
    countries = list(forest["iso3"])
    gscc32 = gscc.astype(np.float32)[None, :]
    gcw_main = forest["documented_overlap_removed"] * gscc32
    gcw_no_overlap_removed = forest["no_overlap_removed"] * gscc32
    gcw_spatial_low = forest["spatial_sd_low"] * gscc32
    gcw_spatial_high = forest["spatial_sd_high"] * gscc32

    faostat_uptake = faostat.set_index("iso3")["net_uptake_tco2_yr"]
    faostat_countries = sorted(faostat_uptake.index)
    gcw_faostat = faostat_uptake.reindex(faostat_countries).to_numpy(dtype=np.float32)[:, None] * gscc32

    route_b = pd.concat(
        [
            pd.DataFrame({"iso3": countries}),
            summarise_draws(forest["documented_overlap_removed"], "uptake_tco2_yr"),
            summarise_draws(gcw_main, "gcw_usd2015_yr"),
            summarise_draws(gcw_spatial_low, "gcw_spatial_sd_low_usd2015_yr")["gcw_spatial_sd_low_usd2015_yr_mean"].to_frame(),
            summarise_draws(gcw_spatial_high, "gcw_spatial_sd_high_usd2015_yr")["gcw_spatial_sd_high_usd2015_yr_mean"].to_frame(),
            summarise_draws(gcw_no_overlap_removed, "gcw_no_overlap_removed_usd2015_yr")[["gcw_no_overlap_removed_usd2015_yr_mean"]],
        ],
        axis=1,
    )
    route_a = pd.concat(
        [
            pd.DataFrame({"iso3": faostat_countries}),
            faostat.set_index("iso3").reindex(faostat_countries)[["net_uptake_tco2_yr", "interannual_sd", "n_years"]]
            .add_prefix("faostat_").reset_index(drop=True),
            summarise_draws(gcw_faostat, "faostat_gcw_usd2015_yr"),
        ],
        axis=1,
    )

    info = territories[["iso3", "name", "continent", "fra_region", "groups", "population", "gdp"]]
    table = info.merge(route_b, on="iso3", how="right").merge(route_a, on="iso3", how="outer")
    table["name"] = table["name"].fillna(table["iso3"])
    table["gcw_per_capita_usd2015"] = table["gcw_usd2015_yr_mean"] / table["population"]
    table["gcw_share_of_gdp"] = table["gcw_usd2015_yr_mean"] / table["gdp"]
    table = table.sort_values("gcw_usd2015_yr_mean", ascending=False).reset_index(drop=True)

    draws = {
        "iso3": np.array(countries),
        "gcw_usd2015_yr": gcw_main,
        "uptake_tco2_yr": forest["documented_overlap_removed"].astype(np.float32),
        "gcw_spatial_sd_low_usd2015_yr": gcw_spatial_low,
        "gcw_spatial_sd_high_usd2015_yr": gcw_spatial_high,
        "gcw_no_overlap_removed_usd2015_yr": gcw_no_overlap_removed,
        "faostat_iso3": np.array(faostat_countries),
        "faostat_gcw_usd2015_yr": gcw_faostat,
        "gscc": gscc.astype(np.float32),
    }
    return table, draws


def run(territories: pd.DataFrame, forest: dict, faostat: pd.DataFrame, gscc: np.ndarray) -> tuple[pd.DataFrame, dict]:
    table, draws = build_gcw(territories, forest, faostat, gscc)
    write_table(table, ACCOUNTS / "country_level_gcw.csv")
    path = DRAWS / "gcw_draws.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_npz_atomic(path, **draws)
    return table, draws
