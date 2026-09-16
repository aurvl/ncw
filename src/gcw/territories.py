"""Q: Which territories are accounted for, and how do FRA, FAOSTAT and BCW codes match?

Output: data_source/summary/territories.csv
"""

from __future__ import annotations

import pandas as pd

from .config import BCW_COUNTRY_CSV, SUMMARY
from .validation import assert_unique, read_fra_variable, write_table


def build_territories() -> pd.DataFrame:
    fra = read_fra_variable("1a_forestArea")[["iso3", "m49", "name", "regions", "subregions"]]
    fra = fra.rename(columns={"name": "fra_name", "regions": "fra_region", "subregions": "fra_subregion"})
    fra["in_fra"] = True

    bcw = pd.read_csv(BCW_COUNTRY_CSV)
    bcw = bcw.loc[bcw["ISO"].notna(), ["ISO", "country_name", "SOVEREIGN1", "Continent", "Groups", "Population", "GDP"]]
    bcw = bcw.rename(
        columns={
            "ISO": "iso3",
            "country_name": "bcw_name",
            "SOVEREIGN1": "sovereign",
            "Continent": "continent",
            "Groups": "groups",
            "Population": "population",
            "GDP": "gdp",
        }
    )
    bcw["in_bcw"] = True

    territories = fra.merge(bcw, on="iso3", how="outer", validate="one_to_one")
    territories[["in_fra", "in_bcw"]] = territories[["in_fra", "in_bcw"]].fillna(False).astype(bool)
    territories["name"] = territories["bcw_name"].fillna(territories["fra_name"])
    territories["m49"] = territories["m49"].astype("Int64")
    assert_unique(territories, ["iso3"], "territories")
    columns = [
        "iso3", "m49", "name", "in_fra", "in_bcw", "fra_name", "bcw_name", "sovereign",
        "fra_region", "fra_subregion", "continent", "groups", "population", "gdp",
    ]
    return territories[columns].sort_values("iso3").reset_index(drop=True)


def run() -> pd.DataFrame:
    table = build_territories()
    write_table(table, SUMMARY / "territories.csv")
    return table
