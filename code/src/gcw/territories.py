"""Q: Which accounting units are used, and how do FRA, FAOSTAT and BCW territories map onto them?

GCW (FRA 2025 countries) defines the units. BCW territories are mapped onto them with the
validated crosswalk data/reference/territory_crosswalk.csv; unmapped BCW codes keep their
own unit. Both sides are kept (outer merge).

Rules for regrouped BCW parts:
- BCW values and draws are summed;
- population and GDP are NOT summed (BCW copies the country figures onto each part): they come
  from the parent row, or from the main part when the country has no BCW row; only parts flagged
  `add_socioeconomics` (Taiwan) add their population and GDP;
- continent and group come from the parent row, or from the main part.

Outputs: data/derived/territories.csv (one row per unit),
         data/derived/bcw_territory_mapping.csv (one row per BCW row)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pycountry

from .config import BCW_COUNTRY_CSV, ECONOMIC_GROUP_OVERRIDES_CSV, SUMMARY, TERRITORY_CROSSWALK_CSV, UNIT_NAME_OVERRIDES
from .validation import assert_unique, read_fra_variable, write_table

BCW_CODES_WITHOUT_ISO = {"Joint Regimes": "BCW-JR", "Overlapping Claims": "BCW-OC"}


def _valid_iso3(unit_code: str) -> str | None:
    """Retain an ISO 3166 alpha-3 code only when the unit key itself is valid."""
    return unit_code if pycountry.countries.get(alpha_3=unit_code) is not None else None


def _complete_economic_groups(
    territories: pd.DataFrame, bcw: pd.DataFrame, overrides: pd.DataFrame,
) -> pd.DataFrame:
    """Keep source groups, then use the source sovereign, then explicit conventions."""
    result = territories.copy()
    source_groups = bcw[["country_name", "Groups"]].dropna(subset=["Groups"])
    conflicts = source_groups.groupby("country_name")["Groups"].nunique()
    if conflicts.gt(1).any():
        raise ValueError(f"Conflicting BCW sovereign groups: {conflicts[conflicts.gt(1)].index.tolist()}")
    sovereign_groups = source_groups.drop_duplicates("country_name").set_index("country_name")["Groups"]

    result["group_source"] = pd.NA
    direct = result["groups"].notna()
    result.loc[direct, "group_source"] = "published_unit"

    inherited_group = result["sovereign"].map(sovereign_groups)
    inherited = result["groups"].isna() & inherited_group.notna()
    result.loc[inherited, "groups"] = inherited_group.loc[inherited]
    result.loc[inherited, "group_source"] = "sovereign_fallback"

    override_groups = result["iso3"].map(overrides.set_index("iso3")["groups"])
    conflict = override_groups.notna() & result["groups"].notna() & override_groups.ne(result["groups"])
    if conflict.any():
        raise ValueError(f"Economic group overrides conflict with the source hierarchy: {result.loc[conflict, 'iso3'].tolist()}")
    manual = result["groups"].isna() & override_groups.notna()
    result.loc[manual, "groups"] = override_groups.loc[manual]
    result.loc[manual, "group_source"] = "researcher_convention"
    result["group_source"] = result["group_source"].fillna("unclassified")
    return result


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
    overrides = pd.read_csv(ECONOMIC_GROUP_OVERRIDES_CSV)
    assert_unique(overrides, ["iso3"], "economic group overrides")
    unknown = sorted(set(overrides["iso3"]) - set(territories["iso3"]))
    if unknown:
        raise ValueError(f"Economic group overrides have unknown units: {unknown}")
    territories = _complete_economic_groups(territories, bcw, overrides)
    # FRA supplies geographic regions for the two units whose BCW continent is blank.
    territories["continent"] = territories["continent"].fillna(territories["fra_region"])
    territories["region"] = territories["continent"]
    territories["UNIT_CODE"] = territories["iso3"]
    territories["ISO3"] = territories["UNIT_CODE"].map(_valid_iso3)
    territories[["in_fra", "in_bcw"]] = territories[["in_fra", "in_bcw"]].fillna(False).astype(bool)
    territories["n_bcw_rows"] = territories["n_bcw_rows"].fillna(0).astype(int)
    territories["name"] = territories["iso3"].map(UNIT_NAME_OVERRIDES)
    territories["name"] = territories["name"].fillna(territories["fra_name"]).fillna(territories["bcw_name"])
    territories["m49"] = territories["m49"].astype("Int64")
    assert_unique(territories, ["iso3"], "territories")
    columns = [
        "iso3", "UNIT_CODE", "ISO3", "m49", "name", "in_fra", "in_bcw", "n_bcw_rows", "bcw_codes", "fra_name", "bcw_name", "sovereign",
        "fra_region", "fra_subregion", "continent", "region", "groups", "group_source", "population", "gdp",
    ]
    return territories[columns].sort_values("iso3").reset_index(drop=True), mapping


def run() -> pd.DataFrame:
    table, mapping = build_territories()
    write_table(mapping, SUMMARY / "bcw_territory_mapping.csv")
    write_table(table, SUMMARY / "territories.csv")
    return table
