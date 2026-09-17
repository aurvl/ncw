"""Q: Which accounting units are used, and how do FRA, FAOSTAT and BCW territories map onto them?

GCW (FRA 2025 countries) defines the units (C12). BCW territories are mapped onto them with the
validated crosswalk data_source/reference/territory_crosswalk.csv; unmapped BCW codes keep their
own unit. Both sides are kept (outer merge).

Rules for regrouped BCW parts (C12):
- BCW values and draws are summed;
- population and GDP are NOT summed (BCW copies the country figures onto each part): they come
  from the parent row, or from the main part when the country has no BCW row; only parts flagged
  `add_socioeconomics` (Taiwan) add their population and GDP;
- continent and group come from the parent row, or from the main part.

Outputs: data_source/summary/territories.csv (one row per unit),
         data_source/summary/bcw_territory_mapping.csv (one row per BCW row)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BCW_COUNTRY_CSV, SUMMARY, TERRITORY_CROSSWALK_CSV, UNIT_NAME_OVERRIDES
from .validation import assert_unique, read_fra_variable, write_table

BCW_CODES_WITHOUT_ISO = {"Joint Regimes": "BCW-JR", "Overlapping Claims": "BCW-OC"}


def read_bcw_table() -> pd.DataFrame:
    """Published BCW table with a code on every row (rows without ISO get a technical code)."""
    bcw = pd.read_csv(BCW_COUNTRY_CSV)
    bcw["bcw_code"] = bcw["ISO"].fillna(bcw["country_name"].map(BCW_CODES_WITHOUT_ISO))
    if bcw["bcw_code"].isna().any():
        raise ValueError(f"BCW rows without code: {bcw.loc[bcw['bcw_code'].isna(), 'country_name'].tolist()}")
    assert_unique(bcw, ["bcw_code"], "BCW table")
    return bcw


def bcw_mapping(bcw: pd.DataFrame) -> pd.DataFrame:
    crosswalk = pd.read_csv(TERRITORY_CROSSWALK_CSV)
    assert_unique(crosswalk, ["bcw_code"], "territory crosswalk")
    unknown = sorted(set(crosswalk["bcw_code"]) - set(bcw["bcw_code"]))
    if unknown:
        raise ValueError(f"Crosswalk codes absent from BCW: {unknown}")
    mapping = bcw[["bcw_code", "country_name"]].merge(
        crosswalk[["bcw_code", "case", "unit_code", "is_main_part", "add_socioeconomics", "decision"]],
        on="bcw_code", how="left",
    )
    mapping["unit_code"] = mapping["unit_code"].fillna(mapping["bcw_code"])
    mapping["is_main_part"] = mapping["is_main_part"].fillna(False).astype(bool)
    mapping["add_socioeconomics"] = mapping["add_socioeconomics"].fillna(False).astype(bool)
    mapping["role"] = np.select(
        [mapping["bcw_code"] == mapping["unit_code"], mapping["is_main_part"]], ["unit_row", "main_part"], "part"
    )
    mapping["case"] = mapping["case"].fillna("same code")
    return mapping.rename(columns={"country_name": "bcw_name"})


def _socioeconomics(bcw: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    rows = bcw.merge(mapping[["bcw_code", "unit_code", "role", "add_socioeconomics"]], on="bcw_code")
    records = []
    for unit, group in rows.groupby("unit_code"):
        reference = group.loc[group["role"] == "unit_row"]
        if reference.empty:
            reference = group.loc[group["role"] == "main_part"]
        if reference.empty:
            reference = group.head(1)
        ref = reference.iloc[0]
        extra = group.loc[group["add_socioeconomics"]]
        records.append({
            "iso3": unit,
            "bcw_name": ref["country_name"],
            "sovereign": ref["SOVEREIGN1"],
            "continent": ref["Continent"],
            "groups": ref["Groups"],
            "population": ref["Population"] + extra["Population"].fillna(0).sum(),
            "gdp": ref["GDP"] + extra["GDP"].fillna(0).sum() if pd.notna(ref["GDP"]) else np.nan,
            "bcw_codes": ";".join(sorted(group["bcw_code"])),
            "n_bcw_rows": len(group),
        })
    return pd.DataFrame(records)


def build_territories() -> tuple[pd.DataFrame, pd.DataFrame]:
    fra = read_fra_variable("1a_forestArea")[["iso3", "m49", "name", "regions", "subregions"]]
    fra = fra.rename(columns={"name": "fra_name", "regions": "fra_region", "subregions": "fra_subregion"})
    fra["in_fra"] = True

    bcw = read_bcw_table()
    mapping = bcw_mapping(bcw)
    units = _socioeconomics(bcw, mapping)
    units["in_bcw"] = True

    territories = fra.merge(units, on="iso3", how="outer", validate="one_to_one")
    territories[["in_fra", "in_bcw"]] = territories[["in_fra", "in_bcw"]].fillna(False).astype(bool)
    territories["n_bcw_rows"] = territories["n_bcw_rows"].fillna(0).astype(int)
    territories["name"] = territories["iso3"].map(UNIT_NAME_OVERRIDES)
    territories["name"] = territories["name"].fillna(territories["fra_name"]).fillna(territories["bcw_name"])
    territories["m49"] = territories["m49"].astype("Int64")
    assert_unique(territories, ["iso3"], "territories")
    columns = [
        "iso3", "m49", "name", "in_fra", "in_bcw", "n_bcw_rows", "bcw_codes", "fra_name", "bcw_name", "sovereign",
        "fra_region", "fra_subregion", "continent", "groups", "population", "gdp",
    ]
    return territories[columns].sort_values("iso3").reset_index(drop=True), mapping


def run() -> pd.DataFrame:
    table, mapping = build_territories()
    write_table(mapping, SUMMARY / "bcw_territory_mapping.csv")
    write_table(table, SUMMARY / "territories.csv")
    return table
