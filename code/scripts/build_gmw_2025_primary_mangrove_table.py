"""Build GMW 2025 areas harmonised to the official corrected-area statistics.

The vector geometry is retained for spatial attribution to the project's EEZs.
Each source-code area and its residual transfers are scaled to the corresponding
GMW corrected country statistic. The GMW README documents the uniform 0.9775
accuracy correction; matching the workbook by source code also audits the
allocation at the exact published country/territory level.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
VALIDATION = ROOT / "data/derived/validation"
RAW_GMW = DATA / "raw/environmental/marine/gmw"
STATS_XLSX = RAW_GMW / "gmw_v4_timeseries_4112_gmw_country_stats_corr_area_formatted.xlsx"
MAIN_OUTPUT = DATA / "derived/gmw_2025_mangrove_area_by_unit.csv"
PROVENANCE_OUTPUT = DATA / "derived/gmw_2025_mangrove_area_provenance.json"
UNIT_AUDIT = VALIDATION / "gmw_2025_corrected_spatial_area_by_unit.csv"
SOURCE_AUDIT = VALIDATION / "gmw_2025_corrected_area_audit_by_source.csv"
SUMMARY_AUDIT = VALIDATION / "gmw_2025_corrected_area_summary.csv"
PUBLISHED_CORRECTION_FACTOR = 0.9775
ALIASES = {"ATF_EI": "ATF-4", "BES_B": "BES", "MUS_CA": "MUS", "TWN": "CHN"}


def _column_for_year(frame: pd.DataFrame, year: int) -> str | int:
    matches = [column for column in frame.columns if str(column).strip() == str(year)]
    if len(matches) != 1:
        raise ValueError(f"Expected one {year} column in GMW stats, found {matches}")
    return matches[0]


def main() -> None:
    overlay = pd.read_csv(VALIDATION / "gmw_2025_eez_overlay_by_source_unit.csv")
    transfers = pd.read_csv(VALIDATION / "gmw_2025_eez_residual_reassignment.csv")
    stats = pd.read_excel(STATS_XLSX, sheet_name="Extent")
    year_col = _column_for_year(stats, 2025)
    stats = stats[["iso", "cnty_name", year_col]].dropna(subset=["iso"]).copy()
    stats["gmw_iso3"] = stats["iso"].astype(str).str.strip()
    stats["official_corrected_2025_ha"] = pd.to_numeric(stats[year_col], errors="coerce")
    stats = stats.loc[stats["official_corrected_2025_ha"].notna()]
    if stats["gmw_iso3"].duplicated().any():
        raise ValueError("GMW corrected country statistics contain duplicate source codes")

    source = overlay.merge(
        stats[["gmw_iso3", "cnty_name", "official_corrected_2025_ha"]],
        on="gmw_iso3", how="outer", validate="one_to_one", indicator=True,
    )
    unmatched = source.loc[source["_merge"] != "both", ["gmw_iso3", "_merge"]]
    if not unmatched.empty:
        raise ValueError(f"GMW vector/stat source codes do not reconcile:\n{unmatched.to_string(index=False)}")
    source = source.drop(columns="_merge")
    source["correction_factor_official_country"] = (
        source["official_corrected_2025_ha"] / source["raw_ha"]
    )
    if (~np.isfinite(source["correction_factor_official_country"])).any():
        raise ValueError("A source-code correction factor is not finite")
    if not np.allclose(
        source["correction_factor_official_country"], PUBLISHED_CORRECTION_FACTOR,
        rtol=0, atol=1e-5,
    ):
        raise ValueError("Corrected statistics do not match the documented 0.9775 factor")
    if not np.allclose(
        source["correction_factor_official_country"],
        source["correction_factor_official_country"].iloc[0], rtol=0, atol=1e-10,
    ):
        raise ValueError("GMW corrected areas are not a uniform factor of the vector areas")

    factor = source.set_index("gmw_iso3")["correction_factor_official_country"]
    source["scaled_geometry_area_ha"] = source["raw_ha"] * source["correction_factor_official_country"]
    source["official_minus_scaled_geometry_ha"] = (
        source["official_corrected_2025_ha"] - source["scaled_geometry_area_ha"]
    )

    # Scale the matched-EEZ part and the residual movements by their GMW source
    # code's published correction. This retains the same spatial allocation.
    within = overlay[["gmw_iso3", "within_matching_eez_ha"]].copy()
    within["corrected_ha"] = within["within_matching_eez_ha"] * within["gmw_iso3"].map(factor)
    within["iso3"] = within["gmw_iso3"].replace(ALIASES)
    within_by_unit = within.groupby("iso3", as_index=False)["corrected_ha"].sum()

    transfers = transfers.copy()
    transfers["correction_factor"] = transfers["gmw_source_iso3"].map(factor)
    if transfers["correction_factor"].isna().any():
        bad = transfers.loc[transfers["correction_factor"].isna(), "gmw_source_iso3"].unique().tolist()
        raise ValueError(f"Residual transfers have no source correction factor: {bad}")
    transfers["corrected_ha"] = transfers["area_ha"] * transfers["correction_factor"]
    transfers["iso3"] = transfers["eez_destination_iso3"].replace(ALIASES)
    received_by_unit = transfers.groupby("iso3", as_index=False)["corrected_ha"].sum()

    units = within_by_unit.merge(received_by_unit, on="iso3", how="outer", suffixes=("_within", "_received"))
    units = units.fillna(0.0).rename(columns={
        "corrected_ha_within": "within_matching_eez_corrected_ha",
        "corrected_ha_received": "received_by_eez_corrected_ha",
    })
    units["final_corrected_ha"] = (
        units["within_matching_eez_corrected_ha"] + units["received_by_eez_corrected_ha"]
    )
    units = units.sort_values("iso3").reset_index(drop=True)

    moved_by_source = transfers.groupby("gmw_source_iso3")["area_ha"].sum()
    source["residual_reassigned_raw_ha"] = source["gmw_iso3"].map(moved_by_source).fillna(0.0)
    if (source["residual_reassigned_raw_ha"] - source["outside_matching_eez_ha"] > 0.05).any():
        raise ValueError("Reassigned area exceeds the source-code area outside its matching EEZ")
    source["unassigned_corrected_ha"] = (
        source["outside_matching_eez_ha"] - source["residual_reassigned_raw_ha"]
    ).clip(lower=0.0) * source["correction_factor_official_country"]
    source["assigned_corrected_ha"] = (
        source["within_matching_eez_ha"] + source["residual_reassigned_raw_ha"]
    ) * source["correction_factor_official_country"]

    official_total = float(source["official_corrected_2025_ha"].sum())
    assigned_total = float(units["final_corrected_ha"].sum())
    unassigned_total = float(source["unassigned_corrected_ha"].sum())
    if not np.isclose(assigned_total + unassigned_total, official_total, atol=0.1, rtol=0):
        raise ValueError(
            "Corrected spatial allocation does not conserve the official area: "
            f"assigned {assigned_total:.4f} + unassigned {unassigned_total:.4f} "
            f"!= official {official_total:.4f} ha"
        )
    if not np.isclose(source["assigned_corrected_ha"].sum(), assigned_total, atol=0.1, rtol=0):
        raise ValueError("Source audit and country allocation totals differ")

    main = units[["iso3", "final_corrected_ha"]].rename(columns={
        "final_corrected_ha": "gmw_2025_mangrove_area_ha"
    })
    if main["iso3"].duplicated().any() or (main["gmw_2025_mangrove_area_ha"] < 0).any():
        raise ValueError("Corrected country area table has duplicates or negative values")
    MAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    main.to_csv(MAIN_OUTPUT, index=False)
    provenance_files = [
        STATS_XLSX,
        VALIDATION / "gmw_2025_eez_overlay_by_source_unit.csv",
        VALIDATION / "gmw_2025_eez_residual_reassignment.csv",
        MAIN_OUTPUT,
    ]
    provenance = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": "GMW v4.1.12, corrected 2025 country areas",
        "files_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in provenance_files
        },
    }
    PROVENANCE_OUTPUT.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    units.to_csv(UNIT_AUDIT, index=False)
    source[[
        "gmw_iso3", "cnty_name", "raw_ha", "official_corrected_2025_ha",
        "correction_factor_official_country", "scaled_geometry_area_ha",
        "official_minus_scaled_geometry_ha", "within_matching_eez_ha",
        "outside_matching_eez_ha", "residual_reassigned_raw_ha",
        "assigned_corrected_ha", "unassigned_corrected_ha",
    ]].sort_values("gmw_iso3").to_csv(SOURCE_AUDIT, index=False)
    pd.DataFrame([{
        "vector_raw_ha": float(source["raw_ha"].sum()),
        "published_corrected_total_ha": official_total,
        "documented_factor": PUBLISHED_CORRECTION_FACTOR,
        "observed_country_factor_min": float(source["correction_factor_official_country"].min()),
        "observed_country_factor_max": float(source["correction_factor_official_country"].max()),
        "spatial_assigned_corrected_ha": assigned_total,
        "spatial_unassigned_corrected_ha": unassigned_total,
        "conservation_residual_ha": assigned_total + unassigned_total - official_total,
        "spatial_accounting_units": int(len(main)),
        "source_country_codes": int(len(source)),
    }]).to_csv(SUMMARY_AUDIT, index=False)

    print(
        f"Wrote {len(main)} accounting units; {assigned_total:,.2f} ha assigned, "
        f"{unassigned_total:,.2f} ha unassigned, official corrected total "
        f"{official_total:,.2f} ha; correction factors "
        f"{source['correction_factor_official_country'].min():.9f}-"
        f"{source['correction_factor_official_country'].max():.9f}."
    )


if __name__ == "__main__":
    main()
