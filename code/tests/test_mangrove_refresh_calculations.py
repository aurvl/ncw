"""Synthetic check of the global account scopes."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))

from build_manuscript_artifacts import aggregate_global_accounts


def test_global_ncw_is_sum_of_available_global_components() -> None:
    gcw = np.array([[1.0, np.nan], [np.nan, 2.0]])
    bcw = np.array([[10.0, 20.0], [np.nan, 30.0]])

    result = aggregate_global_accounts(gcw, bcw)

    np.testing.assert_allclose(result["Green carbon wealth"], [1.0, 2.0])
    np.testing.assert_allclose(result["Blue carbon wealth"], [10.0, 50.0])
    np.testing.assert_allclose(result["Natural carbon wealth"], [11.0, 52.0])
