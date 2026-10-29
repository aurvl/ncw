"""Compare published Hilmi, FRA, direct GMW 2025 and selected mangrove areas.

This is a source reconciliation audit, not a spatial intersection. National
area totals cannot establish which mangrove hectares are inside FRA forest.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
SUMMARY = ROOT / "data" / "derived"
OUT = ROOT / "data" / "outputs" / "validation"
GMW_FILE = RAW / "environmental" / "marine" / "gmw" / "gmw_v4_timeseries_4112_gmw_country_stats_corr_area_formatted.xlsx"
MANGROVE_BURIAL_TC_KM2_YR = 183.6  # Hilmi supplement table 3; Alongi 2022
GSCC_USD_PER_TCO2 = 559.6  # Hilmi 2026 published global mean, illustrative only


def build_comparison() -> pd.DataFrame:
    fra = pd.read_csv(SUMMARY / "forest_areas.csv")
    fra = fra.loc[fra["year"].astype(str) == "2025", ["iso3", "forest", "mangroves"]].copy()
    fra = fra.rename(columns={"forest": "fra_forest_ha", "mangroves": "fra_mangroves_ha"})

    hilmi = pd.read_csv(RAW / "environmental" / "marine" / "bcw" / "output" / "country_level_bcw.csv")
    hilmi = hilmi.loc[:, ["ISO", "country_name", "mangroves_area_km2"]].copy()
    hilmi = hilmi.rename(columns={"ISO": "iso3", "country_name": "hilmi_name"})
    hilmi["hilmi_mangroves_ha"] = hilmi.pop("mangroves_area_km2") * 100.0
    hilmi = hilmi.loc[hilmi["iso3"].notna()].copy()
    crosswalk = pd.read_csv(ROOT / "data" / "reference" / "territory_crosswalk.csv")
    crosswalk = crosswalk[["bcw_code", "unit_code"]].rename(columns={"bcw_code": "iso3"})
    hilmi = hilmi.merge(crosswalk, on="iso3", how="left", validate="one_to_one")
    hilmi["iso3"] = hilmi["unit_code"].fillna(hilmi["iso3"])
    hilmi = hilmi.groupby("iso3", as_index=False).agg(
        hilmi_name=("hilmi_name", "first"),
        hilmi_mangroves_ha=("hilmi_mangroves_ha", lambda values: values.sum(min_count=1)),
    )

    sheets = pd.read_excel(GMW_FILE, sheet_name=["Extent", "lower95th", "upper95th"])
    gmw_stats = sheets["Extent"].loc[:, ["iso", "cnty_name", "2025"]].copy()
    gmw_stats = gmw_stats.rename(columns={"iso": "iso3", "cnty_name": "gmw_name", "2025": "gmw_stats_2025_mangroves_ha"})
    # The source workbook contains a global total row with no ISO code.
    gmw_stats = gmw_stats.loc[gmw_stats["iso3"].notna()].copy()
    for sheet, column in [("lower95th", "gmw_lower95_ha"), ("upper95th", "gmw_upper95_ha")]:
        bounds = sheets[sheet].loc[:, ["iso", "2025"]].rename(columns={"iso": "iso3", "2025": column})
        gmw_stats = gmw_stats.merge(bounds.loc[bounds["iso3"].notna()], on="iso3", how="left", validate="one_to_one")

    gmw_direct = pd.read_csv(SUMMARY / "gmw_2025_mangrove_area_by_unit.csv")
    gmw_direct = gmw_direct[["iso3", "gmw_2025_mangrove_area_ha"]].rename(
        columns={"gmw_2025_mangrove_area_ha": "gmw_2025_direct_corrected_mangroves_ha"}
    )
    selected = pd.read_csv(SUMMARY / "bcw_mangrove_gmw_area_replacement.csv")
    selected = selected[["iso3", "selected_mangrove_area_ha", "mangrove_area_source"]]

    areas = pd.read_csv(ROOT / "data" / "outputs" / "forest_account" / "forest_area_by_biome.csv")
    tropical = areas.loc[
        (areas["variant"] == "no_overlap_removed") & (areas["biome"] == "tropical"),
        ["iso3", "area_ha"],
    ].rename(columns={"area_ha": "current_tropical_allocation_ha"})

    joined = fra.merge(hilmi, on="iso3", how="outer", validate="one_to_one")
    joined = joined.merge(gmw_stats, on="iso3", how="outer", validate="one_to_one")
    joined = joined.merge(gmw_direct, on="iso3", how="outer", validate="one_to_one")
    joined = joined.merge(selected, on="iso3", how="outer", validate="one_to_one")
    joined = joined.merge(tropical, on="iso3", how="left", validate="one_to_one")
    joined["project_bcw_mangroves_ha"] = joined["selected_mangrove_area_ha"]
    joined["fra_minus_hilmi_ha"] = joined["fra_mangroves_ha"] - joined["hilmi_mangroves_ha"]
    joined["fra_minus_gmw_ha"] = joined["fra_mangroves_ha"] - joined["gmw_2025_direct_corrected_mangroves_ha"]
    joined["gmw_minus_hilmi_ha"] = joined["gmw_2025_direct_corrected_mangroves_ha"] - joined["hilmi_mangroves_ha"]
    joined["fra_mangroves_exceed_forest"] = joined["fra_mangroves_ha"] > joined["fra_forest_ha"]
    joined["fra_mangroves_exceed_allocated_tropical"] = (
        joined["fra_mangroves_ha"] > joined["current_tropical_allocation_ha"]
    )
    return joined.sort_values("iso3", na_position="last").reset_index(drop=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    table = build_comparison()
    path = OUT / "mangrove_area_source_comparison.csv"
    table.to_csv(path, index=False)
    positive = lambda name: table[name].fillna(0).sum()  # noqa: E731
    print(f"Wrote {path}")
    sources = ["fra_mangroves_ha", "hilmi_mangroves_ha", "project_bcw_mangroves_ha", "gmw_2025_direct_corrected_mangroves_ha"]
    for name in sources:
        print(f"{name}: {positive(name):,.1f} ha")
    scenarios = pd.DataFrame({"source": sources, "mangroves_ha": [positive(name) for name in sources]})
    scenarios["burial_MtC_yr_at_fixed_rate"] = (
        scenarios["mangroves_ha"] * MANGROVE_BURIAL_TC_KM2_YR / 100.0 / 1e6
    )
    scenarios["indicative_billion_2015usd_yr_at_fixed_price"] = (
        scenarios["burial_MtC_yr_at_fixed_rate"] * 44.0 / 12.0 * GSCC_USD_PER_TCO2 / 1000.0
    )
    scenarios.to_csv(OUT / "mangrove_area_fixed_rate_scenarios.csv", index=False)
    matched = table.dropna(subset=["fra_mangroves_ha", "hilmi_mangroves_ha", "gmw_2025_direct_corrected_mangroves_ha"])
    print(f"All three sources matched by ISO3: {len(matched)} units")
    print(f"FRA mangroves > total forest: {table['fra_mangroves_exceed_forest'].sum()} units")
    print(f"FRA mangroves > allocated tropical forest: {table['fra_mangroves_exceed_allocated_tropical'].sum()} units")
    print(table.loc[table["fra_mangroves_exceed_allocated_tropical"].fillna(False),
                    ["iso3", "fra_mangroves_ha", "fra_forest_ha", "current_tropical_allocation_ha"]].to_string(index=False))


if __name__ == "__main__":
    main()
