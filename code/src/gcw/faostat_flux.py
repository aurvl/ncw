"""Q (Route A): What net forest CO2 flux does each country report to FAOSTAT?

Outputs (data/derived/):
- faostat_forest_flux_annual.csv : annual net flux per country (tCO2/yr, removals positive)
- forest_uptake_faostat.csv      : mean over FAOSTAT_PERIOD, with interannual spread

This is a net flux (removals minus losses); negative values mean the forest is a net source.
"""

from __future__ import annotations

import zipfile

import pandas as pd

from .config import (
    FAOSTAT_ELEMENT, FAOSTAT_FOREST_CSV, FAOSTAT_FOREST_ZIP, FAOSTAT_ITEM, FAOSTAT_PERIOD, FAOSTAT_SOURCE, SUMMARY,
)
from .validation import assert_unique, write_table


def read_annual(territories: pd.DataFrame) -> pd.DataFrame:
    with zipfile.ZipFile(FAOSTAT_FOREST_ZIP) as archive:
        raw = pd.read_csv(archive.open(FAOSTAT_FOREST_CSV), encoding="latin1")
    selected = raw.loc[
        (raw["Item"] == FAOSTAT_ITEM) & (raw["Element"] == FAOSTAT_ELEMENT) & (raw["Source"] == FAOSTAT_SOURCE)
    ].copy()
    if (selected["Unit"] != "kt").any():
        raise ValueError("Unexpected FAOSTAT unit; expected kt.")
    selected["m49"] = pd.to_numeric(selected["Area Code (M49)"].str.lstrip("'"), errors="coerce").astype("Int64")
    codes = territories.dropna(subset=["m49"])[["m49", "iso3"]]
    annual = selected.merge(codes, on="m49", how="inner", validate="many_to_one")
    # FAOSTAT reports removals as negative emissions: flip sign so removals are positive.
    annual["net_uptake_tco2_yr"] = -annual["Value"] * 1000.0
    annual = annual.rename(columns={"Year": "year", "Area": "faostat_name", "Flag": "flag"})
    columns = ["iso3", "m49", "faostat_name", "year", "net_uptake_tco2_yr", "flag"]
    annual = annual[columns].sort_values(["iso3", "year"]).reset_index(drop=True)
    assert_unique(annual, ["iso3", "year"], "FAOSTAT annual flux")
    return annual


def period_mean(annual: pd.DataFrame) -> pd.DataFrame:
    start, end = FAOSTAT_PERIOD
    period = annual.loc[annual["year"].between(start, end)]
    result = period.groupby("iso3", as_index=False).agg(
        net_uptake_tco2_yr=("net_uptake_tco2_yr", "mean"),
        interannual_sd=("net_uptake_tco2_yr", "std"),
        min_year_value=("net_uptake_tco2_yr", "min"),
        max_year_value=("net_uptake_tco2_yr", "max"),
        n_years=("year", "nunique"),
    )
    result["period"] = f"{start}-{end}"
    return result


def run(territories: pd.DataFrame) -> pd.DataFrame:
    annual = read_annual(territories)
    write_table(annual, SUMMARY / "faostat_forest_flux_annual.csv")
    mean = period_mean(annual)
    write_table(mean, SUMMARY / "forest_uptake_faostat.csv")
    return mean
