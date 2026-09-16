"""Q: How much forest does each country have, split into NRF, planted forest and mangroves?

Output: data_source/summary/forest_areas.csv (hectares, FRA 2025, all reporting years)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SUMMARY
from .validation import read_fra_variable, write_table

YEARS = ["1990", "2000", "2010", "2015", "2020", "2025"]
VARIABLES = {
    "forest": "1a_forestArea",
    "nrf": "1b_naturallyRegeneratingForest",
    "planted": "1b_plantedForest",
    "mangroves": "1c_mangroves",
}


def build_forest_areas() -> pd.DataFrame:
    long = []
    for column, name in VARIABLES.items():
        frame = read_fra_variable(name).melt(id_vars="iso3", value_vars=YEARS, var_name="year", value_name=column)
        long.append(frame.set_index(["iso3", "year"]))
    areas = pd.concat(long, axis=1).reset_index()
    areas[list(VARIABLES)] = areas[list(VARIABLES)] * 1000.0  # 1000 ha -> ha

    # Gap filling, flagged row by row.
    areas["nrf_source"] = np.where(areas["nrf"].notna(), "fra", None)
    fill = areas["nrf"].isna() & areas["forest"].notna() & areas["planted"].notna()
    areas.loc[fill, "nrf"] = areas.loc[fill, "forest"] - areas.loc[fill, "planted"]
    areas.loc[fill, "nrf_source"] = "forest_minus_planted"
    fill = areas["nrf"].isna() & areas["forest"].notna()
    areas.loc[fill, "nrf"] = areas.loc[fill, "forest"]
    areas.loc[fill, "planted"] = 0.0
    areas.loc[fill, "nrf_source"] = "assumed_all_nrf"
    areas["planted"] = areas["planted"].fillna(areas["forest"] - areas["nrf"])
    areas["mangroves"] = areas["mangroves"].fillna(0.0)

    # Mangroves are counted in BCW: removed from NRF, as in the current supplement (C7).
    areas["nrf_excl_mangroves"] = (areas["nrf"] - areas["mangroves"]).clip(lower=0.0)
    areas["mangroves_exceed_nrf"] = areas["mangroves"] > areas["nrf"]
    areas["forest_excl_mangroves"] = areas["nrf_excl_mangroves"] + areas["planted"]
    areas["nrf_plus_planted_minus_forest"] = areas["nrf"] + areas["planted"] - areas["forest"]
    return areas.sort_values(["iso3", "year"]).reset_index(drop=True)


def run() -> pd.DataFrame:
    table = build_forest_areas()
    write_table(table, SUMMARY / "forest_areas.csv")
    return table
