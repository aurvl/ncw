"""Compare Ibrahim's fixed-share finance proxy with published forest-action costs.

This is a scenario comparison, not an estimate of a national climate-finance
entitlement or of the cost of replacing the forest ecosystem service.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "economic" / "busch_2024" / "11_MAC_curves_consolidated.xlsx"
LOSS = ROOT / "results" / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv"
GCW = ROOT / "results" / "country_level_gcw.csv"
OUT = ROOT / "results" / "validation"
PRICE_PREFIX = "MAC_mi_whrv_sGr_bu_ad_"
DISCOUNT_RATE = 0.05
HORIZON = 30
IBRAHIM_SHARE = 0.02
PLEDGE_USD_PER_YEAR = 100e9
CPI_2015 = 237.017
CPI_2020 = 258.811


def annuity_factor(rate: float = DISCOUNT_RATE, horizon: int = HORIZON) -> float:
    """Present-value factor for one equal annual flow in years 1..horizon."""
    return float(sum((1 + rate) ** (-year) for year in range(1, horizon + 1)))


def action_curve_status(target_pv_tco2: float, prices: np.ndarray, supply: np.ndarray) -> dict:
    """Bracket a target on a published cumulative MAC curve, without extrapolation."""
    if np.any(np.diff(supply) < -1e-6):
        raise ValueError("Published action-cost curve is not monotone nondecreasing")
    q_min = float(np.interp(-20, prices, supply))
    q_zero = float(np.interp(0, prices, supply))
    q_max = float(np.interp(100, prices, supply))
    result = {
        "source_quantity_at_minus20_tco2_pv": q_min,
        "source_quantity_at_zero_tco2_pv": q_zero,
        "source_quantity_at_100_tco2_pv": q_max,
        "marginal_price_lower_usd2020_tco2": np.nan,
        "marginal_price_upper_usd2020_tco2": np.nan,
        "status": "",
    }
    if target_pv_tco2 > q_max:
        result["status"] = "target_exceeds_published_supply_at_100"
    elif target_pv_tco2 <= q_min:
        result["status"] = "target_within_supply_at_or_below_minus20"
        result["marginal_price_lower_usd2020_tco2"] = -20.0
        result["marginal_price_upper_usd2020_tco2"] = -20.0
    elif target_pv_tco2 <= q_zero:
        result["status"] = "target_within_supply_at_nonpositive_price"
        result["marginal_price_lower_usd2020_tco2"] = np.nan
        result["marginal_price_upper_usd2020_tco2"] = 0.0
    else:
        first = int(np.flatnonzero(supply >= target_pv_tco2)[0])
        result["status"] = "target_within_positive_price_curve"
        result["marginal_price_lower_usd2020_tco2"] = float(prices[max(0, first - 1)])
        result["marginal_price_upper_usd2020_tco2"] = float(prices[first])
    return result


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    curves = pd.read_excel(RAW, sheet_name="Core results")
    prices = curves["price"].to_numpy(dtype=float)
    assert len(prices) == 25 and np.array_equal(prices, np.arange(-20, 105, 5))
    annuity = annuity_factor()
    cpi_factor = CPI_2015 / CPI_2020

    # Ibrahim's proportional allocation applies to every unit with an estimated
    # GCW, independently of whether FRA reported deforestation for that unit.
    # Keep the loss table's missing reports as missing; use only reported,
    # positive-loss rows when matching targets to Busch action curves below.
    loss = pd.read_csv(LOSS)[["iso3", "loss_tco2_mean", "reported_deforestation"]].copy()
    gcw = pd.read_csv(GCW)
    merged = gcw[["iso3", "name", "continent", "groups", "gcw_usd2015_yr_mean", "gcw_share_of_gdp"]].merge(
        loss,
        on="iso3",
        how="left",
        validate="one_to_one",
    )
    total_gcw = float(gcw["gcw_usd2015_yr_mean"].sum(skipna=True))
    merged["ibrahim_2pct_usd2015_yr"] = IBRAHIM_SHARE * merged["gcw_usd2015_yr_mean"]
    merged["gcw_share_global_pct"] = 100 * merged["gcw_usd2015_yr_mean"] / total_gcw
    merged["share_of_30yr_100bn_pledge_usd_cumulative"] = (
        merged["gcw_usd2015_yr_mean"] / total_gcw * PLEDGE_USD_PER_YEAR * HORIZON
    )
    merged["lost_capacity_tco2_yr"] = merged["loss_tco2_mean"]
    merged["lost_capacity_discounted_30yr_tco2"] = merged["loss_tco2_mean"] * annuity

    rows = []
    positive_reported_loss = merged.loc[
        merged["reported_deforestation"].eq(True) & merged["loss_tco2_mean"].gt(0)
    ]
    for row in positive_reported_loss.itertuples(index=False):
        column = PRICE_PREFIX + str(row.iso3)
        if column not in curves.columns:
            calc = {
                "source_quantity_at_minus20_tco2_pv": np.nan,
                "source_quantity_at_zero_tco2_pv": np.nan,
                "source_quantity_at_100_tco2_pv": np.nan,
                "marginal_price_lower_usd2020_tco2": np.nan,
                "marginal_price_upper_usd2020_tco2": np.nan,
                "status": "no_country_curve_in_published_table",
            }
        else:
            supply = curves[column].to_numpy(dtype=float)
            calc = action_curve_status(row.loss_tco2_mean * annuity, prices, supply)
        low = calc["marginal_price_lower_usd2020_tco2"]
        high = calc["marginal_price_upper_usd2020_tco2"]
        # This is a gross uniform-price transfer proxy only for positive-price
        # curves. It is not the integrated resource cost or project budget.
        if calc["status"] == "target_within_positive_price_curve":
            pay_lo = row.loss_tco2_mean * low
            pay_hi = row.loss_tco2_mean * high
        else:
            pay_lo = pay_hi = np.nan
        rows.append({
            "iso3": row.iso3,
            "name": row.name,
            "groups": row.groups,
            "reported_loss_capacity_tco2_yr": row.loss_tco2_mean,
            "target_discounted_30yr_tco2": row.loss_tco2_mean * annuity,
            "busch_curve_available": column in curves.columns,
            **calc,
            "annualized_uniform_price_payment_lower_usd2020_yr_partial": pay_lo,
            "annualized_uniform_price_payment_upper_usd2020_yr_partial": pay_hi,
            "annualized_uniform_price_payment_lower_usd2015_yr_partial": pay_lo * cpi_factor if np.isfinite(pay_lo) else np.nan,
            "annualized_uniform_price_payment_upper_usd2015_yr_partial": pay_hi * cpi_factor if np.isfinite(pay_hi) else np.nan,
        })
    action = pd.DataFrame(rows)
    action.to_csv(OUT / "busch_action_curve_country_scenarios_2026-10-19.csv", index=False)

    statuses = action.groupby("status", as_index=False).agg(
        countries=("iso3", "nunique"),
        lost_capacity_tco2_yr=("reported_loss_capacity_tco2_yr", "sum"),
        target_discounted_30yr_tco2=("target_discounted_30yr_tco2", "sum"),
    )
    statuses["share_of_all_reported_loss_pct"] = (
        100 * statuses["lost_capacity_tco2_yr"] / action["reported_loss_capacity_tco2_yr"].sum()
    )
    statuses.to_csv(OUT / "busch_action_curve_status_summary_2026-10-19.csv", index=False)

    # The original Ibrahim allocation table is retained in properly labelled
    # annual and cumulative units. No annual-minus-cumulative "gap" is formed.
    merged.to_csv(OUT / "ibrahim_2pct_and_pledge_allocations_2026-10-19.csv", index=False)

    positive = action.loc[action["status"].eq("target_within_positive_price_curve")]
    covered_status = action["status"].isin([
        "target_within_supply_at_or_below_minus20",
        "target_within_supply_at_nonpositive_price",
        "target_within_positive_price_curve",
    ])
    matched = action["busch_curve_available"]
    summary = {
        "gibbs_gmw_gcw_usd2015_yr": total_gcw,
        "ibrahim_fixed_share": IBRAHIM_SHARE,
        "ibrahim_2pct_proxy_usd2015_yr": total_gcw * IBRAHIM_SHARE,
        "ibrahim_100bn_30yr_pledge_usd_cumulative": PLEDGE_USD_PER_YEAR * HORIZON,
        "ibrahim_published_country_unit_mismatch": "annual GCW minus 30-year cumulative allocation has incompatible units; no such gap is calculated",
        "busch_article": "Busch et al. (2024), 30-year marginal abatement curves, 5% annual discounting, 2020 USD/tCO2",
        "busch_cost_curve": "least-cost of natural regeneration vs plantation with harvest, suitability screen, buffer, additionality",
        "discount_factor_years_1_to_30": annuity,
        "positive_loss_reporters": int(action.shape[0]),
        "positive_loss_total_tco2_yr": float(action["reported_loss_capacity_tco2_yr"].sum()),
        "country_curves_available": int(matched.sum()),
        "matched_loss_tco2_yr": float(action.loc[matched, "reported_loss_capacity_tco2_yr"].sum()),
        "matched_loss_share_pct": float(100 * action.loc[matched, "reported_loss_capacity_tco2_yr"].sum() / action["reported_loss_capacity_tco2_yr"].sum()),
        "matched_countries_supply_within_price_domain": int(covered_status.sum()),
        "matched_loss_supply_within_price_domain_tco2_yr": float(action.loc[covered_status, "reported_loss_capacity_tco2_yr"].sum()),
        "all_reported_loss_supply_within_price_domain_share_pct": float(100 * action.loc[covered_status, "reported_loss_capacity_tco2_yr"].sum() / action["reported_loss_capacity_tco2_yr"].sum()),
        "positive_price_curve_countries": int(len(positive)),
        "positive_price_curve_loss_tco2_yr": float(positive["reported_loss_capacity_tco2_yr"].sum()),
        "positive_price_payment_proxy_usd2020_yr_partial_lo": float(positive["annualized_uniform_price_payment_lower_usd2020_yr_partial"].sum()),
        "positive_price_payment_proxy_usd2020_yr_partial_hi": float(positive["annualized_uniform_price_payment_upper_usd2020_yr_partial"].sum()),
        "positive_price_payment_proxy_usd2015_yr_partial_lo": float(positive["annualized_uniform_price_payment_lower_usd2015_yr_partial"].sum()),
        "positive_price_payment_proxy_usd2015_yr_partial_hi": float(positive["annualized_uniform_price_payment_upper_usd2015_yr_partial"].sum()),
        "positive_price_median_bracket_usd2020_tco2": [float(positive["marginal_price_lower_usd2020_tco2"].median()), float(positive["marginal_price_upper_usd2020_tco2"].median())],
        "austin_2025_published_action_cost_range_usd_yr_2030": [20e9, 72e9],
        "austin_to_ibrahim_proxy_ratio_pct": [100 * 20e9 / (total_gcw * IBRAHIM_SHARE), 100 * 72e9 / (total_gcw * IBRAHIM_SHARE)],
        "cpi_conversion_2020_to_2015": cpi_factor,
        "limits": [
            "Busch curves cover suitable/additional restoration locations in low- and middle-income countries, not all forest-loss reporters.",
            "The action curve's carbon pool and temporal profile differ from this paper's gross annual living-biomass additions; equal tonnage is a scenario convention, not physical equivalence.",
            "Country curves extend only from -20 to 100 USD2020/tCO2 in five-dollar increments; targets above this support range are not extrapolated.",
            "A positive-price uniform payment proxy is a gross carbon-price transfer for only 12 countries, not integrated project expenditure or a global financing need.",
            "The 2% share is an assumed allocation rule, not estimated from action costs.",
            "Austin et al.'s 20-72 billion USD/year for 2030 concerns forest-based NDC mitigation in its modelled countries/regions, not replacement of this paper's lost capacity.",
        ],
    }
    (OUT / "finance_action_cost_comparison_2026-10-19.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return action, statuses, summary


if __name__ == "__main__":
    _, _, result = build()
    print(json.dumps(result, indent=2))
