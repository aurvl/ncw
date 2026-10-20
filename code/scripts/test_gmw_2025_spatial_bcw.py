"""Compare BCW mangrove cases using raw and GMW accuracy-corrected areas.

The base case is the published BCW mangrove area plus the existing FRA gap-fill.
Alternative cases replace that area draw-by-draw while retaining all non-mangrove
BCW components and the same rate and GSCC draws.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/validation"
ALIASES = {"ATF_EI": "ATF-4", "BES_B": "BES", "MUS_CA": "MUS", "TWN": "CHN"}


def _series_from(frame: pd.DataFrame, key: str, value: str) -> pd.Series:
    if frame[key].duplicated().any():
        raise ValueError(f"Duplicate {key} in {value} area input")
    return frame.set_index(key)[value].astype(float)


def main() -> None:
    overlay = pd.read_csv(OUT / "gmw_2025_eez_overlay_by_source_unit.csv")
    transfers = pd.read_csv(OUT / "gmw_2025_eez_residual_reassignment.csv")
    source_audit = pd.read_csv(OUT / "gmw_2025_corrected_area_audit_by_source.csv")
    factor = _series_from(source_audit, "gmw_iso3", "correction_factor_official_country")

    raw_final = pd.read_csv(OUT / "gmw_2025_eez_final_area_by_unit.csv")
    raw_final = _series_from(raw_final, "iso3", "final_eez_ha")
    raw_final.index = raw_final.index.map(lambda x: ALIASES.get(x, x))
    raw_final = raw_final.groupby(level=0).sum()

    raw_within = overlay[["gmw_iso3", "within_matching_eez_ha"]].copy()
    raw_within["iso3"] = raw_within.gmw_iso3.replace(ALIASES)
    strict_raw = raw_within.groupby("iso3").within_matching_eez_ha.sum()
    strict_corrected = raw_within.assign(
        corrected_ha=raw_within.within_matching_eez_ha * raw_within.gmw_iso3.map(factor)
    ).groupby("iso3").corrected_ha.sum()

    official_country = source_audit.assign(iso3=source_audit.gmw_iso3.replace(ALIASES))
    official_country = official_country.groupby("iso3").official_corrected_2025_ha.sum()
    corrected_spatial = pd.read_csv(OUT / "gmw_2025_corrected_spatial_area_by_unit.csv")
    corrected_spatial = _series_from(corrected_spatial, "iso3", "final_corrected_ha")

    old_area_frame = pd.read_csv(ROOT / "data/derived/bcw_mangrove_gmw_area_replacement.csv")
    old_area = _series_from(old_area_frame, "iso3", "bcw_mangroves_before_gmw_ha")

    bcw_path = ROOT / "results/draws/ncw_draws.npz"
    marine_path = ROOT / "data/raw/environmental/marine/bcw/output/draws.npz"
    with np.load(bcw_path, allow_pickle=True) as data:
        world_current = np.nansum(data["bcw_usd2015_yr"].astype(np.float64), axis=0)
        published_rows = np.nansum(data["bcw_published_rows_usd2015_yr"].astype(np.float64), axis=0)
        gapfill = np.nansum(data["bcw_mangrove_gapfill_usd2015_yr"].astype(np.float64), axis=0)
        adjustment = np.nansum(data["bcw_gmw_mangrove_adjustment_usd2015_yr"].astype(np.float64), axis=0)
    with np.load(marine_path, allow_pickle=True) as data:
        rate = data["bce_rates_draws"][2].astype(np.float64)
        gscc = data["gscc_draws"].astype(np.float64)
    if not (len(rate) == len(gscc) == len(world_current)):
        raise ValueError("BCW rate, GSCC and country draw lengths do not align")

    original_bcw = published_rows + gapfill
    if not np.allclose(world_current, original_bcw + adjustment, rtol=2e-6, atol=10.0):
        raise ValueError("Current BCW does not reconcile to published rows + gap-fill + GMW adjustment")

    scenarios = {
        "published_hilmi_area": old_area,
        "gmw_raw_polygon_reassigned": raw_final,
        "gmw_raw_matching_eez_only": strict_raw,
        "gmw_official_corrected_country_stats": official_country,
        "gmw_corrected_matching_eez_only": strict_corrected,
        "gmw_official_corrected_spatial_reassigned": corrected_spatial,
    }
    codes = sorted(set(old_area.index).union(*(series.index for series in scenarios.values())))
    old_aligned = old_area.reindex(codes, fill_value=0.0)
    detail = pd.DataFrame({"iso3": codes, "published_hilmi_area_ha": old_aligned.to_numpy()})
    rate_mean = float(rate.mean())
    value_per_ha_mean = float(((rate * (44.0 / 12.0) * gscc) / 100.0).mean())

    world_rows = []
    for name, areas in scenarios.items():
        aligned = areas.reindex(codes, fill_value=0.0).astype(float)
        delta_ha = aligned.to_numpy() - old_aligned.to_numpy()
        delta_draws = (delta_ha.sum() / 100.0) * rate * (44.0 / 12.0) * gscc
        total_bcw = original_bcw + delta_draws
        mangrove_values = (aligned.sum() / 100.0) * rate * (44.0 / 12.0) * gscc
        detail[f"{name}_ha"] = aligned.to_numpy()
        detail[f"{name}_delta_value_billion_usd2015_yr"] = (
            delta_ha * value_per_ha_mean / 1e9
        )
        world_rows.append({
            "case": name,
            "area_ha_assigned": float(aligned.sum()),
            "mean_mangrove_MtC_yr": float(aligned.sum() / 100.0 * rate_mean / 1e6),
            "mean_mangrove_value_billion_usd2015_yr": float(mangrove_values.mean() / 1e9),
            "mean_total_bcw_billion_usd2015_yr": float(total_bcw.mean() / 1e9),
            "p05_total_bcw_billion_usd2015_yr": float(np.percentile(total_bcw, 5) / 1e9),
            "p95_total_bcw_billion_usd2015_yr": float(np.percentile(total_bcw, 95) / 1e9),
            "area_difference_from_published_hilmi_ha": float(aligned.sum() - old_aligned.sum()),
        })
    detail.to_csv(OUT / "gmw_2025_spatial_bcw_by_unit.csv", index=False)
    world = pd.DataFrame(world_rows)
    world.to_csv(OUT / "gmw_2025_spatial_bcw_world.csv", index=False)
    print(world.to_string(index=False))


if __name__ == "__main__":
    main()
