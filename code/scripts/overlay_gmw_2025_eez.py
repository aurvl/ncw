"""Intersect the GMW 2025 mangrove polygons with the BCW EEZ/land boundaries.

Processes the 1.55 million public GMW polygons in bounded chunks. The output
keeps unmatched area visible and does not substitute corrected country totals
for polygon area. It is a spatial sensitivity input, not a FRA forest overlap.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[2]
GMW = ROOT / "data/raw/environmental/marine/gmw/gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg"
EEZ = ROOT / "data/raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp"
OUT = ROOT / "data/derived/validation/gmw_2025_eez_overlay_by_source_unit.csv"
GEOMETRY_CODE_ALIASES = {"ATF_EI": "ATF", "BES_B": "BES", "MUS_CA": "MUS"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=20_000)
    parser.add_argument("--limit", type=int, default=None, help="For a smoke test only")
    args = parser.parse_args()

    boundaries = pyogrio.read_dataframe(
        EEZ, columns=["ISO_TER1", "ISO_SOV1", "POL_TYPE"]
    )
    boundaries["accounting_iso3"] = boundaries["ISO_TER1"]
    subordinate = (
        boundaries["accounting_iso3"].isna()
        & boundaries["POL_TYPE"].eq("Union EEZ and country")
    )
    boundaries.loc[subordinate, "accounting_iso3"] = boundaries.loc[subordinate, "ISO_SOV1"]
    by_iso = {
        str(code): shapely.union_all(frame.geometry.values)
        for code, frame in boundaries.loc[boundaries.accounting_iso3.notna()].groupby("accounting_iso3")
    }
    for geometry in by_iso.values():
        shapely.prepare(geometry)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)

    def project(coordinates: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(coordinates[:, 0], coordinates[:, 1])
        return np.column_stack((x, y))

    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"raw_ha": 0.0, "within_matching_eez_ha": 0.0, "polygon_count": 0}
    )
    feature_count = pyogrio.read_info(GMW)["features"]
    upper = min(feature_count, args.limit) if args.limit is not None else feature_count
    for offset in range(0, upper, args.chunk_size):
        frame = pyogrio.read_dataframe(
            GMW,
            columns=["cntry_iso3"],
            skip_features=offset,
            max_features=min(args.chunk_size, upper - offset),
        )
        for code, subset in frame.groupby("cntry_iso3", dropna=False):
            code = str(code)
            geometries = subset.geometry.values
            raw = shapely.area(shapely.transform(geometries, project))
            raw_ha = float(np.sum(raw) / 10_000.0)
            within_ha = 0.0
            boundary = by_iso.get(GEOMETRY_CODE_ALIASES.get(code, code))
            if boundary is not None:
                fully_inside = shapely.contains(boundary, geometries)
                within_ha = float(np.sum(raw[fully_inside]) / 10_000.0)
                if not np.all(fully_inside):
                    clipped = shapely.intersection(boundary, geometries[~fully_inside])
                    within_ha += float(
                        np.sum(shapely.area(shapely.transform(clipped, project)))
                        / 10_000.0
                    )
            totals[code]["raw_ha"] += raw_ha
            totals[code]["within_matching_eez_ha"] += within_ha
            totals[code]["polygon_count"] += len(subset)
        if offset == 0 or (offset // args.chunk_size) % 10 == 9 or offset + len(frame) >= upper:
            print(f"GMW polygons processed: {offset + len(frame):,}/{upper:,}", flush=True)

    rows = []
    for code, values in sorted(totals.items()):
        row = {"gmw_iso3": code, **values}
        row["outside_matching_eez_ha"] = max(
            0.0, row["raw_ha"] - row["within_matching_eez_ha"]
        )
        row["has_matching_eez_code"] = GEOMETRY_CODE_ALIASES.get(code, code) in by_iso
        rows.append(row)
    result = pd.DataFrame(rows)
    assert result["polygon_count"].sum() == upper
    assert (
        result["within_matching_eez_ha"] <= result["raw_ha"] + 1e-5
    ).all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    target = OUT if args.limit is None else OUT.with_name("gmw_2025_eez_overlay_smoke.csv")
    result.to_csv(target, index=False)
    print(result[["raw_ha", "within_matching_eez_ha", "outside_matching_eez_ha"]].sum())
    print(result.sort_values("outside_matching_eez_ha", ascending=False).head(15).to_string(index=False))
    print(target)


if __name__ == "__main__":
    main()
