"""Test a GMW 2025 replacement for mangrove area without changing main outputs.

The GMW country workbook and Hilmi EEZ areas have different territory boundaries.
This is a national-area sensitivity test, not the final spatial update of BCW.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "validation"
COMPARISON = OUT / "mangrove_area_source_comparison.csv"

# Codes in the GMW workbook that represent a component of an existing BNC2 unit.
GMW_UNIT_ALIASES = {
    "ATF_EI": "ATF-4",  # Europa Island
    "BES_B": "BES",  # Bonaire
    "MUS_CA": "MUS",  # Cargados Carajos
    "TWN": "CHN",  # FRA China's reporting unit includes Taiwan
}


def main() -> None:
    comparison = pd.read_csv(COMPARISON)
    gmw = comparison.loc[
        comparison["gmw_mangroves_ha"].fillna(0) > 0,
        ["iso3", "gmw_mangroves_ha"],
    ].copy()
    gmw["iso3"] = gmw["iso3"].replace(GMW_UNIT_ALIASES)
    gmw = gmw.groupby("iso3", as_index=False)["gmw_mangroves_ha"].sum()

    hilmi = comparison.groupby("iso3", as_index=False)[
        ["hilmi_mangroves_ha", "project_bcw_mangroves_ha", "fra_mangroves_ha"]
    ].sum(min_count=1)
    table = hilmi.merge(gmw, on="iso3", how="outer", validate="one_to_one")
    for column in ["hilmi_mangroves_ha", "project_bcw_mangroves_ha", "fra_mangroves_ha", "gmw_mangroves_ha"]:
        table[column] = table[column].fillna(0)
    table["current_minus_gmw_ha"] = (
        table["project_bcw_mangroves_ha"] - table["gmw_mangroves_ha"]
    )
    table["gmw_missing_where_current_positive"] = (
        (table["project_bcw_mangroves_ha"] > 0) & (table["gmw_mangroves_ha"] == 0)
    )
    table["gmw_new_where_current_zero"] = (
        (table["project_bcw_mangroves_ha"] == 0) & (table["gmw_mangroves_ha"] > 0)
    )

    with np.load(ROOT / "data" / "raw" / "environmental" / "marine" / "bcw" / "output" / "draws.npz", allow_pickle=True) as raw:
        rate = raw["bce_rates_draws"][2].astype(np.float64)
        gscc = raw["gscc_draws"].astype(np.float64)
    with np.load(ROOT / "results" / "draws" / "ncw_draws.npz", allow_pickle=True) as current:
        current_iso = current["iso3"].astype(str)
        current_bcw = current["bcw_usd2015_yr"].astype(np.float64)

    current_index = {iso: row for row, iso in enumerate(current_iso)}
    # Include GMW units absent from the current NCW archive in the global test.
    # Their other BCW components remain unavailable here, so results for those
    # units are mangrove-only sensitivities, not a complete national BCW estimate.
    all_units = sorted(set(current_iso) | set(gmw["iso3"]))
    old_area = table.set_index("iso3")["project_bcw_mangroves_ha"]
    new_area = table.set_index("iso3")["gmw_mangroves_ha"]
    values = np.full((len(all_units), len(rate)), np.nan, dtype=np.float64)
    delta = np.zeros_like(values)
    for row, iso in enumerate(all_units):
        if iso in current_index:
            values[row] = current_bcw[current_index[iso]]
        change_ha = new_area.get(iso, 0.0) - old_area.get(iso, 0.0)
        delta[row] = change_ha / 100.0 * rate * (44.0 / 12.0) * gscc
        if iso not in current_index and change_ha > 0:
            values[row] = 0.0
    adjusted = values + delta

    table = table.set_index("iso3").reindex(all_units).reset_index()
    table["current_bcw_mean_billion_usd2015_yr"] = np.where(
        np.isnan(values).all(axis=1), np.nan, np.nan_to_num(values).mean(axis=1) / 1e9
    )
    table["gmw_area_test_bcw_mean_billion_usd2015_yr"] = np.where(
        np.isnan(adjusted).all(axis=1), np.nan, np.nan_to_num(adjusted).mean(axis=1) / 1e9
    )
    table["gmw_area_test_delta_billion_usd2015_yr"] = np.mean(delta, axis=1) / 1e9
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "gmw_2025_mangrove_replacement_test_by_unit.csv", index=False)

    current_world = np.nansum(values, axis=0)
    adjusted_world = np.nansum(adjusted, axis=0)
    # GMW absence is not proof of ecological absence. Keep the earlier area for
    # the three unmatched positive units as an explicit coverage sensitivity.
    missing_mask = table["gmw_missing_where_current_positive"].eq(True)
    missing_area = table.loc[missing_mask, "project_bcw_mangroves_ha"].sum()
    retained_missing_world = adjusted_world + missing_area / 100.0 * rate * (44.0 / 12.0) * gscc
    world = pd.DataFrame(
        {
            "case": ["current_bcw", "gmw_2025_country_area_test", "gmw_keep_unmapped_current_area", "difference"],
            "mean_billion_usd2015_yr": [
                current_world.mean() / 1e9,
                adjusted_world.mean() / 1e9,
                retained_missing_world.mean() / 1e9,
                (adjusted_world - current_world).mean() / 1e9,
            ],
            "p05_billion_usd2015_yr": [
                np.percentile(current_world, 5) / 1e9,
                np.percentile(adjusted_world, 5) / 1e9,
                np.percentile(retained_missing_world, 5) / 1e9,
                np.percentile(adjusted_world - current_world, 5) / 1e9,
            ],
            "p95_billion_usd2015_yr": [
                np.percentile(current_world, 95) / 1e9,
                np.percentile(adjusted_world, 95) / 1e9,
                np.percentile(retained_missing_world, 95) / 1e9,
                np.percentile(adjusted_world - current_world, 95) / 1e9,
            ],
        }
    )
    world.to_csv(OUT / "gmw_2025_mangrove_replacement_test_world.csv", index=False)

    current_mangrove_ha = table["project_bcw_mangroves_ha"].sum()
    gmw_mangrove_ha = table["gmw_mangroves_ha"].sum()
    mangrove_only = pd.DataFrame(
        {
            "case": ["current_mangrove_component", "gmw_2025_mangrove_component"],
            "area_ha": [current_mangrove_ha, gmw_mangrove_ha],
            "mean_MtC_yr": [current_mangrove_ha, gmw_mangrove_ha],
        }
    )
    for column, percentile in [("p05", 5), ("p95", 95)]:
        mangrove_only[f"{column}_billion_usd2015_yr"] = [
            np.percentile(area / 100.0 * rate * (44.0 / 12.0) * gscc, percentile) / 1e9
            for area in (current_mangrove_ha, gmw_mangrove_ha)
        ]
    mangrove_only["mean_MtC_yr"] *= rate.mean() / 100.0 / 1e6
    mangrove_only["mean_billion_usd2015_yr"] = [
        (area / 100.0 * rate * (44.0 / 12.0) * gscc).mean() / 1e9
        for area in (current_mangrove_ha, gmw_mangrove_ha)
    ]
    mangrove_only.to_csv(OUT / "gmw_2025_mangrove_component_test_world.csv", index=False)

    print(f"GMW positive units after code harmonisation: {(table['gmw_mangroves_ha'] > 0).sum()}")
    print(f"Current BCW positive mangrove units: {(table['project_bcw_mangroves_ha'] > 0).sum()}")
    print(f"Current positive, GMW absent: {table['gmw_missing_where_current_positive'].sum()}")
    print(f"GMW positive, current absent: {table['gmw_new_where_current_zero'].sum()}")
    print(f"Current mangrove area: {table['project_bcw_mangroves_ha'].sum():,.1f} ha")
    print(f"GMW mangrove area: {table['gmw_mangroves_ha'].sum():,.1f} ha")
    print(world.to_string(index=False))
    print(mangrove_only.to_string(index=False))


if __name__ == "__main__":
    main()
