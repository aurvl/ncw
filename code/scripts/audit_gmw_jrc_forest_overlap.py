"""Test a spatial GMW-2025 × JRC-forest overlap proxy for FRA mangroves.

This is deliberately a sensitivity analysis, not a replacement for FRA's
national Forest/OWL classifications. GMW polygons are assigned to the value
of the coarse JRC Global Forest Cover 2020 overview at each polygon's
representative point, then their equal-area polygon hectares are summed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import rasterio


ROOT = Path(__file__).resolve().parents[2]
GMW = ROOT / "data/raw/environmental/marine/gmw/gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg"
JRC = ROOT / "data/raw/environmental/forest/forest_mask/JRC_GFC2020_V4_overview_x256.tif"
OVERLAP = ROOT / "data/derived/fra_mangrove_forest_overlap_2025.csv"
GMW_AREA = ROOT / "data/derived/gmw_2025_mangrove_area_by_unit.csv"
OUTPUT = ROOT / "results/validation/gmw_jrc_forest_overlap_proxy.csv"


def main() -> None:
    evidence = pd.read_csv(OVERLAP, usecols=["iso3", "fra_mangroves_2025_ha", "overlap_status"])
    corrected = pd.read_csv(GMW_AREA).rename(columns={"gmw_2025_mangrove_area_ha": "gmw_corrected_area_ha"})
    units = evidence.merge(corrected, on="iso3", how="left")
    rows: list[dict[str, object]] = []

    with rasterio.open(JRC) as forest:
        for number, iso in enumerate(units["iso3"], 1):
            mangroves = pyogrio.read_dataframe(GMW, where=f"cntry_iso3 = '{iso}'", columns=["cntry_iso3", "geometry"])
            if mangroves.empty:
                rows.append({"iso3": iso, "gmw_vector_area_ha": 0.0, "gmw_jrc_forest_proxy_area_ha": 0.0,
                             "gmw_jrc_forest_proxy_fraction": np.nan, "n_gmw_polygons": 0})
                continue
            areas = mangroves.to_crs("ESRI:54009").geometry.area.to_numpy() / 10_000.0
            points = mangroves.geometry.representative_point()
            values = np.fromiter((value[0] for value in forest.sample(zip(points.x, points.y))), dtype=np.uint8, count=len(points))
            forest_area = float(areas[values == 1].sum())
            vector_area = float(areas.sum())
            rows.append({
                "iso3": iso,
                "gmw_vector_area_ha": vector_area,
                "gmw_jrc_forest_proxy_area_ha": forest_area,
                "gmw_jrc_forest_proxy_fraction": forest_area / vector_area if vector_area else np.nan,
                "n_gmw_polygons": len(mangroves),
            })
            if number % 10 == 0 or number == len(units):
                print(f"Processed GMW/JRC overlap proxy: {number}/{len(units)}", flush=True)

    result = units.merge(pd.DataFrame(rows), on="iso3", how="left")
    result["gmw_jrc_forest_proxy_corrected_area_ha"] = (
        result["gmw_corrected_area_ha"] * result["gmw_jrc_forest_proxy_fraction"]
    )
    result["proxy_area_as_fra_mangrove_pct"] = (
        100 * result["gmw_jrc_forest_proxy_corrected_area_ha"] / result["fra_mangroves_2025_ha"]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False, lineterminator="\n")
    print(f"Wrote {len(result)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
