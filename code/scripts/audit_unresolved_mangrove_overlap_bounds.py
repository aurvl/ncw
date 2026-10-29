"""Quantify the algebraic upper bound from unclassified FRA mangrove hectares.

The official FRA-first account is unchanged. This audit asks what the largest
additional tropical Forest overlap could be if every currently unclassified
mangrove hectare were in Forest, subject to available tropical Forest area.
It is a bound, not an estimate or a probability interval.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
VALIDATION = ROOT / "results" / "validation"
CO2_PER_C = 44.0 / 12.0


def build() -> tuple[pd.DataFrame, dict]:
    areas = pd.read_csv(DERIVED / "forest_area_by_biome.csv")
    tropical_rows = areas.loc[
        areas["variant"].eq("documented_overlap_removed") & areas["biome"].eq("tropical"),
        ["iso3", "area_ha"],
    ].copy()
    if tropical_rows["iso3"].duplicated().any():
        raise ValueError("Expected one tropical forest area per unit")
    unknown_by_unit = areas.loc[
        areas["variant"].eq("documented_overlap_removed"),
        ["iso3", "unresolved_fra_mangrove_category_ha"],
    ].drop_duplicates("iso3")
    source = pd.read_csv(DERIVED / "forest_areas.csv")
    reported = source.loc[source["year"].astype(str).eq("2025"), ["iso3", "mangroves_reported"]]
    uptake = pd.read_csv(DERIVED / "forest_uptake_gfw.csv")[["iso3", "uptake_tco2_yr_mean"]]
    table = uptake.merge(unknown_by_unit, on="iso3", how="left", validate="one_to_one")
    table = table.merge(tropical_rows, on="iso3", how="left", validate="one_to_one")
    table["has_tropical_forest_row"] = table["area_ha"].notna()
    table["area_ha"] = table["area_ha"].fillna(0.0)
    table = table.merge(reported, on="iso3", how="left", validate="one_to_one")
    rates = pd.read_csv(DERIVED / "gfw_gibbs_biome_rates_non_mangrove.csv").set_index("biome")
    tropical_rate = float(rates.loc["tropical", "rate_tc_ha_yr_mean"])
    unknown = table["unresolved_fra_mangrove_category_ha"].fillna(0.0).clip(lower=0.0)
    available = table["area_ha"].clip(lower=0.0)
    table["additional_overlap_upper_bound_ha"] = np.minimum(unknown, available)
    table["forest_additions_reduction_upper_bound_tco2_yr"] = (
        table["additional_overlap_upper_bound_ha"] * tropical_rate * CO2_PER_C
    )
    table["forest_additions_lower_bound_tco2_yr"] = (
        table["uptake_tco2_yr_mean"] - table["forest_additions_reduction_upper_bound_tco2_yr"]
    )
    if (
        table["forest_additions_lower_bound_tco2_yr"]
        < -1e-6 * table["uptake_tco2_yr_mean"].clip(lower=1.0)
    ).any():
        raise ValueError("Overlap bound exceeds current modeled forest additions")
    table["forest_additions_lower_bound_tco2_yr"] = table[
        "forest_additions_lower_bound_tco2_yr"
    ].clip(lower=0.0)
    summary = {
        "scenario": "all unclassified FRA mangrove area in tropical Forest, capped by available tropical Forest area",
        "status": "algebraic sensitivity bound; canonical FRA-first account unchanged",
        "units_with_unclassified_area": int(unknown.gt(0).sum()),
        "unclassified_mangrove_area_all_units_ha": float(unknown.sum()),
        "unclassified_mangrove_area_with_tropical_forest_row_ha": float(
            unknown[table["has_tropical_forest_row"]].sum()
        ),
        "additional_overlap_upper_bound_ha": float(table["additional_overlap_upper_bound_ha"].sum()),
        "forest_additions_reduction_upper_bound_tco2_yr": float(
            table["forest_additions_reduction_upper_bound_tco2_yr"].sum()
        ),
        "current_forest_additions_global_tco2_yr": float(uptake["uptake_tco2_yr_mean"].sum()),
        "current_forest_additions_tropical_row_units_tco2_yr": float(
            table.loc[table["has_tropical_forest_row"], "uptake_tco2_yr_mean"].sum()
        ),
    }
    summary["reduction_upper_bound_pct_of_current_forest_additions"] = (
        100 * summary["forest_additions_reduction_upper_bound_tco2_yr"]
        / summary["current_forest_additions_global_tco2_yr"]
    )
    return table, summary


def main() -> None:
    table, summary = build()
    VALIDATION.mkdir(parents=True, exist_ok=True)
    table.to_csv(VALIDATION / "fra_unresolved_mangrove_overlap_bounds.csv", index=False)
    (VALIDATION / "fra_unresolved_mangrove_overlap_bounds.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
