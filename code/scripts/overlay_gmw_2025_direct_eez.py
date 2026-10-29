"""Directly intersect GMW 2025 mangrove polygons with every EEZ UNION unit.

The GMW country code is retained as an attribute so each EEZ result can be
audited against the source label. Areas are measured in Mollweide (ESRI:54009),
following the spatial harmonization described by Hilmi et al. (2026). The
intersection output is dissolved by EEZ UNION and GMW source code before area
measurement; unit totals are dissolved by UNION across all GMW source codes.
This stage records raw geometric areas. The account-area builder then applies
GMW's published global 0.9775 correction uniformly; source codes never trigger
spatial transfers between EEZ units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[2]
GMW = ROOT / "data/raw/environmental/marine/gmw/gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg"
EEZ = ROOT / "data/raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp"
VALIDATION = ROOT / "results/validation"
PAIR_OUT = VALIDATION / "gmw_2025_direct_overlay_by_eez_unit_and_source.csv"
UNIT_OUT = VALIDATION / "gmw_2025_direct_overlay_area_by_eez_unit.csv"
SUMMARY_OUT = VALIDATION / "gmw_2025_direct_overlay_summary.json"

GMW_CODE_ALIASES = {"ATF_EI": "ATF", "BES_B": "BES", "MUS_CA": "MUS"}
EEZ_COLUMNS = [
    "UNION", "ISO_TER1", "ISO_SOV1", "POL_TYPE", "TERRITORY1", "SOVEREIGN1"
]


def _project_xy(coordinates: np.ndarray, transformer: Transformer) -> np.ndarray:
    x, y = transformer.transform(coordinates[:, 0], coordinates[:, 1])
    return np.column_stack((x, y))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_eez_units() -> pd.DataFrame:
    boundaries = pyogrio.read_dataframe(EEZ, columns=EEZ_COLUMNS)
    if boundaries["UNION"].isna().any():
        raise ValueError("EEZ boundary has an empty UNION identifier")

    rows = []
    for union_name, frame in boundaries.groupby("UNION", sort=True, dropna=False):
        geometries = np.asarray(frame.geometry.values, dtype=object)
        invalid = ~shapely.is_valid(geometries)
        if invalid.any():
            geometries[invalid] = shapely.make_valid(geometries[invalid])
        geometry = shapely.union_all(geometries)
        first = frame.iloc[0]
        rows.append(
            {
                "eez_union": str(union_name),
                "eez_iso3": _clean_code(first["ISO_TER1"]),
                "eez_sovereign_iso3": _clean_code(first["ISO_SOV1"]),
                "eez_polygon_type": _clean_text(first["POL_TYPE"]),
                "eez_territory_name": _clean_text(first["TERRITORY1"]),
                "eez_sovereign_name": _clean_text(first["SOVEREIGN1"]),
                "geometry": geometry,
            }
        )

    units = pd.DataFrame(rows)
    if units["eez_union"].duplicated().any():
        raise ValueError("EEZ UNION dissolve did not produce unique units")
    return units


def _clean_code(value) -> str | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip()


def _clean_text(value) -> str | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, default=20_000)
    parser.add_argument("--intersection-batch-size", type=int, default=1_000)
    parser.add_argument(
        "--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 2))
    )
    parser.add_argument("--limit", type=int, default=None, help="Process an initial feature subset only")
    args = parser.parse_args()
    if (
        args.chunk_size < 1
        or args.intersection_batch_size < 1
        or args.workers < 1
        or (args.limit is not None and args.limit < 1)
    ):
        parser.error("--chunk-size, --intersection-batch-size, --workers and --limit must be positive")
    if not GMW.is_file() or not EEZ.is_file():
        missing = [str(path) for path in (GMW, EEZ) if not path.is_file()]
        raise FileNotFoundError("Required spatial inputs are missing: " + ", ".join(missing))

    units = _read_eez_units()
    unit_geometries = np.asarray(units["geometry"].values, dtype=object)
    transformer = Transformer.from_crs("EPSG:4326", "ESRI:54009", always_xy=True)
    unit_geometries = shapely.transform(
        unit_geometries, lambda xy: _project_xy(xy, transformer)
    )
    invalid_projected_eez = ~shapely.is_valid(unit_geometries)
    projected_eez_repaired = int(invalid_projected_eez.sum())
    if invalid_projected_eez.any():
        unit_geometries[invalid_projected_eez] = shapely.make_valid(
            unit_geometries[invalid_projected_eez]
        )
    tree = shapely.STRtree(unit_geometries)

    source_info = pyogrio.read_info(GMW)
    feature_count = int(source_info["features"])
    upper = min(feature_count, args.limit) if args.limit is not None else feature_count
    source_code_names: dict[str, str] = {}
    pair_areas: dict[tuple[int, str], float] = defaultdict(float)
    pair_polygon_counts: dict[tuple[int, str], int] = defaultdict(int)
    unit_areas: dict[int, float] = defaultdict(float)
    unit_cross_source_overlap: dict[int, float] = defaultdict(float)
    features_without_positive_area_intersection = 0
    invalid_gmw_repaired = 0
    projected_gmw_repaired = 0
    processed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as intersection_pool, pyogrio.open_arrow(
        GMW,
        columns=["cntry_iso3", "cntry_name"],
        batch_size=args.chunk_size,
        use_pyarrow=True,
    ) as (arrow_metadata, reader):
        geometry_index = reader.schema.get_field_index(arrow_metadata["geometry_name"])
        code_index = reader.schema.get_field_index("cntry_iso3")
        name_index = reader.schema.get_field_index("cntry_name")
        for arrow_batch in reader:
            if processed >= upper:
                break
            batch_size = min(arrow_batch.num_rows, upper - processed)
            if batch_size < arrow_batch.num_rows:
                arrow_batch = arrow_batch.slice(0, batch_size)
            geometries = shapely.from_wkb(
                arrow_batch.column(geometry_index).to_pylist()
            )
            codes = np.asarray(
                [value.strip() if value else "" for value in arrow_batch.column(code_index).to_pylist()],
                dtype=object,
            )
            names = np.asarray(
                [value.strip() if value else "" for value in arrow_batch.column(name_index).to_pylist()],
                dtype=object,
            )
            for code, name in zip(codes, names):
                if code:
                    source_code_names.setdefault(code, name)
            invalid = ~shapely.is_valid(geometries)
            if invalid.any():
                invalid_gmw_repaired += int(invalid.sum())
                geometries[invalid] = shapely.make_valid(geometries[invalid])
            geometries = shapely.transform(
                geometries, lambda xy: _project_xy(xy, transformer)
            )
            invalid_projected = ~shapely.is_valid(geometries)
            if invalid_projected.any():
                projected_gmw_repaired += int(invalid_projected.sum())
                geometries[invalid_projected] = shapely.make_valid(
                    geometries[invalid_projected]
                )

            input_indices, unit_indices = tree.query(geometries, predicate="intersects")
            if len(input_indices) == 0:
                features_without_positive_area_intersection += arrow_batch.num_rows
                processed += arrow_batch.num_rows
                print(f"GMW polygons processed: {processed:,}/{upper:,}", flush=True)
                continue

            positive_feature_mask = np.zeros(arrow_batch.num_rows, dtype=bool)
            intersection_batches = [
                (
                    input_indices[batch_start:batch_start + args.intersection_batch_size],
                    unit_indices[batch_start:batch_start + args.intersection_batch_size],
                )
                for batch_start in range(0, len(input_indices), args.intersection_batch_size)
            ]
            intersection_pieces = intersection_pool.map(
                lambda pair: shapely.intersection(
                    geometries[pair[0]], unit_geometries[pair[1]]
                ),
                intersection_batches,
            )
            for (batch_input, batch_units), pieces in zip(
                intersection_batches, intersection_pieces
            ):
                positive = (~shapely.is_empty(pieces)) & (shapely.area(pieces) > 0)
                if not positive.any():
                    continue
                batch_input = batch_input[positive]
                batch_units = batch_units[positive]
                pieces = pieces[positive]
                positive_feature_mask[batch_input] = True
                batch_codes = codes[batch_input]
                unique_codes, code_ids = np.unique(batch_codes, return_inverse=True)
                code_stride = 100_000
                if len(unique_codes) >= code_stride:
                    raise ValueError("Unexpectedly many GMW source codes in one intersection batch")
                pair_ids = batch_units.astype(np.int64) * code_stride + code_ids
                unique_pair_ids, inverse = np.unique(pair_ids, return_inverse=True)
                order = np.argsort(inverse, kind="stable")
                breaks = np.flatnonzero(np.diff(inverse[order])) + 1
                groups = np.split(order, breaks)
                batch_pair_areas: dict[tuple[int, str], float] = {}

                for pair_id, positions in zip(unique_pair_ids, groups):
                    unit_index = int(pair_id // code_stride)
                    code = str(unique_codes[int(pair_id % code_stride)])
                    key = (unit_index, code)
                    area = float(shapely.area(shapely.union_all(pieces[positions])) / 10_000.0)
                    pair_areas[key] += area
                    pair_polygon_counts[key] += int(len(positions))
                    batch_pair_areas[key] = area

                for unit_index in np.unique(batch_units):
                    unit_index = int(unit_index)
                    selected = batch_units == unit_index
                    unit_area = float(shapely.area(shapely.union_all(pieces[selected])) / 10_000.0)
                    source_area_sum = sum(
                        area for (pair_unit, _), area in batch_pair_areas.items()
                        if pair_unit == unit_index
                    )
                    unit_areas[unit_index] += unit_area
                    unit_cross_source_overlap[unit_index] += max(
                        0.0, source_area_sum - unit_area
                    )

            features_without_positive_area_intersection += int(
                arrow_batch.num_rows - positive_feature_mask.sum()
            )
            processed += arrow_batch.num_rows
            print(f"GMW polygons processed: {processed:,}/{upper:,}", flush=True)

    pair_rows = []
    for (unit_index, source_code), area in sorted(
        pair_areas.items(), key=lambda item: (units.iloc[item[0][0]]["eez_union"], item[0][1])
    ):
        unit = units.iloc[unit_index]
        normalized_gmw_code = GMW_CODE_ALIASES.get(source_code, source_code)
        comparison_code = unit["eez_iso3"] or unit["eez_sovereign_iso3"]
        pair_rows.append(
            {
                "eez_union": unit["eez_union"],
                "eez_iso3": unit["eez_iso3"],
                "eez_sovereign_iso3": unit["eez_sovereign_iso3"],
                "eez_polygon_type": unit["eez_polygon_type"],
                "eez_territory_name": unit["eez_territory_name"],
                "eez_sovereign_name": unit["eez_sovereign_name"],
                "gmw_cntry_iso3": source_code,
                "gmw_cntry_name": source_code_names.get(source_code),
                "gmw_code_matches_eez_iso3": bool(
                    comparison_code and normalized_gmw_code == comparison_code
                ),
                "intersected_area_ha": area,
                "intersecting_gmw_polygon_count": pair_polygon_counts[(unit_index, source_code)],
            }
        )

    pair_table = pd.DataFrame(pair_rows)
    unit_rows = []
    for unit_index, unit in units.iterrows():
        pair_keys = [key for key in pair_areas if key[0] == unit_index]
        if pair_keys:
            direct_area = unit_areas[unit_index]
            pair_area_sum = sum(pair_areas[key] for key in pair_keys)
            overlap_excess = unit_cross_source_overlap[unit_index]
            code_count = len(pair_keys)
            polygon_count = sum(pair_polygon_counts[key] for key in pair_keys)
        else:
            direct_area = 0.0
            pair_area_sum = 0.0
            overlap_excess = 0.0
            code_count = 0
            polygon_count = 0
        unit_rows.append(
            {
                **{key: unit[key] for key in EEZ_COLUMNS if key in unit.index},
                "eez_union": unit["eez_union"],
                "eez_iso3": unit["eez_iso3"],
                "eez_sovereign_iso3": unit["eez_sovereign_iso3"],
                "eez_polygon_type": unit["eez_polygon_type"],
                "eez_territory_name": unit["eez_territory_name"],
                "eez_sovereign_name": unit["eez_sovereign_name"],
                "gmw_direct_overlay_area_ha": direct_area,
                "sum_of_source_code_areas_ha": pair_area_sum,
                "cross_source_overlap_excess_ha": overlap_excess,
                "intersecting_gmw_source_code_count": code_count,
                "intersecting_gmw_polygon_count": polygon_count,
            }
        )
    unit_table = pd.DataFrame(unit_rows).sort_values("eez_union").reset_index(drop=True)

    validation_dir = VALIDATION
    validation_dir.mkdir(parents=True, exist_ok=True)
    if args.limit is not None:
        pair_path = PAIR_OUT.with_name("gmw_2025_direct_overlay_by_eez_unit_and_source_smoke.csv")
        unit_path = UNIT_OUT.with_name("gmw_2025_direct_overlay_area_by_eez_unit_smoke.csv")
    else:
        pair_path = PAIR_OUT
        unit_path = UNIT_OUT
    pair_table.to_csv(pair_path, index=False)
    unit_table.to_csv(unit_path, index=False)

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Project and validate GMW and EEZ geometries in Mollweide, then directly intersect by EEZ UNION and GMW source code; intersections are dissolved within bounded batches before measuring raw geometric area.",
        "area_basis": "Raw mapped polygon area before GMW's global accuracy correction; the downstream account-area builder multiplies area by 0.9775.",
        "area_correction_applied_in_overlay": False,
        "gmw_source": str(GMW.relative_to(ROOT)).replace("\\", "/"),
        "eez_source": str(EEZ.relative_to(ROOT)).replace("\\", "/"),
        "input_crs": "EPSG:4326",
        "area_crs": "ESRI:54009 (Mollweide)",
        "gmw_features_total": feature_count,
        "gmw_features_processed": upper,
        "eez_union_units": int(len(units)),
        "gmw_source_codes_observed": int(len(source_code_names)),
        "intersection_pairs": int(len(pair_table)),
        "units_with_intersections": int((unit_table["gmw_direct_overlay_area_ha"] > 0).sum()),
        "gmw_invalid_geometries_repaired": invalid_gmw_repaired,
        "gmw_invalid_geometries_repaired_after_projection": projected_gmw_repaired,
        "eez_invalid_geometries_repaired_after_projection": projected_eez_repaired,
        "gmw_features_without_positive_area_intersection": features_without_positive_area_intersection,
        "total_direct_overlay_area_ha_summed_across_union_units": float(unit_table["gmw_direct_overlay_area_ha"].sum()),
        "sum_of_pair_dissolved_areas_ha": float(pair_table["intersected_area_ha"].sum()),
        "cross_source_overlap_excess_ha": float(unit_table["cross_source_overlap_excess_ha"].sum()),
        "files_sha256": {},
    }
    if args.limit is None:
        summary["files_sha256"] = {
            str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
            for path in (GMW, EEZ, pair_path, unit_path)
        }
        SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Pair table: {pair_path}")
    print(f"EEZ-unit table: {unit_path}")


if __name__ == "__main__":
    main()
