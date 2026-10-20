"""Audit how excluding source-model mangrove pixels changes the four rates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "data/summary"
VALIDATION = ROOT / "results/validation"
BIOMES = ["tropical", "subtropical", "temperate", "boreal"]


def main() -> None:
    old_path = SUMMARY / "gfw_gibbs_biome_rates_with_mangroves.csv"
    if not old_path.is_file():
        old_path = SUMMARY / "gfw_gibbs_biome_rates.csv"
    old = pd.read_csv(old_path).set_index("biome")
    clean = pd.read_csv(SUMMARY / "gfw_gibbs_biome_rates_non_mangrove.csv").set_index("biome")
    if set(old.index) != set(BIOMES) or set(clean.index) != set(BIOMES):
        raise ValueError("Both rate tables must contain exactly the four FAO GEZ biomes")
    rows = []
    for biome in BIOMES:
        before, after = old.loc[biome], clean.loc[biome]
        excluded = float(after.excluded_mangrove_area_ha)
        assert excluded >= 0
        assert np.isclose(float(before.area_ha), float(after.area_ha) + excluded, rtol=1e-6)
        assert int(before.pixel_count) == int(after.pixel_count) + int(after.excluded_mangrove_pixel_count)
        rows.append(
            {
                "biome": biome,
                "all_forest_rate_tc_ha_yr": float(before.rate_tc_ha_yr_mean),
                "non_mangrove_rate_tc_ha_yr": float(after.rate_tc_ha_yr_mean),
                "rate_change_tc_ha_yr": float(after.rate_tc_ha_yr_mean - before.rate_tc_ha_yr_mean),
                "rate_change_percent": 100.0 * (
                    float(after.rate_tc_ha_yr_mean / before.rate_tc_ha_yr_mean) - 1.0
                ),
                "all_valid_area_ha": float(before.area_ha),
                "non_mangrove_valid_area_ha": float(after.area_ha),
                "excluded_mangrove_area_ha": excluded,
                "excluded_mangrove_area_percent": 100.0 * excluded / float(before.area_ha),
                "excluded_mangrove_pixel_count": int(after.excluded_mangrove_pixel_count),
                "non_mangrove_spatial_sd_tc_ha_yr": float(after.rate_tc_ha_yr_spatial_sd),
            }
        )
    result = pd.DataFrame(rows)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    result.to_csv(VALIDATION / "gfw_non_mangrove_rate_comparison.csv", index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
