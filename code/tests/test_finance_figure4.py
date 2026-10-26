"""Check inverse marginal prices and partial integration against a toy curve."""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_finance_figure4 import inverse_price, positive_price_cost


def test_inverse_price_interpolates_within_the_published_grid():
    quantities = np.array([10.0, 20.0, 40.0])
    prices = np.array([-5.0, 0.0, 5.0])
    estimate, lower, upper = inverse_price(30.0, quantities, prices)
    assert (estimate, lower, upper) == (2.5, 0.0, 5.0)
    with pytest.raises(ValueError):
        inverse_price(45.0, quantities, prices)


def test_positive_price_integral_excludes_supply_below_zero_price():
    # From Q(0)=20 to target=30, price rises linearly from 0 to 2.5.
    quantities = np.array([10.0, 20.0, 40.0])
    prices = np.array([-5.0, 0.0, 5.0])
    integral, lower, upper = positive_price_cost(30.0, quantities, prices)
    assert integral == pytest.approx(12.5)
    assert lower == pytest.approx(0.0)
    assert upper == pytest.approx(50.0)
