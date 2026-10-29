"""Build the static data files used by the web explorer.

Inputs are repository outputs only (no external data):
- results/validation/country_level_results_master.csv  (unit-level accounts)
- results/tables/manuscript/Supplementary_country_level_accounts_2024.csv  (GCW/GDP 2024)
- results/tables/manuscript/Table1_global_carbon_wealth.csv  (global totals)
- data/raw/geospatial/boundaries/ne_10m_admin_0_map_units.zip  (land polygons)
- data/raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp  (EEZ polygons)

Outputs, written to web/public/data/:
- units.json   one record per accounting unit; values are copied from the current master,
               plus bcw_gdp_2024_pct (BCW / GDP 2024)
- global.json  Table 1 totals
- aggregates.json  totals by region and economic group, checked against the paper tables
- land.geojson, eez.geojson  simplified geometries keyed by unit code

Run from the repository root:  python web/scripts/build_web_data.py
"""

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "data"
BOUNDARIES = ROOT / "data" / "raw" / "geospatial" / "boundaries"

# Same Natural Earth to study-unit aliases as notebook 08.
NE_TO_UNIT = {"SDS": "SSD", "SAH": "ESH", "PSX": "PSE", "HKG": "CHN", "MAC": "CHN", "TWN": "CHN",
              "CYN": "CYP", "SOL": "SOM", "ALD": "FIN", "ATC": "AUS", "IOA": "AUS"}

TEXT_FIELDS = [
    "UNIT_CODE", "name", "continent", "region", "groups", "sovereign", "unit_class",
    "overlap_status", "busch_scenario_status", "emissions_2024_match_status", "mangrove_area_source",
]
BOOL_FIELDS = ["has_gcw", "has_bcw", "desk_study", "reported_deforestation",
               "busch_curve_available"]
NUMERIC_FIELDS = [
    # Wealth accounts (US$2015 per year)
    "ncw_usd2015_yr_mean", "ncw_usd2015_yr_p05", "ncw_usd2015_yr_p95",
    "gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95",
    "bcw_usd2015_yr_mean", "bcw_usd2015_yr_p05", "bcw_usd2015_yr_p95",
    "forest_share_of_ncw", "gcw_share_global_pct",
    # Forest account
    "uptake_tco2_yr_mean", "uptake_tco2_yr_p05", "uptake_tco2_yr_p95",
    "fra_total_forest_area_2025_ha", "fra_primary_forest_2025_ha", "fra_planted_forest_2025_ha",
    "fra_other_wooded_land_2025_ha",
    "forest_area_allocated_tropical_ha", "forest_area_allocated_subtropical_ha",
    "forest_area_allocated_temperate_ha", "forest_area_allocated_boreal_ha",
    "forest_rate_tropical_tC_ha_yr", "forest_rate_subtropical_tC_ha_yr",
    "forest_rate_temperate_tC_ha_yr", "forest_rate_boreal_tC_ha_yr",
    "forest_additions_tropical_tCO2_yr", "forest_additions_subtropical_tCO2_yr",
    "forest_additions_temperate_tCO2_yr", "forest_additions_boreal_tCO2_yr",
    "fra_mangroves_2025_ha", "documented_forest_mangrove_area_ha",
    # Marine account
    "mangrove_area_selected_ha", "selected_mangrove_uptake_tCO2_yr_mean",
    "saltmarsh_area_km2_hilmi_source", "seagrass_area_km2_hilmi_source",
    "saltmarsh_uptake_tC_yr_source_mean", "seagrass_uptake_tC_yr_source_mean",
    "coastal_component_uptake_tCO2_yr_current_area", "open_ocean_bcp_tCO2_yr_source",
    "bcw_source_eez_area_km2",
    # Economy and emissions
    "population_2024", "gdp_2015usd_2024", "gdp_per_capita_2024", "gcw_gdp_2024_pct", "bcw_gdp_2024_pct",
    "co2_emissions_tco2_2024", "gcw_additions_to_emissions_ratio",
    "gcw_accounting_balance_mean_tco2_yr", "ncw_accounting_balance_mean_tco2_yr",
    # Deforestation
    "loss_tco2_mean", "loss_value_usd2015_yr_mean", "erosion_pct_of_gcw", "loss_pct_of_gdp",
    # Finance
    "our_2pct_gcw_allocation_usd2015_yr",
]


def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def build_units():
    master = pd.read_csv(ROOT / "results/validation/country_level_results_master.csv", low_memory=False)
    accounts = pd.read_csv(ROOT / "results/tables/manuscript/Supplementary_country_level_accounts_2024.csv",
                           low_memory=False)
    master = master.merge(accounts[["UNIT_CODE", "gcw_gdp_2024_pct"]], on="UNIT_CODE", how="left")
    if "fra_other_wooded_land_2025_ha" not in master.columns:
        master["fra_other_wooded_land_2025_ha"] = np.nan
    if master["UNIT_CODE"].duplicated().any():
        raise ValueError("UNIT_CODE must be unique")
    has_account = master["has_gcw"].fillna(False).astype(bool) | master["has_bcw"].fillna(False).astype(bool)
    expected_ncw = master["gcw_usd2015_yr_mean"].fillna(0) + master["bcw_usd2015_yr_mean"].fillna(0)
    if not np.allclose(master.loc[has_account, "ncw_usd2015_yr_mean"], expected_ncw.loc[has_account],
                       rtol=1e-9, atol=1):
        raise ValueError("Current master NCW does not equal available GCW + BCW, with missing components as zero")
    if master.loc[~has_account, "ncw_usd2015_yr_mean"].notna().any():
        raise ValueError("NCW must remain missing when neither account is available")
    for field in BOOL_FIELDS:
        master[field] = master[field].astype(str).str.lower().map({"true": True, "false": False})
    # BCW share of GDP, defined exactly like the table's gcw_gdp_2024_pct (100 x account / GDP 2024).
    gdp = master["gdp_2015usd_2024"].where(master["gdp_2015usd_2024"] > 0)
    if (100 * master["gcw_usd2015_yr_mean"] / gdp - master["gcw_gdp_2024_pct"]).abs().max() > 1e-9:
        raise ValueError("gcw_gdp_2024_pct no longer equals 100 x GCW / GDP 2024")
    master["bcw_gdp_2024_pct"] = 100 * master["bcw_usd2015_yr_mean"] / gdp
    records = []
    for row in master[TEXT_FIELDS + BOOL_FIELDS + NUMERIC_FIELDS].itertuples(index=False):
        record = {k: clean(v) for k, v in zip(TEXT_FIELDS + BOOL_FIELDS + NUMERIC_FIELDS, row)}
        for k in NUMERIC_FIELDS:
            if record[k] is not None:
                record[k] = float(f"{record[k]:.6g}")
        records.append(record)
    return master, records


def build_global(master):
    table1 = pd.read_csv(ROOT / "results/tables/manuscript/Table1_global_carbon_wealth.csv")
    keys = {"Green carbon wealth": "gcw", "Blue carbon wealth": "bcw", "Natural carbon wealth": "ncw"}
    out = {}
    for row in table1.itertuples(index=False):
        out[keys[row.component]] = {
            "mean_trillion": row.value_mean_trillion_usd2015_yr,
            "p05_trillion": row.value_p05_trillion_usd2015_yr,
            "p95_trillion": row.value_p95_trillion_usd2015_yr,
            "share_pct": row.share_of_ncw_pct,
        }
    out["counts"] = {"gcw_units": int(master["has_gcw"].sum()), "ncw_units": int(master["ncw_usd2015_yr_mean"].notna().sum())}
    # With missing components counted as zero, unit-level NCW must sum to the additive global NCW.
    ncw_sum = master["ncw_usd2015_yr_mean"].sum() / 1e12
    if abs(ncw_sum - out["ncw"]["mean_trillion"]) > 1e-6:
        raise ValueError(f"NCW unit sum {ncw_sum} differs from Table 1 {out['ncw']['mean_trillion']}")
    # Consistency check: unit-level GCW must sum to the Table 1 total.
    gcw_sum = master["gcw_usd2015_yr_mean"].sum() / 1e12
    if abs(gcw_sum - out["gcw"]["mean_trillion"]) > 1e-6:
        raise ValueError(f"GCW unit sum {gcw_sum} differs from Table 1 {out['gcw']['mean_trillion']}")
    return out


def build_aggregates(master):
    """Totals by region and by economic group, summed from unit means as in the paper tables.

    NCW uses the additive rule (missing component = 0), like `ncw_trillion_usd2015_yr` in
    Supplementary_region_profiles_2024.csv. Each sum is checked against the paper table that
    reports it; counts say how many units contribute to each total.
    """
    tables = ROOT / "results/tables/manuscript"
    regions = pd.read_csv(tables / "Supplementary_region_profiles_2024.csv").set_index("region")
    table2 = pd.read_csv(tables / "Table2_geographic_economic_profiles.csv").set_index("group")
    finance = pd.read_csv(tables / "Supplementary_Figure4_finance_allocations_by_group.csv").set_index("group_display")
    world_ncw = master["ncw_usd2015_yr_mean"].sum()
    sums = {
        "gcw_usd2015_yr": "gcw_usd2015_yr_mean", "bcw_usd2015_yr": "bcw_usd2015_yr_mean", "ncw_usd2015_yr": "ncw_usd2015_yr_mean",
        "forest_additions_tco2_yr": "uptake_tco2_yr_mean", "forest_area_2025_ha": "fra_total_forest_area_2025_ha",
        "mangrove_area_selected_ha": "mangrove_area_selected_ha", "emissions_tco2_2024": "co2_emissions_tco2_2024",
        "capacity_loss_tco2_yr": "loss_tco2_mean", "our_2pct_gcw_allocation_usd2015_yr": "our_2pct_gcw_allocation_usd2015_yr",
    }

    def profile(rows, key):
        out = {"key": key, "units": int(len(rows)), "units_gcw": int(rows["has_gcw"].eq(True).sum()),
               "units_bcw": int(rows["has_bcw"].eq(True).sum()),
               "units_both": int((rows["has_gcw"].eq(True) & rows["has_bcw"].eq(True)).sum())}
        for name, col in sums.items():
            out[name] = float(rows[col].sum()) if rows[col].notna().any() else None
            out[f"{name}_n"] = int(rows[col].notna().sum())
        out["share_world_ncw_pct"] = 100 * rows["ncw_usd2015_yr_mean"].sum() / world_ncw
        return out

    def check(name, got, expected, tol=1e-6):
        if not math.isclose(got, expected, rel_tol=tol, abs_tol=1e-9):
            raise ValueError(f"{name}: {got} differs from paper table {expected}")

    out = {"regions": [], "groups": []}
    for region, rows in master.dropna(subset=["region"]).groupby("region"):
        p = profile(rows, region)
        if region in regions.index:
            ref = regions.loc[region]
            for field, col in (("gcw_usd2015_yr", "gcw_trillion_usd2015_yr"), ("bcw_usd2015_yr", "bcw_trillion_usd2015_yr"),
                               ("ncw_usd2015_yr", "ncw_trillion_usd2015_yr")):
                if pd.notna(ref[col]):
                    check(f"{region} {field}", (p[field] or 0) / 1e12, ref[col])
            p["median_gcw_gdp_2024_pct"] = None if pd.isna(ref["median_gcw_gdp_2024_pct"]) else float(ref["median_gcw_gdp_2024_pct"])
        out["regions"].append(p)
    for group, rows in master.dropna(subset=["groups"]).groupby("groups"):
        p = profile(rows, group)
        ref = table2.loc[group]
        check(f"{group} gcw", p["gcw_usd2015_yr"] / 1e12, ref["gcw_trillion_usd2015_yr"])
        check(f"{group} 2% GCW allocation", p["our_2pct_gcw_allocation_usd2015_yr"], finance.loc[group, "total_usd2015_yr"])
        p["median_gcw_gdp_2024_pct"] = float(ref["median_gcw_gdp_2024_pct"])
        for col in ("green_dominant_units", "mixed_units", "blue_dominant_units"):
            p[col] = int(ref[col])
        out["groups"].append(p)
    return out


def write_geojson(frame, path, tolerance, precision=3):
    frame = frame.copy()
    frame["geometry"] = frame.geometry.make_valid().simplify(tolerance, preserve_topology=True)
    frame = frame.loc[~frame.geometry.is_empty]
    features = []
    for code, geom in zip(frame["code"], frame.geometry):
        geo = json.loads(json.dumps(mapping(geom)), parse_float=lambda x: round(float(x), precision))
        features.append({"type": "Feature", "properties": {"code": code}, "geometry": geo})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
                    encoding="utf-8")
    return path.stat().st_size / 1e6


def build_geometries(units):
    land = gpd.read_file("/vsizip/" + (BOUNDARIES / "ne_10m_admin_0_map_units.zip").as_posix()
                         + "/ne_10m_admin_0_map_units.shp")
    land["code"] = [gu if gu in units else iso if iso in units else NE_TO_UNIT.get(adm, adm)
                    for gu, iso, adm in zip(land["GU_A3"], land["ISO_A3"], land["ADM0_A3"])]
    land = land.loc[land["code"] != "ATA"].dissolve("code", as_index=False)[["code", "geometry"]].to_crs("EPSG:4326")
    eez = gpd.read_file(BOUNDARIES / "EEZ_land_union_v4_202410.shp")
    eez = eez.set_crs("EPSG:4326") if eez.crs is None else eez.to_crs("EPSG:4326")
    eez = eez.rename(columns={"ISO_TER1": "code"})
    eez = eez.loc[eez["code"].isin(units)].dissolve("code", as_index=False)[["code", "geometry"]]
    return (write_geojson(land, OUT / "land.geojson", 0.02),
            write_geojson(eez, OUT / "eez.geojson", 0.05, precision=2),
            sorted(set(land["code"]) & units), sorted(set(eez["code"])))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master, records = build_units()
    units = {r["UNIT_CODE"] for r in records}
    (OUT / "units.json").write_text(json.dumps(records, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (OUT / "global.json").write_text(json.dumps(build_global(master), indent=1), encoding="utf-8")
    (OUT / "aggregates.json").write_text(json.dumps(build_aggregates(master), indent=1), encoding="utf-8")
    land_mb, eez_mb, land_codes, eez_codes = build_geometries(units)
    gcw_units = {r["UNIT_CODE"] for r in records if r["has_gcw"]}
    print(f"units.json: {len(records)} units | land.geojson {land_mb:.1f} MB | eez.geojson {eez_mb:.1f} MB")
    print(f"GCW units without land polygon: {sorted(gcw_units - set(land_codes))}")
    print(f"BCW units without EEZ polygon: {sorted({r['UNIT_CODE'] for r in records if r['has_bcw']} - set(eez_codes))}")


if __name__ == "__main__":
    main()
