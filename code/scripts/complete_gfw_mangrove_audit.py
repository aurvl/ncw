"""Complete audit rows for tile/biome cells consisting entirely of mangroves.

The first remote aggregation omitted these zero-weight cells from its tile
table. The clean biome rates are unaffected. This repair uses the verified
all-forest tile table to restore their excluded area and pixel counts, then
recomputes only the exclusion audit columns in the clean biome table. The
original remote outputs remain in gfw_non_mangrove_results.tar.gz.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
GIBBS_OUTPUT = ROOT / "data" / "outputs" / "gibbs_gfw"


def main() -> None:
    old_path = GIBBS_OUTPUT / "gfw_gibbs_tile_rates_with_mangroves.csv"
    if not old_path.is_file():
        old_path = GIBBS_OUTPUT / "gfw_gibbs_tile_rates.csv"
    old = pd.read_csv(old_path)
    clean_path = GIBBS_OUTPUT / "gfw_gibbs_tile_rates_non_mangrove.csv"
    clean = pd.read_csv(clean_path)
    keys = ["source_tile", "biome"]
    baseline = old.set_index(keys)
    filtered = clean.set_index(keys)
    if not filtered.index.is_unique or not baseline.index.is_unique:
        raise ValueError("Tile/biome keys must be unique")
    missing = baseline.loc[baseline.index.difference(filtered.index)]
    additions = []
    for (tile, biome), row in missing.iterrows():
        additions.append(
            {
                "source_tile": tile,
                "biome": biome,
                "rate_tc_ha_yr_mean": 0.0,
                "rate_tc_ha_yr_spatial_sd": 0.0,
                "area_ha": 0.0,
                "pixel_count": 0,
                "negative_source_pixel_count": 0,
                "excluded_mangrove_pixel_count": int(row.pixel_count),
                "excluded_mangrove_area_ha": float(row.area_ha),
            }
        )
    if additions:
        clean = pd.concat([clean, pd.DataFrame(additions)], ignore_index=True)
    check = old.merge(clean, on=keys, suffixes=("_old", "_clean"), validate="one_to_one")
    if len(check) != len(old):
        raise AssertionError("Every original tile/biome cell must have a clean audit row")
    if not np.allclose(
        check.area_ha_old,
        check.area_ha_clean + check.excluded_mangrove_area_ha,
        rtol=1e-9,
        atol=1e-4,
    ):
        raise AssertionError("Tile area does not reconcile with excluded mangrove area")
    if not (
        check.pixel_count_old
        == check.pixel_count_clean + check.excluded_mangrove_pixel_count
    ).all():
        raise AssertionError("Tile pixel counts do not reconcile")
    clean = clean.sort_values(keys).reset_index(drop=True)
    clean.to_csv(clean_path, index=False)

    rates_path = GIBBS_OUTPUT / "gfw_gibbs_biome_rates_non_mangrove.csv"
    rates = pd.read_csv(rates_path)
    excluded = clean.groupby("biome")[
        ["excluded_mangrove_pixel_count", "excluded_mangrove_area_ha"]
    ].sum()
    for index, row in rates.iterrows():
        biome = row.biome
        rates.loc[index, "excluded_mangrove_pixel_count"] = int(
            excluded.loc[biome, "excluded_mangrove_pixel_count"]
        )
        rates.loc[index, "excluded_mangrove_area_ha"] = float(
            excluded.loc[biome, "excluded_mangrove_area_ha"]
        )
    rates.to_csv(rates_path, index=False)
    print(f"Completed {len(additions)} entirely mangrove tile/biome audit rows")
    print(rates[["biome", "excluded_mangrove_pixel_count", "excluded_mangrove_area_ha"]].to_string(index=False))


if __name__ == "__main__":
    main()
