"""Extract and harmonise 2024 emissions, population and GDP for the paper units.

The script keeps source observations separate from the older BCW 2023 series.
Missing country or territory values are never filled with zeros or parent-country
values. It creates a fully traceable crosswalk and coverage audit.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import pycountry


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "economic" / "socioeconomics_2024"
SUMMARY = ROOT / "data" / "derived"
OUT = ROOT / "results" / "validation"
GCB_C_TO_CO2 = 3.664  # conversion explicitly stated in the GCB 2025 workbook

AGGREGATES = {
    "KP Annex B", "Non KP Annex B", "OECD", "Non-OECD", "EU27", "Africa",
    "Asia", "Central America", "Europe", "Middle East", "North America",
    "Oceania", "South America", "International Shipping",
    "International Aviation", "Statistical Difference", "World",
}


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


GCB_ALIASES = {
    _norm("Bonaire, Saint Eustatius and Saba"): "BES",
    _norm("Brunei Darussalam"): "BRN",
    _norm("Cape Verde"): "CPV",
    _norm("Congo"): "COG",
    _norm("Democratic Republic of the Congo"): "COD",
    _norm("Cote d'Ivoire"): "CIV",
    _norm("Czechia"): "CZE",
    _norm("Faeroe Islands"): "FRO",
    _norm("Micronesia (Federated States of)"): "FSM",
    _norm("Hong Kong"): "HKG",
    _norm("Kosovo"): "XKX",
    _norm("Luxembourg"): "LUX",
    _norm("Macao"): "MAC",
    _norm("North Macedonia"): "MKD",
    _norm("Mauritius"): "MUS",
    _norm("State of Palestine"): "PSE",
    _norm("Sint Maarten (Dutch part)"): "SXM",
    _norm("Somalia"): "SOM",
    _norm("Eswatini"): "SWZ",
    _norm("Timor-Leste"): "TLS",
    _norm("Turkiye"): "TUR",
    _norm("Tuerkiye"): "TUR",
    _norm("T?rkiye"): "TUR",
    _norm("USA"): "USA",
    _norm("Wallis and Futuna Islands"): "WLF",
    _norm("Russia"): "RUS",
    _norm("Saint Helena"): "SHN",
}


def _gcb_iso3(name: str) -> str | None:
    key = _norm(name)
    if key in GCB_ALIASES:
        return GCB_ALIASES[key]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None


def _read_wdi(filename: str) -> tuple[dict[str, float], dict]:
    payload = json.loads((RAW / filename).read_text(encoding="utf-8"))
    metadata, rows = payload
    values = {
        str(row["countryiso3code"]): float(row["value"])
        for row in rows
        if row.get("countryiso3code") and row.get("value") is not None
    }
    return values, metadata


def extract_gcb() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = RAW / "national_fossil_carbon_emissions_GCB2025.xlsx"
    sheet = pd.read_excel(path, sheet_name="Territorial Emissions", header=None)
    if str(sheet.iloc[9, 0]).strip() != "MtC/yr":
        raise ValueError("Unexpected unit/header in GCB 2025 Territorial Emissions sheet")
    year_rows = {
        int(float(row.iloc[0])): row
        for _, row in sheet.iterrows()
        if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip().isdigit()
    }
    if 2023 not in year_rows or 2024 not in year_rows:
        raise ValueError("GCB workbook does not contain both 2023 and 2024 rows")

    names = sheet.iloc[11, 1:]
    records = []
    for column, raw_name in enumerate(names, start=1):
        if pd.isna(raw_name):
            continue
        name = str(raw_name).strip()
        aggregate = _norm(name) in {_norm(item) for item in AGGREGATES}
        iso3 = None if aggregate else _gcb_iso3(name)
        c2023 = pd.to_numeric(pd.Series([year_rows[2023].iloc[column]]), errors="coerce").iloc[0]
        c2024 = pd.to_numeric(pd.Series([year_rows[2024].iloc[column]]), errors="coerce").iloc[0]
        records.append({
            "gcb_name": name,
            "gcb_column": column + 1,
            "iso3": iso3,
            "is_aggregate": aggregate,
            "gcb_2023_mtC_yr": c2023,
            "gcb_2024_mtC_yr": c2024,
            "gcb_2023_mtco2_yr": c2023 * GCB_C_TO_CO2 if pd.notna(c2023) else float("nan"),
            "gcb_2024_mtco2_yr": c2024 * GCB_C_TO_CO2 if pd.notna(c2024) else float("nan"),
        })
    source = pd.DataFrame(records)
    named = source.loc[~source["is_aggregate"]].copy()
    if named["iso3"].isna().any():
        missing = named.loc[named["iso3"].isna(), "gcb_name"].tolist()
        raise ValueError(f"Unmapped GCB country/territory names: {missing}")
    duplicates = named.loc[named["iso3"].duplicated(keep=False), ["gcb_name", "iso3"]]
    if not duplicates.empty:
        raise ValueError(f"GCB country names map to duplicate ISO3 codes:\n{duplicates}")
    return source, named


def build() -> tuple[pd.DataFrame, dict]:
    SUMMARY.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    units = pd.read_csv(ROOT / "results" / "country_level_gcw.csv")
    gcb_all, gcb = extract_gcb()
    population, pop_meta = _read_wdi("wb_population_2024.json")
    gdp, gdp_meta = _read_wdi("wb_gdp_constant_2015_2024.json")

    gcb_all["mapped_to_study_unit"] = gcb_all["iso3"].isin(set(units["iso3"]))
    gcb_all.to_csv(SUMMARY / "gcb2025_national_fossil_emissions_2023_2024_by_entity.csv", index=False)

    gcb_unit = gcb.loc[gcb["iso3"].isin(set(units["iso3"])), [
        "iso3", "gcb_name", "gcb_2023_mtC_yr", "gcb_2024_mtC_yr",
        "gcb_2023_mtco2_yr", "gcb_2024_mtco2_yr",
    ]].copy()
    if gcb_unit["iso3"].duplicated().any():
        raise AssertionError("Duplicate GCB emissions after country-to-unit mapping")

    socio = units[["iso3", "name", "population", "gdp", "gcw_usd2015_yr_mean", "uptake_tco2_yr_mean"]].copy()
    socio = socio.rename(columns={
        "population": "population_bcw_reference",
        "gdp": "gdp_2015usd_bcw_reference",
    })
    socio = socio.merge(gcb_unit, on="iso3", how="left", validate="one_to_one")
    socio["population_2024"] = socio["iso3"].map(population)
    socio["gdp_2015usd_2024"] = socio["iso3"].map(gdp)
    socio["co2_emissions_tco2_2024"] = socio["gcb_2024_mtco2_yr"] * 1_000_000
    socio["co2_emissions_tco2_2023_gcb2025"] = socio["gcb_2023_mtco2_yr"] * 1_000_000
    socio["gdp_per_capita_2024"] = socio["gdp_2015usd_2024"] / socio["population_2024"]
    socio["emissions_2024_match_status"] = socio["gcb_name"].notna().map({True: "direct GCB country/territory", False: "no directly matched GCB row"})
    socio.to_csv(SUMMARY / "socioeconomic_2024_by_unit.csv", index=False)

    comparison = socio.loc[socio["co2_emissions_tco2_2023_gcb2025"].notna() & socio["co2_emissions_tco2_2024"].notna(), [
        "iso3", "name", "gcb_name", "co2_emissions_tco2_2023_gcb2025", "co2_emissions_tco2_2024",
    ]].copy()
    comparison["absolute_change_tco2"] = comparison["co2_emissions_tco2_2024"] - comparison["co2_emissions_tco2_2023_gcb2025"]
    comparison["pct_change"] = 100 * comparison["absolute_change_tco2"] / comparison["co2_emissions_tco2_2023_gcb2025"].replace(0, pd.NA)
    comparison.to_csv(OUT / "gcb2025_emissions_change_2023_2024_by_unit.csv", index=False)

    old_bcw = pd.read_csv(ROOT / "data" / "raw" / "environmental" / "marine" / "bcw" / "output" / "country_level_bcw.csv")
    territories = pd.read_csv(ROOT / "data" / "derived" / "territories.csv")
    code_to_unit: dict[str, str] = {}
    for _, row in territories.dropna(subset=["bcw_codes"]).iterrows():
        for code in str(row["bcw_codes"]).split(";"):
            code_to_unit[code] = row["iso3"]
    old_bcw["study_iso3"] = old_bcw["ISO"].astype(str).map(code_to_unit)
    old_bcw = old_bcw.dropna(subset=["study_iso3"]).sort_values("CO2_emissions_2023", ascending=False)
    old_bcw = old_bcw.groupby("study_iso3", as_index=False).first()[["study_iso3", "CO2_emissions_2023"]]
    vintage = socio.merge(old_bcw, left_on="iso3", right_on="study_iso3", how="left")
    vintage = vintage.loc[vintage["CO2_emissions_2023"].notna() & vintage["co2_emissions_tco2_2023_gcb2025"].notna()].copy()
    vintage["gcb2025_2023_minus_bcw2023_tco2"] = vintage["co2_emissions_tco2_2023_gcb2025"] - vintage["CO2_emissions_2023"]
    vintage["pct_difference"] = 100 * vintage["gcb2025_2023_minus_bcw2023_tco2"] / vintage["CO2_emissions_2023"].replace(0, pd.NA)
    vintage[["iso3", "name", "gcb_name", "CO2_emissions_2023", "co2_emissions_tco2_2023_gcb2025", "gcb2025_2023_minus_bcw2023_tco2", "pct_difference"]].to_csv(
        OUT / "gcb2025_2023_vintage_vs_bcw_2023_by_unit.csv", index=False
    )

    common = socio[["co2_emissions_tco2_2024", "population_2024", "gdp_2015usd_2024"]].notna().all(axis=1)
    summary = {
        "analysis_year": 2024,
        "study_units": int(len(units)),
        "gcb_2025_national_entities": int((~gcb_all["is_aggregate"]).sum()),
        "gcb_entities_mapped_to_study_units": int(gcb_all["mapped_to_study_unit"].sum()),
        "emissions_2024_nonmissing": int(socio["co2_emissions_tco2_2024"].notna().sum()),
        "population_2024_nonmissing": int(socio["population_2024"].notna().sum()),
        "gdp_2024_nonmissing": int(socio["gdp_2015usd_2024"].notna().sum()),
        "common_emissions_population_gdp_2024": int(common.sum()),
        "population_wdi_lastupdated": pop_meta.get("lastupdated"),
        "gdp_wdi_lastupdated": gdp_meta.get("lastupdated"),
        "gcb_conversion_factor_mtco2_per_mtc": GCB_C_TO_CO2,
        "gcb_country_rows_unmapped_to_study": gcb_all.loc[(~gcb_all["is_aggregate"]) & (~gcb_all["mapped_to_study_unit"]), "gcb_name"].tolist(),
        "study_units_without_gcb_emissions": socio.loc[socio["co2_emissions_tco2_2024"].isna(), ["iso3", "name"]].to_dict("records"),
        "study_units_without_population_2024": socio.loc[socio["population_2024"].isna(), ["iso3", "name"]].to_dict("records"),
        "study_units_without_gdp_2024": socio.loc[socio["gdp_2015usd_2024"].isna(), ["iso3", "name"]].to_dict("records"),
        "gcb2025_2023_vs_bcw2023_overlap_n": int(len(vintage)),
        "gcb2025_2023_vs_bcw2023_median_abs_pct_difference": float(vintage["pct_difference"].abs().median()),
        "gcb2025_2023_vs_bcw2023_pearson_r": float(vintage[["CO2_emissions_2023", "co2_emissions_tco2_2023_gcb2025"]].corr().iloc[0, 1]),
        "notes": [
            "GCB fossil and industrial-process CO2 is national territorial emissions; land-use change is not included in this series.",
            "GCB source rows use MtC/year. Conversion uses the 3.664 factor printed in the GCB 2025 workbook.",
            "World Bank WDI population is a midyear estimate; GDP is constant 2015 US dollars.",
            "No country/territory emissions are imputed from a sovereign parent or filled with zero.",
            "Debt is not downloaded or used for this spatial analysis.",
        ],
    }
    (OUT / "socioeconomic_2024_coverage_audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return socio, summary


def main() -> None:
    socio, summary = build()
    print(json.dumps({
        "rows": len(socio),
        "emissions_2024_nonmissing": summary["emissions_2024_nonmissing"],
        "population_2024_nonmissing": summary["population_2024_nonmissing"],
        "gdp_2024_nonmissing": summary["gdp_2024_nonmissing"],
        "common_2024": summary["common_emissions_population_gdp_2024"],
        "gcb2025_2023_vs_bcw2023_overlap_n": summary["gcb2025_2023_vs_bcw2023_overlap_n"],
        "median_abs_pct_difference": summary["gcb2025_2023_vs_bcw2023_median_abs_pct_difference"],
        "pearson_r": summary["gcb2025_2023_vs_bcw2023_pearson_r"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
