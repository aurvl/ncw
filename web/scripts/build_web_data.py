"""Build the static data files used by the web explorer.

Called at the end of code/scripts/main.py (skip with --skip-web) and runnable on its own.
Inputs are repository outputs only (no external data):
- data/derived/validation/country_level_results_master.csv  (unit-level accounts)
- results/tables/manuscript/Supplementary_country_level_accounts_2024.csv  (GCW/GDP 2024)
- results/tables/manuscript/Table1_global_carbon_wealth.csv  (global totals)
- results/tables/01_bcw_hilmi_updated.csv  (BCW source records and their accounting unit)
- results/tables/05_restoration_costs_by_entity.csv, 06_restoration_supply_curves.csv  (forest restoration)
- data/raw/geospatial/boundaries/ne_10m_admin_0_map_units.zip  (land polygons)
- data/raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp  (EEZ polygons)

The accounts do not share one entity list. GCW and NCW use the 266 accounting units, drawn on
land polygons. BCW starts from the 296 source records of Hilmi et al., each counted in one
accounting unit (e.g. Trindade in Brazil), so the EEZ geometry is keyed by source record and
carries its unit. Forest restoration is national (ISO3) and only covers countries with inputs.

Outputs, written to web/public/data/:
- units.json        one record per accounting unit, copied from the master, plus bcw_gdp_2024_pct
- global.json       Table 1 totals
- aggregates.json   totals by region and economic group, checked against the paper tables
- bcw_sources.json  BCW source records: code, territory, role and accounting unit
- restoration.json  forest-restoration results by unit for the soil scenarios shown on the site
- curves/<ISO3>.json  restoration supply and effective-cost curves, loaded when a card opens
- land.geojson, eez.geojson  simplified geometries (rebuilt only when missing or with --geometry)

Run from the repository root:  python web/scripts/build_web_data.py [--geometry]
"""

import argparse
import json
import math
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "data"
BOUNDARIES = ROOT / "data" / "raw" / "geospatial" / "boundaries"
TABLES = ROOT / "results" / "tables"
MASTER = ROOT / "data" / "derived" / "validation" / "country_level_results_master.csv"

# Soil scenarios offered by the restoration switch on the site; the first is the default.
SOIL_SCENARIOS = ["busch_reference", "zero_soil_change"]

# Same Natural Earth to study-unit aliases as notebook 08.
NE_TO_UNIT = {"SDS": "SSD", "SAH": "ESH", "PSX": "PSE", "HKG": "CHN", "MAC": "CHN", "TWN": "CHN",
              "CYN": "CYP", "SOL": "SOM", "ALD": "FIN", "ATC": "AUS", "IOA": "AUS"}

TEXT_FIELDS = [
    "UNIT_CODE", "name", "continent", "region", "groups", "sovereign", "unit_class",
    "overlap_status", "emissions_2024_match_status", "mangrove_area_source",
]
BOOL_FIELDS = ["has_gcw", "has_bcw", "desk_study", "reported_deforestation"]
NUMERIC_FIELDS = [
    # Wealth accounts (US$2015 per year)
    "ncw_usd2015_yr_mean", "ncw_usd2015_yr_p05", "ncw_usd2015_yr_p95",
    "gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95",
    "bcw_usd2015_yr_mean", "bcw_usd2015_yr_p05", "bcw_usd2015_yr_p95",
    "forest_share_of_ncw", "gcw_share_global_pct",
    # Forest account
    "uptake_tco2_yr_mean", "uptake_tco2_yr_p05", "uptake_tco2_yr_p95",
    "fra_total_forest_area_2025_ha", "fra_primary_forest_2025_ha", "fra_planted_forest_2025_ha",
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

RESTORATION_FIELDS = [
    "restoration_status", "restoration_target_discounted_30yr_tco2", "available_discounted_30yr_tco2",
    "target_coverage_pct", "restoration_marginal_cost_usd2015_tco2", "restoration_cost_net_pv_usd2015",
    "restoration_cost_net_annual_usd2015", "restoration_cost_positive_annual_usd2015",
    "restoration_cost_uniform_annual_usd2015", "nr_soil_rate_tC_ha_yr", "plantation_soil_rate_tC_ha_yr",
]


def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def rounded(value):
    value = clean(value)
    return float(f"{value:.6g}") if isinstance(value, float) else value


def build_units():
    master = pd.read_csv(MASTER, low_memory=False)
    accounts = pd.read_csv(TABLES / "manuscript" / "Supplementary_country_level_accounts_2024.csv", low_memory=False)
    master = master.merge(accounts[["UNIT_CODE", "gcw_gdp_2024_pct"]], on="UNIT_CODE", how="left")
    missing = [c for c in TEXT_FIELDS + BOOL_FIELDS + NUMERIC_FIELDS if c not in master.columns and c != "bcw_gdp_2024_pct"]
    if missing:
        raise ValueError(f"The master table lacks fields used by the web explorer: {missing}")
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
    table1 = pd.read_csv(TABLES / "manuscript" / "Table1_global_carbon_wealth.csv")
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
    tables = TABLES / "manuscript"
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


def build_bcw_sources(units):
    """BCW source records of Hilmi et al. with the accounting unit each one is counted in."""
    bcw = pd.read_csv(TABLES / "01_bcw_hilmi_updated.csv")
    if bcw["iso"].duplicated().any():
        raise ValueError("BCW source codes must be unique")
    unknown = set(bcw["account_unit_code"]) - units
    if unknown:
        raise ValueError(f"BCW source records point to unknown units: {sorted(unknown)}")
    return [{"code": row.iso, "unit": row.account_unit_code, "role": row.mapping_role,
             "name": clean(row.country_name), "territory": clean(row.territory1)}
            for row in bcw.itertuples(index=False)]


def build_restoration(units):
    """Restoration results by unit and soil scenario, plus one curve file per country."""
    costs = pd.read_csv(TABLES / "05_restoration_costs_by_entity.csv")
    costs = costs.loc[costs["soil_scenario"].isin(SOIL_SCENARIOS)]
    if costs.duplicated(["unit_code", "soil_scenario"]).any() or not set(costs["unit_code"]) <= units:
        raise ValueError("Restoration costs must hold one row per known unit and soil scenario")
    results = {}
    for row in costs.itertuples(index=False):
        # Units without a restoration target have no values; missing fields are left out.
        record = {f: rounded(getattr(row, f)) for f in RESTORATION_FIELDS}
        record = {f: v for f, v in record.items() if v is not None}
        if record:
            results.setdefault(row.unit_code, {})[row.soil_scenario] = record

    curves = pd.read_csv(TABLES / "06_restoration_supply_curves.csv")
    curves = curves.loc[curves["soil_scenario"].isin(SOIL_SCENARIOS)]
    folder = OUT / "curves"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    price = {"price_supply": "price_usd2015_per_tco2", "effective_cost": "marginal_effective_cost_usd2015_per_tco2"}
    with_curves = []
    for iso3, rows in curves.groupby("iso3"):
        if iso3 not in units:
            raise ValueError(f"Restoration curve for unknown unit {iso3}")
        data = {}
        for (scenario, kind), part in rows.groupby(["soil_scenario", "curve_type"]):
            part = part.sort_values("quantity_cumulative_discounted_30yr_tco2")
            # Points are [cumulative discounted 30-year tCO2, US$2015 per tCO2].
            data.setdefault(scenario, {})[kind] = [[float(f"{q:.5g}"), float(f"{p:.5g}")] for q, p in
                                                   zip(part["quantity_cumulative_discounted_30yr_tco2"], part[price[kind]])]
        (folder / f"{iso3}.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        with_curves.append(iso3)
    return {"scenarios": SOIL_SCENARIOS, "units": results, "curves": sorted(with_curves)}


def write_geojson(frame, path, tolerance, precision=3, props=("code",)):
    frame = frame.copy()
    frame["geometry"] = frame.geometry.make_valid().simplify(tolerance, preserve_topology=True)
    frame = frame.loc[~frame.geometry.is_empty]
    features = []
    for row in frame.itertuples(index=False):
        geo = json.loads(json.dumps(mapping(row.geometry)), parse_float=lambda x: round(float(x), precision))
        features.append({"type": "Feature", "properties": {p: getattr(row, p) for p in props}, "geometry": geo})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
                    encoding="utf-8")
    return path.stat().st_size / 1e6


def eez_source_code(row, codes, by_name, by_territory):
    """BCW source record of one EEZ polygon, following how Hilmi et al. built their records.

    Multi-party overlapping claims and joint regimes are pooled records; a named disputed
    territory (Falklands, Western Sahara, Kuril Islands...) is its own record; parts without
    an ISO code (Trindade, Galapagos, Hawaii...) are matched by name.
    """
    if row.POL_TYPE == "Joint regime (EEZ)":
        return "BCW-JR"
    if str(row.UNION).startswith("Overlapping claim"):
        return "BCW-OC"
    if row.ISO_TER1 in codes:
        return row.ISO_TER1
    return by_name.get(row.UNION) or by_territory.get(row.TERRITORY1)


def build_geometries(units, sources):
    land = gpd.read_file("/vsizip/" + (BOUNDARIES / "ne_10m_admin_0_map_units.zip").as_posix()
                         + "/ne_10m_admin_0_map_units.shp")
    land["code"] = [gu if gu in units else iso if iso in units else NE_TO_UNIT.get(adm, adm)
                    for gu, iso, adm in zip(land["GU_A3"], land["ISO_A3"], land["ADM0_A3"])]
    land = land.loc[land["code"] != "ATA"].dissolve("code", as_index=False)[["code", "geometry"]].to_crs("EPSG:4326")

    eez = gpd.read_file(BOUNDARIES / "EEZ_land_union_v4_202410.shp")
    eez = eez.set_crs("EPSG:4326") if eez.crs is None else eez.to_crs("EPSG:4326")
    codes = {s["code"] for s in sources}
    by_name = {s["name"]: s["code"] for s in sources if s["name"]}
    territories = pd.Series([s["territory"] for s in sources if s["territory"]]).value_counts()
    by_territory = {s["territory"]: s["code"] for s in sources if s["territory"] and territories[s["territory"]] == 1}
    eez["code"] = [eez_source_code(r, codes, by_name, by_territory) for r in eez.itertuples(index=False)]
    eez = eez.loc[eez["code"].notna()].dissolve("code", as_index=False)[["code", "geometry"]]
    eez["unit"] = eez["code"].map({s["code"]: s["unit"] for s in sources})
    return (write_geojson(land, OUT / "land.geojson", 0.02),
            write_geojson(eez, OUT / "eez.geojson", 0.05, precision=2, props=("code", "unit")))


def geometry_codes(path):
    return {f["properties"]["code"] for f in json.loads(path.read_text(encoding="utf-8"))["features"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--geometry", action="store_true", help="rebuild land.geojson and eez.geojson from the raw boundaries")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    master, records = build_units()
    units = {r["UNIT_CODE"] for r in records}
    sources = build_bcw_sources(units)
    restoration = build_restoration(units)
    (OUT / "units.json").write_text(json.dumps(records, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (OUT / "global.json").write_text(json.dumps(build_global(master), indent=1), encoding="utf-8")
    (OUT / "aggregates.json").write_text(json.dumps(build_aggregates(master), indent=1), encoding="utf-8")
    (OUT / "bcw_sources.json").write_text(json.dumps(sources, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (OUT / "restoration.json").write_text(json.dumps(restoration, separators=(",", ":")), encoding="utf-8")

    land_path, eez_path = OUT / "land.geojson", OUT / "eez.geojson"
    # Geometries change only with the raw boundaries; an EEZ file still keyed by unit is rebuilt.
    stale_eez = eez_path.is_file() and "unit" not in json.loads(eez_path.read_text(encoding="utf-8"))["features"][0]["properties"]
    if args.geometry or not land_path.is_file() or not eez_path.is_file() or stale_eez:
        land_mb, eez_mb = build_geometries(units, sources)
        print(f"land.geojson {land_mb:.1f} MB | eez.geojson {eez_mb:.1f} MB")
    print(f"units.json: {len(records)} units | bcw_sources.json: {len(sources)} records | "
          f"restoration curves: {len(restoration['curves'])} countries")
    gcw_units = {r["UNIT_CODE"] for r in records if r["has_gcw"]}
    print(f"GCW units without land polygon: {sorted(gcw_units - geometry_codes(land_path))}")
    print(f"BCW source records without EEZ polygon: {sorted({s['code'] for s in sources} - geometry_codes(eez_path))}")


if __name__ == "__main__":
    main()
