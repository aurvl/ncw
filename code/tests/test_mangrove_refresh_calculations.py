"""Synthetic checks for refreshed global account scopes and erosion rates."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))

from build_manuscript_artifacts import aggregate_global_accounts
from rebuild_deforestation_capacity import estimate_capacity_loss


def test_global_ncw_is_sum_of_available_global_components() -> None:
    gcw = np.array([[1.0, np.nan], [np.nan, 2.0]])
    bcw = np.array([[10.0, 20.0], [np.nan, 30.0]])

    result = aggregate_global_accounts(gcw, bcw)

    np.testing.assert_allclose(result["Green carbon wealth"], [1.0, 2.0])
    np.testing.assert_allclose(result["Blue carbon wealth"], [10.0, 50.0])
    np.testing.assert_allclose(result["Natural carbon wealth"], [11.0, 52.0])


def test_capacity_loss_uses_current_biome_mix_and_preserves_missing_vs_zero() -> None:
    shares = pd.DataFrame(
        {
            "tropical": [0.25, 1.0, 0.25],
            "subtropical": [0.75, 0.0, 0.75],
            "temperate": [0.0, 0.0, 0.0],
            "boreal": [0.0, 0.0, 0.0],
        },
        index=["reported", "reported_zero", "unreported"],
    )
    rates = pd.Series(
        {"tropical": 2.0, "subtropical": 4.0, "temperate": 0.0, "boreal": 0.0}
    )
    area_loss = pd.Series(
        {"reported": 100.0, "reported_zero": 0.0, "unreported": np.nan}
    )

    result = estimate_capacity_loss(area_loss, shares, rates)

    assert np.isclose(result["reported"], 100.0 * 3.5 * (44.0 / 12.0))
    assert result["reported_zero"] == 0.0
    assert np.isnan(result["unreported"])


def test_zero_report_with_zero_forest_area_remains_zero() -> None:
    shares = pd.DataFrame(
        {"tropical": [np.nan], "subtropical": [np.nan], "temperate": [np.nan], "boreal": [np.nan]},
        index=["zero_forest"],
    )
    rates = pd.Series({"tropical": 2.0, "subtropical": 4.0, "temperate": 3.0, "boreal": 1.0})
    area_loss = pd.Series({"zero_forest": 0.0})

    assert estimate_capacity_loss(area_loss, shares, rates)["zero_forest"] == 0.0
