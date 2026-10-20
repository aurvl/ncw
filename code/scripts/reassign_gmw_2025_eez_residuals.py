"""Allocate GMW polygons outside their source country to the EEZ they cross.

Only non-overlapping `Union EEZ and country` units are eligible. Remaining
area is reported rather than assigned to overlapping claims or joint regimes.
"""

from __future__ import annotations

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
OUT = ROOT / "results/validation"
GEOMETRY_ALIASES = {"ATF_EI": "ATF", "BES_B": "BES", "MUS_CA": "MUS"}
PROJECT_ALIASES = {"ATF_EI": "ATF-4", "BES_B": "BES", "MUS_CA": "MUS", "TWN": "CHN"}


def main() -> None:
    audit = pd.read_csv(OUT / "gmw_2025_eez_overlay_by_source_unit.csv")
    to_review = audit.loc[audit["outside_matching_eez_ha"] > 1e-5]
    boundaries = pyogrio.read_dataframe(
        EEZ, columns=["ISO_TER1", "ISO_SOV1", "POL_TYPE"]
    )
    boundaries["unit"] = boundaries["ISO_TER1"]
    subordinate = boundaries["unit"].isna() & boundaries["POL_TYPE"].eq("Union EEZ and country")
    boundaries.loc[subordinate, "unit"] = boundaries.loc[subordinate, "ISO_SOV1"]
    by_unit = {
        str(code): shapely.union_all(frame.geometry.values)
        for code, frame in boundaries.loc[boundaries.unit.notna()].groupby("unit")
    }
    union_boundaries = boundaries.loc[
        boundaries["POL_TYPE"].eq("Union EEZ and country")
        & boundaries["unit"].notna()
    ].reset_index(drop=True)
    tree = shapely.STRtree(union_boundaries.geometry.values)
    projector = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)

    def project(coordinates: np.ndarray) -> np.ndarray:
        x, y = projector.transform(coordinates[:, 0], coordinates[:, 1])
        return np.column_stack((x, y))

    assigned: dict[tuple[str, str], float] = defaultdict(float)
    unassigned: dict[str, float] = defaultdict(float)
    for source in to_review["gmw_iso3"].astype(str):
        frame = pyogrio.read_dataframe(GMW, where=f"cntry_iso3 = '{source}'", columns=["cntry_iso3"])
        own_boundary = by_unit.get(GEOMETRY_ALIASES.get(source, source))
        if own_boundary is None:
            residual = frame.geometry.values
        else:
            shapely.prepare(own_boundary)
            outside = ~shapely.contains(own_boundary, frame.geometry.values)
            residual = shapely.difference(frame.geometry.values[outside], own_boundary)
        residual = residual[~shapely.is_empty(residual)]
        for geometry in residual:
            remaining = geometry
            candidates = tree.query(geometry, predicate="intersects")
            for index in candidates:
                boundary = union_boundaries.geometry.iloc[index]
                piece = shapely.intersection(remaining, boundary)
                if shapely.is_empty(piece):
                    continue
                area = shapely.area(shapely.transform(piece, project)) / 10_000.0
                if area <= 0:
                    continue
                destination = str(union_boundaries.iloc[index]["unit"])
                assigned[(source, destination)] += area
                remaining = shapely.difference(remaining, piece)
                if shapely.is_empty(remaining):
                    break
            if not shapely.is_empty(remaining):
                unassigned[source] += (
                    shapely.area(shapely.transform(remaining, project)) / 10_000.0
                )
        print(source, "assigned", sum(v for (s, _), v in assigned.items() if s == source),
              "unassigned", unassigned[source], flush=True)

    moves = pd.DataFrame(
        [
            {"gmw_source_iso3": source, "eez_destination_iso3": destination, "area_ha": area}
            for (source, destination), area in sorted(assigned.items())
        ]
    )
    moves.to_csv(OUT / "gmw_2025_eez_residual_reassignment.csv", index=False)

    final = audit.copy()
    final["iso3"] = final["gmw_iso3"].replace(PROJECT_ALIASES)
    final = final.groupby("iso3", as_index=False)["within_matching_eez_ha"].sum()
    additions = moves.groupby("eez_destination_iso3")["area_ha"].sum()
    final["received_from_other_gmw_unit_ha"] = final["iso3"].map(additions).fillna(0.0)
    final["final_eez_ha"] = (
        final["within_matching_eez_ha"] + final["received_from_other_gmw_unit_ha"]
    )
    missing_dest = additions.index.difference(final["iso3"])
    if len(missing_dest):
        final = pd.concat(
            [
                final,
                pd.DataFrame(
                    {
                        "iso3": missing_dest,
                        "within_matching_eez_ha": 0.0,
                        "received_from_other_gmw_unit_ha": additions.loc[missing_dest].values,
                        "final_eez_ha": additions.loc[missing_dest].values,
                    }
                ),
            ],
            ignore_index=True,
        )
    final.sort_values("iso3").to_csv(OUT / "gmw_2025_eez_final_area_by_unit.csv", index=False)
    raw_total = audit["raw_ha"].sum()
    assert np.isclose(final["final_eez_ha"].sum() + sum(unassigned.values()), raw_total, atol=0.01)
    print("Raw total ha", raw_total)
    print("Final EEZ-attributed ha", final["final_eez_ha"].sum())
    print("Unassigned ha", sum(unassigned.values()))
    print(moves.sort_values("area_ha", ascending=False).head(15).to_string(index=False))


if __name__ == "__main__":
    main()
