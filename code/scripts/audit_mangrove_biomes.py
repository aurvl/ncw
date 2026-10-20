"""Locate GMW 2025 mangrove polygons by FAO ecological domain.

The analysis diagnoses biome allocation; it does not identify which polygons
qualify as FRA forest, since FRA national area tables are not pixel maps.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gmw-gpkg", type=Path, required=True)
    parser.add_argument("--gez-shp", type=Path, required=True)
    parser.add_argument("--iso", nargs="+", default=["PAK", "TCA", "SHN"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    gez = gpd.read_file(args.gez_shp)[["gez_code", "gez_name", "geometry"]]
    gez["biome"] = gez["gez_code"].floordiv(10).map({1: "tropical", 2: "subtropical", 3: "temperate", 4: "boreal"})
    gez = gez.loc[gez["biome"].notna()]
    records = []
    for iso in args.iso:
        mangroves = pyogrio.read_dataframe(args.gmw_gpkg, where=f"cntry_iso3 = '{iso}'")
        if mangroves.empty:
            records.append({"iso3": iso, "biome": "no_gmw_polygons", "gmw_vector_area_ha": 0.0})
            continue
        mangroves["gmw_vector_area_ha"] = mangroves.to_crs("ESRI:54009").geometry.area / 10_000.0
        # Country mangrove polygons are tiny (30 m mapped extent). A representative
        # point assigns each polygon to one GEZ domain without a costly overlay.
        points = mangroves[["gmw_vector_area_ha", "geometry"]].copy()
        points.geometry = points.geometry.representative_point()
        assigned = gpd.sjoin(points, gez[["biome", "geometry"]], how="left", predicate="within")
        assigned["biome"] = assigned["biome"].fillna("outside_gez")
        for biome, area in assigned.groupby("biome", dropna=False)["gmw_vector_area_ha"].sum().items():
            records.append({"iso3": iso, "biome": biome, "gmw_vector_area_ha": area})
    result = pd.DataFrame(records).sort_values(["iso3", "biome"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
