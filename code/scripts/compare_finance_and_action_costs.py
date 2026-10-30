"""Build the 2% GCW allocation and join it to calculated restoration results.

The restoration calculation is performed for every country DTA before this
script joins any FRA-loss targets. No published Busch country curve is read or
used as a selection or validation criterion.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LOSS = ROOT / "results" / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv"
GCW = ROOT / "data" / "derived" / "accounts" / "country_level_gcw.csv"
DERIVED = ROOT / "data" / "derived"
OUT = DERIVED / "validation"
BUSCH_DIR = DERIVED / "busch_reconstruction"
BUSCH_LABEL = "all_dta"
DISCOUNT_RATE = 0.05
HORIZON = 30
SOURCE_DISCOUNT_FACTOR = sum((1 - DISCOUNT_RATE) ** year for year in range(HORIZON))
OUR_ALLOCATION_RATE = 0.02
PLEDGE_USD_PER_YEAR = 100e9


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    OUT.mkdir(parents=True, exist_ok=True)

    # This allocation is needed as a target for the later entity-level join.
    # It is built independently of restoration-data availability.
    loss = pd.read_csv(LOSS)[["iso3", "loss_tco2_mean", "reported_deforestation"]].copy()
    gcw = pd.read_csv(GCW)
    merged = gcw[[
        "iso3", "name", "continent", "groups", "gcw_usd2015_yr_mean", "gcw_share_of_gdp"
    ]].merge(loss, on="iso3", how="left", validate="one_to_one")
    total_gcw = float(gcw["gcw_usd2015_yr_mean"].sum(skipna=True))
    merged["our_2pct_gcw_allocation_usd2015_yr"] = (
        OUR_ALLOCATION_RATE * merged["gcw_usd2015_yr_mean"]
    )
    merged["gcw_share_global_pct"] = 100 * merged["gcw_usd2015_yr_mean"] / total_gcw
    merged["share_of_30yr_100bn_pledge_usd_cumulative"] = (
        merged["gcw_usd2015_yr_mean"] / total_gcw * PLEDGE_USD_PER_YEAR * HORIZON
    )
    merged["lost_capacity_tco2_yr"] = merged["loss_tco2_mean"]
    merged["lost_capacity_discounted_30yr_tco2"] = (
        merged["loss_tco2_mean"] * SOURCE_DISCOUNT_FACTOR
    )
    merged.to_csv(OUT / "our_2pct_gcw_allocation_and_pledge.csv", index=False)

    positive_loss = merged.loc[
        merged["reported_deforestation"].eq(True) & merged["loss_tco2_mean"].gt(0)
    ].copy()
    positive_loss["target_discounted_30yr_tco2"] = (
        positive_loss["loss_tco2_mean"] * SOURCE_DISCOUNT_FACTOR
    )
    positive_loss = positive_loss.rename(columns={
        "loss_tco2_mean": "reported_loss_capacity_tco2_yr",
        "our_2pct_gcw_allocation_usd2015_yr": "our_2pct_gcw_allocation_usd2015_yr",
    })

    coverage_path = BUSCH_DIR / f"busch_{BUSCH_LABEL}_coverage.csv"
    summary_path = BUSCH_DIR / f"busch_{BUSCH_LABEL}_summary.json"
    if coverage_path.is_file() and summary_path.is_file():
        reconstruction_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        complete = (
            reconstruction_summary.get("processed_country_dta_count")
            == reconstruction_summary.get("archive_country_dta_count")
        )
        if complete:
            coverage = pd.read_csv(coverage_path)
            carry = [
                "iso3", "status", "available_discounted_tco2",
                "target_coverage_pct", "marginal_effective_cost_usd2015_per_discounted_tco2",
                "net_economic_cost_pv_usd2015", "positive_project_cost_pv_usd2015",
                "uniform_carbon_payment_pv_usd2015", "net_economic_cost_annual_usd2015",
                "positive_project_cost_annual_usd2015", "uniform_carbon_payment_annual_usd2015",
                "selected_cells_with_fractional_last",
            ]
            carry = [column for column in carry if column in coverage.columns]
            action = positive_loss.merge(
                coverage[carry], on="iso3", how="left", validate="one_to_one"
            )
            action["cell_input_available"] = action["available_discounted_tco2"].notna()
            action["status"] = action["status"].fillna("no_country_input_dta")
            action["allocation_over_positive_project_cost"] = np.divide(
                action["our_2pct_gcw_allocation_usd2015_yr"],
                action["positive_project_cost_annual_usd2015"],
                out=np.full(len(action), np.nan),
                where=action["positive_project_cost_annual_usd2015"].gt(0),
            )
            action["allocation_over_uniform_payment"] = np.divide(
                action["our_2pct_gcw_allocation_usd2015_yr"],
                action["uniform_carbon_payment_annual_usd2015"],
                out=np.full(len(action), np.nan),
                where=action["uniform_carbon_payment_annual_usd2015"].gt(0),
            )
        else:
            action = positive_loss.copy()
            action["cell_input_available"] = np.nan
            action["status"] = "reconstruction_incomplete"
    else:
        action = positive_loss.copy()
        action["cell_input_available"] = np.nan
        action["status"] = "reconstruction_not_run"

    optional_cost_columns = [
        "available_discounted_tco2", "target_coverage_pct",
        "marginal_effective_cost_usd2015_per_discounted_tco2",
        "net_economic_cost_pv_usd2015", "positive_project_cost_pv_usd2015",
        "uniform_carbon_payment_pv_usd2015", "net_economic_cost_annual_usd2015",
        "positive_project_cost_annual_usd2015", "uniform_carbon_payment_annual_usd2015",
    ]
    for column in optional_cost_columns:
        if column not in action:
            action[column] = np.nan

    action.to_csv(OUT / "busch_action_curve_country_scenarios.csv", index=False)
    statuses = action.groupby("status", as_index=False, dropna=False).agg(
        countries=("iso3", "nunique"),
        lost_capacity_tco2_yr=("reported_loss_capacity_tco2_yr", "sum"),
        target_discounted_30yr_tco2=("target_discounted_30yr_tco2", "sum"),
    )
    total_loss = float(action["reported_loss_capacity_tco2_yr"].sum())
    statuses["share_of_positive_loss_pct"] = (
        100 * statuses["lost_capacity_tco2_yr"] / total_loss if total_loss else np.nan
    )
    statuses.to_csv(OUT / "busch_action_curve_status_summary.csv", index=False)

    summary = {
        "gcw_usd2015_yr": total_gcw,
        "our_allocation_rate": OUR_ALLOCATION_RATE,
        "our_2pct_gcw_allocation_usd2015_yr": total_gcw * OUR_ALLOCATION_RATE,
        "positive_loss_entities": int(len(action)),
        "positive_loss_capacity_tco2_yr": total_loss,
        "source_discount_factor_30yr": SOURCE_DISCOUNT_FACTOR,
        "restoration_calculation": "all country DTA inputs, before joining positive FRA-loss targets",
        "published_country_curve_comparison_performed": False,
        "restoration_join_status_counts": action.status.value_counts(dropna=False).to_dict(),
    }
    (OUT / "finance_action_cost_comparison.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return action, statuses, summary


if __name__ == "__main__":
    _, _, result = build()
    print(json.dumps(result, indent=2, ensure_ascii=False))
