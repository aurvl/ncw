"""Correct and aggregate the direct GMW-to-EEZ overlay into BCW account units.

The source-code label in GMW is retained in the spatial audit table. National
and territory assignment follows the intersected EEZ UNION unit; only EEZ units
classified as ``Union EEZ and country`` enter the national account. The raw
intersection areas are multiplied by GMW's published global accuracy factor
before they enter the account. Both raw and corrected areas are retained.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
VALIDATION = ROOT / "data/outputs/validation"
UNIT_OVERLAY = VALIDATION / "gmw_2025_direct_overlay_area_by_eez_unit.csv"
PAIR_OVERLAY = VALIDATION / "gmw_2025_direct_overlay_by_eez_unit_and_source.csv"
OVERLAY_SUMMARY = VALIDATION / "gmw_2025_direct_overlay_summary.json"
EEZ_SOURCE = DATA / "raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp"
GMW_SOURCE = DATA / "raw/environmental/marine/gmw/gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg"
TERRITORIES = DATA / "derived/territories.csv"
BCW_CROSSWALK = DATA / "derived/bcw_territory_mapping.csv"
MAIN_OUTPUT = DATA / "derived/gmw_2025_mangrove_area_by_unit.csv"
PROVENANCE_OUTPUT = DATA / "derived/gmw_2025_mangrove_area_provenance.json"
ACCOUNT_AUDIT = VALIDATION / "gmw_2025_direct_area_by_account_iso3.csv"
UNIT_AUDIT = VALIDATION / "gmw_2025_direct_area_eez_crosswalk.csv"
GMW_AREA_CORRECTION_FACTOR = 0.9775


def _normalize(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    for path in (UNIT_OVERLAY, PAIR_OVERLAY, OVERLAY_SUMMARY, EEZ_SOURCE, GMW_SOURCE):
        if not path.is_file():
            raise FileNotFoundError(f"Required direct GMW overlay file is missing: {path}")

    overlay_summary = json.loads(OVERLAY_SUMMARY.read_text(encoding="utf-8"))
    expected_gmw = overlay_summary["files_sha256"].get(
        str(GMW_SOURCE.relative_to(ROOT)).replace("\\", "/")
    )
    expected_eez = overlay_summary["files_sha256"].get(
        str(EEZ_SOURCE.relative_to(ROOT)).replace("\\", "/")
    )
    if expected_gmw != _sha256(GMW_SOURCE) or expected_eez != _sha256(EEZ_SOURCE):
        raise ValueError(
            "The GMW or EEZ source changed after the spatial overlay. "
            "Rerun overlay_gmw_2025_direct_eez.py before building account areas."
        )

    units = pd.read_csv(UNIT_OVERLAY)
    crosswalk = pd.read_csv(BCW_CROSSWALK)
    study_units = pd.read_csv(TERRITORIES, usecols=["iso3"])["iso3"].dropna().astype(str)
    valid_study_units = set(study_units)

    name_to_unit: dict[str, str] = {}
    for name, code in zip(crosswalk["bcw_name"], crosswalk["unit_code"]):
        normalized = _normalize(name)
        previous = name_to_unit.setdefault(normalized, str(code).strip())
        if previous != str(code).strip():
            raise ValueError(f"Ambiguous BCW territory-name crosswalk for {name!r}")

    country_units = units.loc[
        units["eez_polygon_type"].eq("Union EEZ and country")
    ].copy()
    country_units["gmw_direct_overlay_area_raw_ha"] = country_units[
        "gmw_direct_overlay_area_ha"
    ].astype(float)
    if (
        not np.isfinite(country_units["gmw_direct_overlay_area_raw_ha"]).all()
        or country_units["gmw_direct_overlay_area_raw_ha"].lt(0).any()
    ):
        raise ValueError("Raw direct GMW account areas must be finite and non-negative")
    country_units["gmw_area_correction_factor"] = GMW_AREA_CORRECTION_FACTOR
    country_units["gmw_direct_overlay_area_corrected_ha"] = (
        country_units["gmw_direct_overlay_area_raw_ha"]
        * GMW_AREA_CORRECTION_FACTOR
    )
    if not np.allclose(
        country_units["gmw_direct_overlay_area_corrected_ha"],
        country_units["gmw_direct_overlay_area_raw_ha"] * GMW_AREA_CORRECTION_FACTOR,
        rtol=0,
        atol=1e-10,
    ):
        raise ValueError("Corrected GMW intersections do not match the published global factor")
    country_units["accounting_unit_code"] = country_units["eez_territory_name"].map(
        lambda name: name_to_unit.get(_normalize(name))
    )
    country_units["accounting_unit_mapping"] = np.where(
        country_units["accounting_unit_code"].notna(), "BCW territory-name crosswalk", ""
    )
    for index in country_units.index[country_units["accounting_unit_code"].isna()]:
        territory_code = country_units.at[index, "eez_iso3"]
        sovereign_code = country_units.at[index, "eez_sovereign_iso3"]
        if pd.notna(territory_code) and str(territory_code) in valid_study_units:
            country_units.at[index, "accounting_unit_code"] = str(territory_code)
            country_units.at[index, "accounting_unit_mapping"] = "EEZ ISO_TER1"
        elif pd.notna(sovereign_code) and str(sovereign_code) in valid_study_units:
            country_units.at[index, "accounting_unit_code"] = str(sovereign_code)
            country_units.at[index, "accounting_unit_mapping"] = "EEZ ISO_SOV1 fallback"

    positive_unmapped = country_units.loc[
        country_units["gmw_direct_overlay_area_raw_ha"].gt(0)
        & country_units["accounting_unit_code"].isna(),
        ["eez_union", "eez_territory_name", "eez_iso3", "eez_sovereign_iso3", "gmw_direct_overlay_area_raw_ha"],
    ]
    if not positive_unmapped.empty:
        raise ValueError(
            "Positive GMW area could not be mapped to a study unit:\n"
            + positive_unmapped.to_string(index=False)
        )
    unknown_units = country_units.loc[
        country_units["accounting_unit_code"].notna()
        & ~country_units["accounting_unit_code"].isin(valid_study_units),
        ["eez_union", "accounting_unit_code"],
    ]
    if not unknown_units.empty:
        raise ValueError("EEZ crosswalk produced unknown study-unit codes:\n" + unknown_units.to_string(index=False))

    account_areas = (
        country_units.loc[country_units["accounting_unit_code"].notna()]
        .groupby("accounting_unit_code", as_index=False)
        .agg(
            gmw_2025_mangrove_area_raw_ha=("gmw_direct_overlay_area_raw_ha", "sum"),
            gmw_2025_mangrove_area_ha=("gmw_direct_overlay_area_corrected_ha", "sum"),
            eez_union_unit_count=("eez_union", "nunique"),
        )
        .rename(columns={"accounting_unit_code": "iso3"})
        .sort_values("iso3")
        .reset_index(drop=True)
    )
    if account_areas["iso3"].duplicated().any() or (account_areas["gmw_2025_mangrove_area_ha"] < 0).any():
        raise ValueError("Direct GMW account areas are duplicated or negative")
    if not np.isclose(
        account_areas["gmw_2025_mangrove_area_ha"].sum(),
        account_areas["gmw_2025_mangrove_area_raw_ha"].sum() * GMW_AREA_CORRECTION_FACTOR,
        rtol=0,
        atol=1e-7,
    ):
        raise ValueError("Aggregated corrected GMW area does not conserve the global factor")

    crosswalk_audit = country_units[
        [
            "eez_union", "eez_iso3", "eez_sovereign_iso3", "eez_territory_name",
            "accounting_unit_code", "accounting_unit_mapping",
            "gmw_direct_overlay_area_raw_ha", "gmw_area_correction_factor",
            "gmw_direct_overlay_area_corrected_ha",
        ]
    ].sort_values("eez_union")
    MAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    final = account_areas[
        ["iso3", "gmw_2025_mangrove_area_raw_ha", "gmw_2025_mangrove_area_ha"]
    ]
    final.to_csv(MAIN_OUTPUT, index=False)
    account_areas.to_csv(ACCOUNT_AUDIT, index=False)
    crosswalk_audit.to_csv(UNIT_AUDIT, index=False)

    provenance_files = [
        GMW_SOURCE, EEZ_SOURCE, PAIR_OVERLAY, UNIT_OVERLAY, MAIN_OUTPUT,
        ACCOUNT_AUDIT, UNIT_AUDIT,
    ]
    provenance = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": "GMW v4.1.12 2025; direct Mollweide spatial intersection by EEZ UNION",
        "area_measurement": "Direct GMW polygon x EEZ UNION intersection in Mollweide; raw geometric area is retained before GMW's global accuracy correction.",
        "area_correction_applied": True,
        "area_correction_factor": GMW_AREA_CORRECTION_FACTOR,
        "area_correction_source": "GMW v4.1.12 README: a global overestimate was identified by the accuracy assessment; 0.9775 is used for all mangrove extent estimates.",
        "raw_account_area_sum_ha": float(final["gmw_2025_mangrove_area_raw_ha"].sum()),
        "corrected_account_area_sum_ha": float(final["gmw_2025_mangrove_area_ha"].sum()),
        "accounting_rule": "EEZ units classified Union EEZ and country; territory-name crosswalk first, then ISO_TER1 and ISO_SOV1 fallback",
        "files_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
            for path in provenance_files
        },
    }
    PROVENANCE_OUTPUT.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(final)} study units from {len(country_units)} EEZ country/territory units; "
        f"{final['gmw_2025_mangrove_area_raw_ha'].sum():,.2f} ha raw; "
        f"{final['gmw_2025_mangrove_area_ha'].sum():,.2f} ha after the GMW "
        f"{GMW_AREA_CORRECTION_FACTOR:.4f} global accuracy correction."
    )


if __name__ == "__main__":
    main()
