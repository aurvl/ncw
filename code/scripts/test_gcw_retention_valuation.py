"""Conditional GSCC valuation sensitivity for forest living-biomass additions.

The fractions below are valuation assumptions, not observed retention fractions
or mappings from years of storage to permanent CO2 removal. The main GCW draws
already include GSCC uncertainty, so multiplying each draw preserves it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DRAW_FILE = ROOT / "data" / "derived" / "draws" / "gcw_draws.npz"
OUT = ROOT / "data" / "derived" / "validation"
FRACTIONS = (0.25, 0.33, 0.50, 0.75, 1.00)


def summarize(draws: np.ndarray) -> dict[str, float]:
    return {
        "mean_billion_usd2015_yr": float(np.mean(draws) / 1e9),
        "p05_billion_usd2015_yr": float(np.percentile(draws, 5) / 1e9),
        "p50_billion_usd2015_yr": float(np.percentile(draws, 50) / 1e9),
        "p95_billion_usd2015_yr": float(np.percentile(draws, 95) / 1e9),
    }


def main() -> None:
    with np.load(DRAW_FILE, allow_pickle=False) as data:
        iso3 = data["iso3"].astype(str)
        gcw = data["gcw_usd2015_yr"].astype(np.float64)
    assert gcw.shape[0] == len(iso3)
    assert np.isfinite(gcw).all()
    assert (gcw >= 0).all()

    world_draws = gcw.sum(axis=0)
    world_rows = []
    country_rows = []
    for fraction in FRACTIONS:
        world_rows.append({"valuation_fraction": fraction, **summarize(world_draws * fraction)})
        for code, draws in zip(iso3, gcw, strict=True):
            country_rows.append({"iso3": code, "valuation_fraction": fraction, **summarize(draws * fraction)})

    # A full fraction reproduces the unmodified published-method GCW draws.
    full = world_rows[-1]
    assert np.isclose(full["mean_billion_usd2015_yr"], world_draws.mean() / 1e9)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(world_rows).to_csv(OUT / "gcw_valuation_fraction_sensitivity_world.csv", index=False)
    pd.DataFrame(country_rows).to_csv(OUT / "gcw_valuation_fraction_sensitivity_by_unit.csv", index=False)
    print(pd.DataFrame(world_rows).to_string(index=False))


if __name__ == "__main__":
    main()
