"""Q: Which social cost of carbon values the flows, and with which uncertainty?

The GSCC draws are read from the BCW release so that GCW and BCW share identical draws (C8).
Output: data_source/summary/gscc_summary.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BCW_DRAWS_NPZ, SUMMARY
from .validation import summarise_draws, write_table


def load_gscc_draws() -> np.ndarray:
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        return archive["gscc_draws"].astype(np.float64)


def run() -> np.ndarray:
    draws = load_gscc_draws()
    summary = summarise_draws(draws[None, :], "gscc_usd2015_per_tco2")
    summary.insert(0, "n_draws", draws.size)
    summary.insert(0, "source", "BCW release draws.npz (gscc_draws), structure-adjusted GSCC")
    write_table(summary, SUMMARY / "gscc_summary.csv")
    return draws
