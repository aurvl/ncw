"""Small validation, IO and draw-summary helpers shared by all modules."""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .config import FRA_VARIABLE, FRA_ZIP


def require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def assert_unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    duplicates = frame.loc[frame.duplicated(keys, keep=False), keys]
    if not duplicates.empty:
        examples = duplicates.drop_duplicates().head(10).to_dict(orient="records")
        raise ValueError(f"{label} has duplicate keys {keys}: {examples}")


def write_table(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    print(f"  wrote {path.relative_to(path.parents[2])} ({len(frame)} rows)")
    return path


def read_fra_variable(name: str) -> pd.DataFrame:
    """Read one FRA 2025 variable file (values in 1000 ha) from the untouched bulk zip."""
    with zipfile.ZipFile(FRA_ZIP) as archive:
        return pd.read_csv(archive.open(FRA_VARIABLE.format(name=name)))


def summarise_draws(draws: np.ndarray, prefix: str) -> pd.DataFrame:
    """Mean, standard deviation and percentiles over axis 1 of an (N, B) draw matrix.

    The standard deviation describes the spread of the value; it is not the Monte Carlo
    standard error of the mean (sd / sqrt(B)).
    """
    draws = np.asarray(draws, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        stats = {
            f"{prefix}_mean": np.nanmean(draws, axis=1),
            f"{prefix}_sd": np.nanstd(draws, axis=1, ddof=1),
            f"{prefix}_p05": np.nanpercentile(draws, 5, axis=1),
            f"{prefix}_p50": np.nanpercentile(draws, 50, axis=1),
            f"{prefix}_p95": np.nanpercentile(draws, 95, axis=1),
        }
    return pd.DataFrame(stats)


def sum_draws(draws: np.ndarray, groups: pd.Series) -> tuple[list, np.ndarray]:
    """Sum an (N, B) matrix draw by draw within each group, preserving correlations."""
    labels = list(pd.unique(groups.dropna()))
    summed = np.vstack([np.nansum(draws[(groups == label).to_numpy()], axis=0) for label in labels])
    return labels, summed
