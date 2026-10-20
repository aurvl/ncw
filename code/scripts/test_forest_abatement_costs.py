"""No-trade Rickels cost scenario for reported forest-capacity losses.

This is a hypothetical compensation exercise. The historical forest-capacity
loss is carried forward to 2030 by assumption; it is not a forecast and is not
part of the NDC accounting used by Rickels et al. The source workbook is read
from the authors' public repository in memory and is not redistributed here.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LOSS_FILE = ROOT / "results/tables/manuscript/Supplementary_country_level_erosion.csv"
OUT = ROOT / "results/validation"
SOURCE_COMMIT = "61e17605919e19c1da83e282cafc8940d6edf3b8"
SOURCE_URL = (
    "https://raw.githubusercontent.com/wilmwilmsen/OceanValue/"
    f"{SOURCE_COMMIT}/Supplementary_Data_M4.xlsx"
)
SCENARIOS = {"DART": 28, "SSP1": 45, "SSP2": 62, "SSP3": 79, "SSP4": 96, "SSP5": 113}
FRACTIONS = (0.0, 0.25, 0.5, 1.0)


def abatement_cost_billion(
    alpha: float, gdp_billion: float, bau_mtco2: float, cap_mtco2: float
) -> float:
    """Reproduce Rickels supplementary M4's no-trade cost formula (Eq. 8)."""
    effective_cap = min(bau_mtco2, cap_mtco2)
    reduction_share = 1.0 - effective_cap / bau_mtco2
    return alpha * reduction_share**3 * gdp_billion * bau_mtco2 / 1000.0


def load_source(path: Path | None) -> pd.DataFrame:
    if path is None:
        with urlopen(SOURCE_URL, timeout=60) as response:
            data = response.read()
        return pd.read_excel(BytesIO(data), sheet_name="Model_with_ocean", header=None)
    return pd.read_excel(path, sheet_name="Model_with_ocean", header=None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, help="Optional local copy of Rickels M4")
    args = parser.parse_args()
    source = load_source(args.workbook)
    source = source.loc[
        source[0].astype(str).str.fullmatch(r"[A-Z]{3}") | source[0].eq("EU")
    ].copy()
    assert len(source) == 146, "Unexpected region count in pinned Rickels M4 workbook"

    losses = pd.read_csv(LOSS_FILE)
    losses = losses.loc[losses["reported_deforestation"].eq(True), ["iso3", "loss_tco2_mean"]]
    loss_by_iso = losses.set_index("iso3")["loss_tco2_mean"] / 1e6
    records = []
    checks = []
    for _, country in source.iterrows():
        iso3 = str(country[0])
        alpha = float(country[6])
        for scenario, start in SCENARIOS.items():
            gdp = float(country[start])
            bau = float(country[start + 1])
            for ambition, target_col, cached_cost_col in (
                ("low", start + 2, start + 4),
                ("high", start + 3, start + 6),
            ):
                target = float(country[target_col])
                cached = float(country[cached_cost_col])
                baseline = abatement_cost_billion(alpha, gdp, bau, target)
                checks.append(abs(baseline - cached))
                loss_mt = loss_by_iso.get(iso3, np.nan)
                for fraction in FRACTIONS:
                    available = np.isfinite(loss_mt)
                    new_cap = target - fraction * loss_mt if available else np.nan
                    feasible = bool(available and new_cap >= 0)
                    new_cost = (
                        abatement_cost_billion(alpha, gdp, bau, new_cap)
                        if feasible
                        else np.nan
                    )
                    records.append(
                        {
                            "iso3": iso3,
                            "macro_scenario": scenario,
                            "ndc_ambition": ambition,
                            "replacement_fraction": fraction,
                            "historical_lost_capacity_MtCO2_yr": loss_mt,
                            "has_reported_forest_loss": available,
                            "scenario_feasible": feasible,
                            "alpha": alpha,
                            "gdp_2030_billion_source_usd": gdp,
                            "bau_2030_MtCO2": bau,
                            "ndc_2030_MtCO2": target,
                            "hypothetical_cap_2030_MtCO2": new_cap,
                            "baseline_cost_billion_source_usd": baseline,
                            "hypothetical_cost_billion_source_usd": new_cost,
                            "incremental_cost_billion_source_usd": new_cost - baseline,
                        }
                    )

    max_error = max(checks)
    assert max_error < 1e-8, f"Rickels M4 baseline mismatch: {max_error}"
    result = pd.DataFrame(records)
    OUT.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT / "forest_abatement_no_trade_country_scenarios.csv", index=False)
    matched = result.loc[result["scenario_feasible"]]
    summary = matched.groupby(
        ["macro_scenario", "ndc_ambition", "replacement_fraction"], as_index=False
    ).agg(
        matched_reporting_countries=("iso3", "nunique"),
        matched_loss_MtCO2_yr=("historical_lost_capacity_MtCO2_yr", "sum"),
        matched_baseline_cost_billion_source_usd=("baseline_cost_billion_source_usd", "sum"),
        incremental_cost_billion_source_usd=("incremental_cost_billion_source_usd", "sum"),
    )
    summary.to_csv(OUT / "forest_abatement_no_trade_summary.csv", index=False)
    print(f"Rickels workbook countries: {source[0].nunique()}")
    print(f"Forest-loss reporting countries: {loss_by_iso.notna().sum()}")
    print(f"Country overlap: {len(set(source[0]) & set(loss_by_iso.dropna().index))}")
    print(f"Maximum baseline replication error, billion source USD: {max_error:.3g}")
    global_baseline = (
        result.loc[result["replacement_fraction"].eq(0.0)]
        .groupby(["macro_scenario", "ndc_ambition"])["baseline_cost_billion_source_usd"]
        .sum()
    )
    print(
        "Complete-region high-ambition baseline averaged across six scenarios: "
        f"{global_baseline.xs('high', level='ndc_ambition').mean():.6f} billion source USD"
    )
    print(
        summary.loc[
            summary["replacement_fraction"].eq(1.0) & summary["ndc_ambition"].eq("high")
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
