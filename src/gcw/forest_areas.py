"""Q: How much forest does each country have?

Output: data_source/summary/forest_areas.csv (hectares, FRA 2025, all reporting years)

Only total forest and mangroves enter the sequestration estimate (C17). Naturally regenerating
forest (NRF), planted forest and primary forest (PR) are kept as descriptive variables:
Forest = NRF + Planted and PR is a subset of NRF, so PR is never added to NRF or Planted.
"""

from __future__ import annotations

import pandas as pd

from .config import SUMMARY
from .validation import read_fra_variable, write_table

YEARS = ["1990", "2000", "2010", "2015", "2020", "2025"]
VARIABLES = {
    "forest": "1a_forestArea",
    "mangroves": "1c_mangroves",
    "nrf": "1b_naturallyRegeneratingForest",
    "planted": "1b_plantedForest",
    "primary": "1b_primary",
}


def build_forest_areas() -> pd.DataFrame:
    long = []
    for column, name in VARIABLES.items():
        frame = read_fra_variable(name).melt(id_vars="iso3", value_vars=YEARS, var_name="year", value_name=column)
        long.append(frame.set_index(["iso3", "year"]))
    areas = pd.concat(long, axis=1).reset_index()
    areas[list(VARIABLES)] = areas[list(VARIABLES)] * 1000.0  # 1000 ha -> ha
    areas["mangroves"] = areas["mangroves"].fillna(0.0)

    # Descriptive consistency flags (not used in the estimate).
    areas["nrf_plus_planted_minus_forest"] = areas["nrf"] + areas["planted"] - areas["forest"]
    areas["primary_exceeds_nrf"] = areas["primary"] > areas["nrf"]
    return areas.sort_values(["iso3", "year"]).reset_index(drop=True)


def run() -> pd.DataFrame:
    table = build_forest_areas()
    write_table(table, SUMMARY / "forest_areas.csv")
    return table
