"""Build historical Figure 4 tables from the earlier published-curve comparison.

This script predates the current all-country cell reconstruction and is not part
of the current Busch calculation pipeline. Its published-curve comparison must
not be reported as a result of the current analysis.

The 2% allocation is a stipulated scenario. Busch's curves describe modeled
reforestation mitigation opportunities; the matching exercise does not price
replacement of the forest service measured in this study.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data" / "derived" / "validation"
TABLES = ROOT / "results" / "tables" / "manuscript"
CURVES = ROOT / "data" / "raw" / "economic" / "busch_2024" / "11_MAC_curves_consolidated.xlsx"
CURVE_PREFIX = "MAC_mi_whrv_sGr_bu_ad_"
ANNUITY_30Y_5PCT = sum(1 / 1.05**year for year in range(1, 31))
CPI_2020_TO_2015 = 237.017 / 258.811
GROUP_ORDER = ["Developed economies", "Developing economies", "LDCs", "SIDS", "Unclassified"]
STATUS_ORDER = [
    "target_within_supply_at_or_below_minus20",
    "target_within_supply_at_nonpositive_price",
    "target_within_positive_price_curve",
    "target_exceeds_published_supply_at_100",
    "no_country_curve_in_published_table",
]


def with_unit_identifiers(frame: pd.DataFrame) -> pd.DataFrame:
    """Add explicit accounting and ISO identifiers to a unit-level figure table."""
    identifiers = pd.read_csv(ROOT / "data" / "derived" / "territories.csv")[[
        "iso3", "UNIT_CODE", "ISO3", "region"
    ]]
    result = frame.merge(identifiers, on="iso3", how="left", validate="many_to_one")
    if result["UNIT_CODE"].isna().any():
        raise ValueError("Figure 4 contains units absent from the territory crosswalk")
    front = [column for column in ["UNIT_CODE", "ISO3", "name", "region"] if column in result]
    return result[[*front, *(column for column in result if column not in front)]]


def inverse_price(target: float, quantities: np.ndarray, prices: np.ndarray) -> tuple[float, float, float]:
    """Linearly interpolate a target within a monotone published MAC grid."""
    if not (quantities[0] < target <= quantities[-1]):
        raise ValueError("Target must lie strictly above the first grid quantity and within the last")
    if np.any(np.diff(quantities) < 0):
        raise ValueError("Cumulative modeled supply must be nondecreasing")
    right = int(np.flatnonzero(quantities >= target)[0])
    left = right - 1
    if quantities[right] == quantities[left]:
        raise ValueError("Cannot interpolate over a flat quantity interval")
    fraction = (target - quantities[left]) / (quantities[right] - quantities[left])
    estimate = prices[left] + fraction * (prices[right] - prices[left])
    return float(estimate), float(prices[left]), float(prices[right])


def positive_price_cost(target: float, quantities: np.ndarray, prices: np.ndarray) -> tuple[float, float, float]:
    """Integrate only the modeled positive-price segment Q(0)..target.

    Returns piecewise-linear integral and lower/upper price-grid rectangles in
    2020 USD present value. This omits the negative-price segment and is not a
    complete implementation budget or a replacement cost.
    """
    zero = int(np.flatnonzero(prices == 0)[0])
    if not (quantities[zero] < target <= quantities[-1]):
        raise ValueError("Positive-price integral needs a target above Q(0) within the grid")
    total = lower = upper = 0.0
    start_quantity = float(quantities[zero])
    for right in range(zero + 1, len(prices)):
        end_quantity = min(float(quantities[right]), target)
        if end_quantity > start_quantity:
            p_left = float(prices[right - 1])
            p_right = float(prices[right])
            q_left = float(quantities[right - 1])
            q_right = float(quantities[right])
            p_start = p_left + (start_quantity - q_left) * (p_right - p_left) / (q_right - q_left)
            p_end = p_left + (end_quantity - q_left) * (p_right - p_left) / (q_right - q_left)
            width = end_quantity - start_quantity
            total += width * (p_start + p_end) / 2
            lower += width * p_left
            upper += width * p_right
            start_quantity = end_quantity
        if start_quantity >= target:
            break
    if not np.isclose(start_quantity, target, rtol=1e-12):
        raise ValueError("Positive-price integral did not reach the target")
    return total, lower, upper


def build() -> dict:
    allocation = pd.read_csv(VALIDATION / "our_2pct_gcw_allocation_and_pledge.csv")
    if len(allocation) != 236 or allocation.iso3.duplicated().any():
        raise ValueError("Expected 236 unique national allocation units")
    amount = "our_2pct_gcw_allocation_usd2015_yr"
    if allocation[amount].isna().any() or (allocation[amount] < 0).any():
        raise ValueError("National allocations must be nonmissing and nonnegative")
    allocation = allocation.sort_values([amount, "iso3"], ascending=[False, True]).reset_index(drop=True)
    total = float(allocation[amount].sum())
    allocation["allocation_rank"] = np.arange(1, len(allocation) + 1)
    allocation["cumulative_allocation_usd2015_yr"] = allocation[amount].cumsum()
    allocation["cumulative_share_pct"] = 100 * allocation["cumulative_allocation_usd2015_yr"] / total
    allocation["cumulative_country_share_pct"] = 100 * allocation["allocation_rank"] / len(allocation)
    allocation["group_display"] = allocation.groups.fillna("Unclassified")
    national = allocation[[
        "allocation_rank", "iso3", "name", "groups", "group_display",
        "gcw_usd2015_yr_mean", amount, "cumulative_allocation_usd2015_yr",
        "cumulative_share_pct", "cumulative_country_share_pct",
    ]]
    with_unit_identifiers(national).to_csv(
        TABLES / "Supplementary_Figure4_finance_allocations_by_unit.csv", index=False
    )

    group = allocation.groupby("group_display", as_index=False).agg(
        units=("iso3", "size"), total_usd2015_yr=(amount, "sum"),
        median_usd2015_yr=(amount, "median"),
        p25_usd2015_yr=(amount, lambda values: values.quantile(0.25)),
        p75_usd2015_yr=(amount, lambda values: values.quantile(0.75)),
    ).set_index("group_display")
    present_groups = [name for name in GROUP_ORDER if name in group.index]
    group = group.loc[present_groups].reset_index()
    if group.units.sum() != 236 or not np.isclose(group.total_usd2015_yr.sum(), total):
        raise ValueError("Economic groups do not reconcile to the national total")
    group.to_csv(TABLES / "Supplementary_Figure4_finance_allocations_by_group.csv", index=False)

    gcw = pd.read_csv(TABLES / "Table1_global_carbon_wealth.csv")
    gcw = gcw.loc[gcw.component.eq("Green carbon wealth")].iloc[0]
    uncertainty = {
        "allocation_rule_fraction": 0.02,
        "mean_billion_usd2015_yr": float(gcw.value_mean_trillion_usd2015_yr * 20),
        "p05_billion_usd2015_yr": float(gcw.value_p05_trillion_usd2015_yr * 20),
        "p95_billion_usd2015_yr": float(gcw.value_p95_trillion_usd2015_yr * 20),
        "uncertainty_scope": "GCW monetary draws conditional on fixed forest inputs; not full uncertainty in rates, areas or the 2% rule",
    }
    if not np.isclose(uncertainty["mean_billion_usd2015_yr"] * 1e9, total):
        raise ValueError("Global uncertainty table and national allocations differ")

    action = pd.read_csv(VALIDATION / "busch_action_curve_country_scenarios.csv")
    if len(action) != 105 or action.iso3.duplicated().any():
        raise ValueError("Expected 105 unique positive-loss units")
    raw = pd.read_excel(CURVES, sheet_name="Core results")
    prices = raw.price.to_numpy(dtype=float)
    if not np.array_equal(prices, np.arange(-20, 105, 5)):
        raise ValueError("Unexpected Busch price grid")
    rows = []
    for row in action.itertuples(index=False):
        output = {
            "iso3": row.iso3, "name": row.name, "status": row.status,
            "reported_loss_capacity_tco2_yr": row.reported_loss_capacity_tco2_yr,
            "target_discounted_30yr_tco2": row.target_discounted_30yr_tco2,
            "marginal_price_interpolated_usd2020_tco2": np.nan,
            "marginal_price_grid_lower_usd2020_tco2": np.nan,
            "marginal_price_grid_upper_usd2020_tco2": np.nan,
            "positive_price_integral_pv_usd2020_partial": np.nan,
            "positive_price_integral_grid_lower_pv_usd2020_partial": np.nan,
            "positive_price_integral_grid_upper_pv_usd2020_partial": np.nan,
            "positive_price_integral_annual_usd2015_partial": np.nan,
        }
        column = CURVE_PREFIX + row.iso3
        if column in raw:
            quantities = raw[column].to_numpy(dtype=float)
            if np.any(np.diff(quantities) < 0):
                raise ValueError(f"Nonmonotone Busch curve for {row.iso3}")
            if row.status in ("target_within_supply_at_nonpositive_price", "target_within_positive_price_curve"):
                price, lo, hi = inverse_price(row.target_discounted_30yr_tco2, quantities, prices)
                output["marginal_price_interpolated_usd2020_tco2"] = price
                output["marginal_price_grid_lower_usd2020_tco2"] = lo
                output["marginal_price_grid_upper_usd2020_tco2"] = hi
                if row.status == "target_within_positive_price_curve":
                    integral, bound_lo, bound_hi = positive_price_cost(
                        row.target_discounted_30yr_tco2, quantities, prices
                    )
                    output["positive_price_integral_pv_usd2020_partial"] = integral
                    output["positive_price_integral_grid_lower_pv_usd2020_partial"] = bound_lo
                    output["positive_price_integral_grid_upper_pv_usd2020_partial"] = bound_hi
                    output["positive_price_integral_annual_usd2015_partial"] = (
                        integral / ANNUITY_30Y_5PCT * CPI_2020_TO_2015
                    )
        rows.append(output)
    marginal = pd.DataFrame(rows)
    with_unit_identifiers(marginal).to_csv(
        TABLES / "Supplementary_Figure4_Busch_marginal_prices_by_unit.csv", index=False
    )
    counts = marginal.status.value_counts().reindex(STATUS_ORDER).fillna(0).astype(int)
    if counts.sum() != 105 or counts.iloc[:3].sum() != 46:
        raise ValueError("Busch availability and price-domain counts changed")
    covered = marginal.status.isin(STATUS_ORDER[:3])
    coverage_share = float(100 * marginal.loc[covered, "reported_loss_capacity_tco2_yr"].sum()
                           / marginal.reported_loss_capacity_tco2_yr.sum())
    positive = marginal.loc[marginal.status.eq("target_within_positive_price_curve")]
    if not (
        (positive.positive_price_integral_grid_lower_pv_usd2020_partial
         <= positive.positive_price_integral_pv_usd2020_partial).all()
        and (positive.positive_price_integral_pv_usd2020_partial
             <= positive.positive_price_integral_grid_upper_pv_usd2020_partial).all()
    ):
        raise ValueError("Interpolated cost is outside its price-grid bounds")
    interpolated = marginal.marginal_price_interpolated_usd2020_tco2.dropna()
    summary = {
        "national_units": 236,
        "allocation_total_billion_usd2015_yr": total / 1e9,
        "top10_allocation_share_pct": float(allocation.loc[:9, amount].sum() / total * 100),
        "top50_allocation_share_pct": float(allocation.loc[:49, amount].sum() / total * 100),
        "allocation_uncertainty": uncertainty,
        "busch_positive_loss_units": 105,
        "busch_status_counts": counts.to_dict(),
        "busch_supply_sufficient_by_100_units": int(covered.sum()),
        "busch_supply_sufficient_by_100_loss_share_pct": coverage_share,
        "busch_interpolated_marginal_price_units": int(len(interpolated)),
        "busch_interpolated_marginal_price_min_usd2020_tco2": float(interpolated.min()),
        "busch_interpolated_marginal_price_median_usd2020_tco2": float(interpolated.median()),
        "busch_interpolated_marginal_price_max_usd2020_tco2": float(interpolated.max()),
        "busch_positive_price_units": int(len(positive)),
        "busch_positive_price_partial_integral_pv_usd2020": float(positive.positive_price_integral_pv_usd2020_partial.sum()),
        "busch_positive_price_partial_integral_annual_usd2015": float(positive.positive_price_integral_annual_usd2015_partial.sum()),
        "partial_integral_scope": "Only Q(0) to the target for 12 positive-price units; excludes other costs, negative-price supply and all units without an estimable positive-price target",
    }
    (VALIDATION / "finance_figure4_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
