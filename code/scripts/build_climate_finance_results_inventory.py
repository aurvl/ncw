"""Historical climate-finance inventory from an earlier published-curve analysis.

This script is retained for provenance only. It predates the current all-country
cell reconstruction and does not describe or generate current Busch results.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VAL = ROOT / "data/derived/validation"
REC = VAL / "busch_reconstruction"
CURRENT_BUSCH_RUN = "mangrove_refresh_20261023"
OUT = VAL / "CLIMATE_FINANCE_COMPLETE_RESULTS_INVENTORY.md"
COUNTRY_OUT = VAL / "CLIMATE_FINANCE_country_inventory_236.csv"
GROUP_OUT = VAL / "CLIMATE_FINANCE_group_inventory.csv"
PRICE_OUT = VAL / "CLIMATE_FINANCE_price_grid_aggregate_71.csv"
SOURCE_FACTOR = sum(0.95**year for year in range(30))
CONVENTIONAL_FACTOR = sum(1 / 1.05**year for year in range(1, 31))


def fmt(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}"


def markdown(rows: list[list[object]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def describe(values: pd.Series) -> dict[str, float]:
    v = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    q = v.quantile([0, .05, .25, .50, .75, .95, 1]) if len(v) else pd.Series(dtype=float)
    return {"n": len(v), "zero": int(v.eq(0).sum()), "negative": int(v.lt(0).sum()),
            "min": q.get(0, np.nan), "p05": q.get(.05, np.nan),
            "p25": q.get(.25, np.nan), "median": q.get(.50, np.nan),
            "p75": q.get(.75, np.nan), "p95": q.get(.95, np.nan),
            "max": q.get(1, np.nan), "sum": v.sum(), "mean": v.mean()}


def gini(values: pd.Series) -> float:
    v = np.sort(pd.to_numeric(values, errors="coerce").dropna().to_numpy(float))
    if len(v) == 0 or v.sum() == 0:
        return np.nan
    return float((2 * np.arange(1, len(v) + 1) - len(v) - 1) @ v / (len(v) * v.sum()))


def verify_reconstruction_inputs(summary: dict) -> None:
    """Refuse to combine the reconstruction with changed source inputs."""
    expected = summary["input_sha256"]
    for relative in (
        "data/raw/economic/busch_2024/11_MAC_curves_consolidated.xlsx",
        "data/raw/economic/busch_2024/stata_code/10_stata_code/1. Model loop all data.do",
        "data/derived/validation/our_2pct_gcw_allocation_and_pledge.csv",
    ):
        matches = [digest for name, digest in expected.items()
                   if name.replace("\\", "/").endswith(relative)]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous recorded hash for {relative}")
        digest = hashlib.sha256()
        with (ROOT / relative).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != matches[0]:
            raise ValueError(f"Busch reconstruction input changed: {relative}")


def main() -> None:
    a = pd.read_csv(VAL / "our_2pct_gcw_allocation_and_pledge.csv")
    gcw = pd.read_csv(ROOT / "data/derived/accounts/country_level_gcw.csv")
    b = pd.read_csv(REC / f"busch_{CURRENT_BUSCH_RUN}_coverage_105.csv")
    curves = pd.read_csv(REC / f"busch_{CURRENT_BUSCH_RUN}_25_price_curves.csv")
    summary = json.loads((REC / f"busch_{CURRENT_BUSCH_RUN}_summary.json").read_text(encoding="utf-8"))
    verify_reconstruction_inputs(summary)
    old = json.loads((VAL / "finance_figure4_summary.json").read_text(encoding="utf-8"))
    table1 = pd.read_csv(ROOT / "results/tables/manuscript/Table1_global_carbon_wealth.csv")
    ids = pd.read_csv(ROOT / "data/derived/territories.csv")
    if not (len(a) == 236 and len(b) == 105 and len(curves) == 71 * 25):
        raise ValueError("Expected 236 allocation, 105 loss, and 71×25 curve rows")
    if a.iso3.duplicated().any() or b.iso3.duplicated().any():
        raise ValueError("Duplicate accounting-unit key")
    if not np.allclose(a.our_2pct_gcw_allocation_usd2015_yr, .02 * a.gcw_usd2015_yr_mean):
        raise ValueError("National 2% rule does not reconcile")

    national = a.merge(gcw[["iso3", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p50",
                             "gcw_usd2015_yr_p95"]], on="iso3", validate="one_to_one")
    national = national.merge(ids[["iso3", "UNIT_CODE", "ISO3", "region", "group_source"]],
                              on="iso3", validate="one_to_one")
    national = national.merge(b.drop(columns=["name", "groups", "lost_capacity_tco2_yr",
                                       "our_2pct_gcw_allocation_usd2015_yr"]), on="iso3",
                              how="left", validate="one_to_one")
    national["allocation_p05_usd2015_yr"] = .02 * national.gcw_usd2015_yr_p05
    national["allocation_p95_usd2015_yr"] = .02 * national.gcw_usd2015_yr_p95
    national["loss_sample_105"] = national.iso3.isin(b.iso3)
    national["published_busch_curve_available"] = national.source_curve_validated.eq(True)
    national["busch_target_within_supply"] = national.status.eq("target_within_cell_supply")
    national["busch_positive_marginal_price"] = (
        national.busch_target_within_supply
        & national.marginal_effective_cost_usd2015_per_discounted_tco2.gt(0)
    )
    national["scenario_target_30yr_tco2_all_positive_loss"] = np.where(
        national.loss_sample_105, national.lost_capacity_tco2_yr * SOURCE_FACTOR, np.nan
    )
    national["source_target_30yr_tco2_if_curve"] = national.target_discounted_30yr_tco2
    national = national.sort_values(["our_2pct_gcw_allocation_usd2015_yr", "iso3"],
                                    ascending=[False, True]).reset_index(drop=True)
    national["allocation_rank"] = np.arange(1, len(national) + 1)
    national["cumulative_allocation_share_pct"] = (
        100 * national.our_2pct_gcw_allocation_usd2015_yr.cumsum()
        / national.our_2pct_gcw_allocation_usd2015_yr.sum()
    )
    national["allocation_over_positive_cost_defined"] = np.where(
        national.positive_project_cost_annual_usd2015.gt(0),
        national.our_2pct_gcw_allocation_usd2015_yr / national.positive_project_cost_annual_usd2015,
        np.nan)
    national["allocation_over_uniform_payment_defined"] = np.where(
        national.uniform_carbon_payment_annual_usd2015.gt(0),
        national.our_2pct_gcw_allocation_usd2015_yr / national.uniform_carbon_payment_annual_usd2015,
        np.nan)
    first = ["UNIT_CODE", "ISO3", "iso3", "name", "region", "continent", "groups",
             "group_source", "allocation_rank", "gcw_usd2015_yr_mean",
             "our_2pct_gcw_allocation_usd2015_yr", "allocation_p05_usd2015_yr",
             "allocation_p95_usd2015_yr", "cumulative_allocation_share_pct",
             "reported_deforestation", "lost_capacity_tco2_yr", "loss_sample_105",
             "scenario_target_30yr_tco2_all_positive_loss", "published_busch_curve_available",
             "busch_target_within_supply", "busch_positive_marginal_price", "status"]
    national[[*first, *(c for c in national if c not in first)]].to_csv(COUNTRY_OUT, index=False)

    g_rows = []
    for group, part in national.groupby("groups", dropna=False):
        sample = part[part.loss_sample_105]
        matched = part[part.busch_target_within_supply]
        stats = describe(part.our_2pct_gcw_allocation_usd2015_yr)
        g_rows.append({"group": group, "units_236": len(part),
                       "allocation_total_usd2015_yr": stats["sum"],
                       "allocation_share_global_pct": 100 * stats["sum"] / national.our_2pct_gcw_allocation_usd2015_yr.sum(),
                       "allocation_zero_units": stats["zero"],
                       "allocation_mean_usd2015_yr": stats["mean"],
                       "allocation_p05_usd2015_yr": stats["p05"],
                       "allocation_p25_usd2015_yr": stats["p25"],
                       "allocation_median_usd2015_yr": stats["median"],
                       "allocation_p75_usd2015_yr": stats["p75"],
                       "allocation_p95_usd2015_yr": stats["p95"],
                       "allocation_min_usd2015_yr": stats["min"],
                       "allocation_max_usd2015_yr": stats["max"],
                       "allocation_gini_within_group": gini(part.our_2pct_gcw_allocation_usd2015_yr),
                       "positive_loss_units_105": len(sample),
                       "loss_tco2_yr": sample.lost_capacity_tco2_yr.sum(),
                       "available_curve_units": int(sample.published_busch_curve_available.sum()),
                       "no_curve_units": int(sample.status.eq("no_published_country_curve").sum()),
                       "insufficient_supply_units": int(sample.status.eq("target_outside_cell_supply").sum()),
                       "within_supply_units": len(matched),
                       "within_supply_share_of_group_loss_pct": (
                           100 * matched.lost_capacity_tco2_yr.sum() / sample.lost_capacity_tco2_yr.sum()
                           if sample.lost_capacity_tco2_yr.sum() else np.nan),
                       "positive_price_units": int(matched.busch_positive_marginal_price.sum()),
                       "matched_allocation_usd2015_yr": matched.our_2pct_gcw_allocation_usd2015_yr.sum(),
                       "matched_positive_cost_usd2015_yr": matched.positive_project_cost_annual_usd2015.sum(),
                       "matched_uniform_payment_usd2015_yr": matched.uniform_carbon_payment_annual_usd2015.sum()})
    groups = pd.DataFrame(g_rows).sort_values("allocation_total_usd2015_yr", ascending=False)
    groups.to_csv(GROUP_OUT, index=False)

    price = curves.groupby("price_usd2020_per_tco2", as_index=False).agg(
        published_numeric_sum=("published_workbook_numeric_labelled_tco2", "sum"),
        reconstructed_source_tC_sum=("reconstructed_source_tC", "sum"),
        verified_conversion_tco2_sum=("verified_conversion_tco2", "sum"),
        conversion_and_soil_once_tco2_sum=("conversion_and_soil_once_tco2", "sum"),
        countries_nonzero_corrected=("conversion_and_soil_once_tco2", lambda s: int(s.gt(0).sum())),
    )
    price["soil_correction_delta_tco2"] = (price.conversion_and_soil_once_tco2_sum
                                            - price.verified_conversion_tco2_sum)
    price["soil_correction_delta_pct"] = np.where(
        price.verified_conversion_tco2_sum.gt(0),
        100 * price.soil_correction_delta_tco2 / price.verified_conversion_tco2_sum,
        np.nan)
    published_global = pd.read_excel(
        ROOT / "data/raw/economic/busch_2024/11_MAC_curves_consolidated.xlsx",
        sheet_name="Core results",
        usecols=["price", "MAC_mi_whrv_sGr_bu_ad_total"],
    ).rename(columns={"price": "price_usd2020_per_tco2",
                      "MAC_mi_whrv_sGr_bu_ad_total": "published_global_workbook_numeric"})
    price = price.merge(published_global, on="price_usd2020_per_tco2",
                        validate="one_to_one")
    if len(price) != 25:
        raise ValueError("Published and matched-country price grids do not reconcile")
    price.to_csv(PRICE_OUT, index=False)

    a_total = float(national.our_2pct_gcw_allocation_usd2015_yr.sum())
    gcw_row = table1.loc[table1.component.eq("Green carbon wealth")].iloc[0]
    matched = national[national.busch_target_within_supply]
    positive = matched[matched.busch_positive_marginal_price]
    zero_price = matched[~matched.busch_positive_marginal_price]
    missing = national[national.status.eq("no_published_country_curve")]
    insufficient = national[national.status.eq("target_outside_cell_supply")]
    sample = national[national.loss_sample_105]
    source_curves = national[national.published_busch_curve_available]
    n_matched = len(matched)
    n_positive_price = len(positive)
    n_nonpositive_price = len(zero_price)
    n_insufficient = len(insufficient)
    n_missing = len(missing)
    n_source_curves = len(source_curves)
    n_core_curves = int(source_curves.published_sheet.eq("Core results").sum())
    n_other_curves = int(source_curves.published_sheet.eq("Other results").sum())
    n_zero_supply = int(insufficient.available_discounted_tco2.fillna(0).eq(0).sum())
    n_positive_insufficient = n_insufficient - n_zero_supply
    matched_loss_share_pct = 100 * matched.lost_capacity_tco2_yr.sum() / sample.lost_capacity_tco2_yr.sum()
    if not (len(matched) == summary["finance_target_within_supply"]
            and len(missing) + len(insufficient) + len(matched) == len(sample)
            and len(source_curves) == summary["covered_positive_loss_units"]):
        raise ValueError("Latest Busch reconstruction counts did not reconcile")
    if not np.isclose(a_total, gcw_row.value_mean_trillion_usd2015_yr * .02 * 1e12):
        raise ValueError("Global GCW allocation does not reconcile")
    fraction_sensitivity = pd.read_csv(VAL / "gcw_valuation_fraction_sensitivity_world.csv")
    full_fraction = fraction_sensitivity.loc[fraction_sensitivity.valuation_fraction.eq(1)].iloc[0]

    sections = []
    def add(text: str = "") -> None:
        sections.append(text)

    add("# Climate-finance complete results inventory\n")
    add("**Status (23 October 2026):** regenerated after the mangrove-area and forest-capacity refresh. The GCW allocation is a stipulated scenario; the Busch correction is an independently derived reconstruction, pending clarification with the source authors. Monetary amounts below are in real US$2015 unless otherwise stated. Accounting units may be countries or territories.\n")
    add("## 1. Research questions and analytical scope\n")
    add("1. How is a hypothetical annual allocation equal to 2% of estimated GCW distributed across 236 forest-account units? 2. Among the 105 units with positive reported annual forest-capacity loss, which have published Busch country curves and enough reconstructed 30-year mitigation supply for an equal-tonnage scenario? 3. For the matched units, how do annual-equivalent modeled resource costs and theoretical uniform carbon payments compare with the stipulated allocation? None of these comparisons identifies an actual funding need, an observed transfer, or ecological equivalence.\n")
    add("## 2. Data sources, samples, definitions, and methodology\n")
    add(markdown([
        ["GCW allocation", "236", "GCW from `data/derived/accounts/country_level_gcw.csv`; allocation `0.02 × GCW_mean`", "US$2015 yr⁻¹", "stipulated / modeled valuation"],
        ["Positive capacity loss", "105 of 139 deforestation reporters", "`lost_capacity_tco2_yr > 0`; area loss × four biome rates", "tCO₂ yr⁻¹", "modeled from reported forest loss"],
        ["Busch source country curves", f"138 source curves (115 Core, 23 Other); {n_source_curves} match positive-loss units", "25 grid prices from −20 to 100, step 5", "source workbook labels quantities tCO₂; audit finds tC-like numerics", "published / audited"],
        ["Derived cost comparison", f"{n_matched} target-within-supply units", "Cell outputs; tC→tCO₂ ×(44/12); natural soil term counted once", "30-year discounted tCO₂, US$2015 PV", "derived / provisional"],
    ], ["Object", "Population", "Definition", "Unit", "Status"]))
    add("\nSource horizon: `Q_i = L_i × D`, `D = Σ(t=0,…,29) 0.95^t = " + fmt(SOURCE_FACTOR, 9) + "`. This treats each observed annual capacity loss as persisting for 30 years and follows the source program's factor. The conventional years-1–30 5% factor is " + fmt(CONVENTIONAL_FACTOR, 9) + "; it is a separate sensitivity, not silently substituted. In the 236-row CSV, `lost_capacity_discounted_30yr_tco2` is the older conventional-horizon column, whereas `scenario_target_30yr_tco2_all_positive_loss` uses the source factor for this inventory. Positive-loss units lacking a Busch curve have a scenario `Q_i` in the new country inventory but no source modeled supply/cost. The other 131 of 236 units fall outside the positive-loss sample; their blank Busch fields do not mean a zero mitigation price.\n")
    add("Corrected cell quantity is in tCO₂ after multiplying by `44/12`; natural regeneration uses `aboveground + belowground + soil/2` instead of the source output's `aboveground + belowground + soil`. Plantation carbon is unchanged. Method choice is recalculated with the source rule, and both natural-regeneration and plantation prices are recomputed with the same exact carbon-to-CO₂ ratio. Monetary input variables are converted to US$2015 before calculating cell costs and prices. Eligible cell net 30-year project cost divided by corrected screened/buffered/additional tCO₂ is the derived effective marginal price. The supply curve ranks cells by this price; a fraction of the final cell reaches `Q_i`. Net economic cost is the signed cost sum; positive project cost sums only positive cell costs; theoretical uniform payment is `max(0, marginal price at Q_i) × Q_i`. The annual-equivalent values divide the 30-year present values in US$2015 by `D`. The published workbook's validation grid remains in US$2020.\n")
    add("**Scope distinction.** The current `finance_figure4_summary.json` is the published workbook-grid comparison and remains separate from this cell-level reconstruction. The regenerated `gcw_valuation_fraction_sensitivity_world.csv` 100% row is US$" + fmt(full_fraction.mean_billion_usd2015_yr, 6) + " billion/year and matches current Table 1 GCW of US$" + fmt(gcw_row.value_mean_trillion_usd2015_yr * 1000, 6) + " billion/year. The 2% allocation interval is US$" + fmt(gcw_row.value_p05_trillion_usd2015_yr * 20, 3) + "–" + fmt(gcw_row.value_p95_trillion_usd2015_yr * 20, 3) + " billion/year when only existing GCW draw uncertainty is propagated.\n")
    add("## 3. Exhaustive allocation results\n")
    add(markdown([
        ["GCW mean", fmt(gcw_row.value_mean_trillion_usd2015_yr * 1000, 6), "billion US$2015/yr", "Table 1, Green carbon wealth"],
        ["2% allocation mean / national sum", fmt(a_total / 1e9, 6), "billion US$2015/yr", "0.02 × current GCW; n=236"],
        ["Allocation P05", fmt(gcw_row.value_p05_trillion_usd2015_yr * 20, 6), "billion US$2015/yr", "0.02 × global GCW draw P05"],
        ["Allocation P50", fmt(gcw_row.value_p50_trillion_usd2015_yr * 20, 6), "billion US$2015/yr", "0.02 × global GCW draw P50"],
        ["Allocation P95", fmt(gcw_row.value_p95_trillion_usd2015_yr * 20, 6), "billion US$2015/yr", "0.02 × global GCW draw P95"],
        ["Zero allocated value", str(int(national.our_2pct_gcw_allocation_usd2015_yr.eq(0).sum())), "units", "observed zeros in modeled GCW table; no imputation"],
        ["Unclassified GCW units", str(int(national.groups.isna().sum())), "units", "all 236 have a project group"],
        ["Gini", fmt(gini(national.our_2pct_gcw_allocation_usd2015_yr), 6), "0–1", "equal to GCW Gini by positive scaling"],
        ["HHI", fmt(float(((national.our_2pct_gcw_allocation_usd2015_yr / a_total) ** 2).sum()), 6), "0–1", "sum of squared national allocation shares"],
    ], ["Measure", "Exact result", "Unit", "Formula / denominator"]))
    add("\nThe P05–P95 interval conditions on fixed forest inputs and varying monetary draws. It is neither a confidence interval for the 2% policy rule nor full ecological uncertainty. National P05 and P95 values in the attached 236-row CSV are `0.02 ×` each unit's GCW P05/P95; these are **not additive** into the global draw P05/P95.\n")
    order = national.sort_values("our_2pct_gcw_allocation_usd2015_yr", ascending=False)
    concentration = []
    for k in [1, 5, 10, 20, 25, 50, 100, 118, 200, 236]:
        concentration.append([k, fmt(order.iloc[:k].our_2pct_gcw_allocation_usd2015_yr.sum() / 1e9, 6),
                              fmt(100 * order.iloc[:k].our_2pct_gcw_allocation_usd2015_yr.sum() / a_total, 4),
                              "236 ranked units"])
    add("### Concentration and distribution\n")
    add(markdown(concentration, ["Top N", "Annual allocation (billion US$2015)", "Share of 236-unit total (%)", "Denominator"]))
    add("\nThe bottom 118 units receive " + fmt(100 * order.iloc[118:].our_2pct_gcw_allocation_usd2015_yr.sum() / a_total, 4) + "% of the total. Top-N shares and the Gini are mechanically identical for GCW and a uniform 2% allocation.\n")
    pledge = national.share_of_30yr_100bn_pledge_usd_cumulative
    add("The legacy source table also contains a **separate** illustrative US$100 billion per year pledge allocated in proportion to national GCW for 30 years: total "
        + fmt(pledge.sum() / 1e12, 6) + " trillion US$ cumulative, top 10 "
        + fmt(order.iloc[:10].share_of_30yr_100bn_pledge_usd_cumulative.sum() / 1e12, 6)
        + " trillion (" + fmt(100 * order.iloc[:10].share_of_30yr_100bn_pledge_usd_cumulative.sum() / pledge.sum(), 4)
        + "% of 236-unit total). Formula: `national_GCW / global_GCW × 100 billion × 30`. This is an undiscounted policy thought experiment whose currency price year is unspecified in the source script; it is neither the 2% GCW allocation nor a cost estimate and is **not** pooled with US$2015 results. Full national values remain in the 236-row CSV.\n")
    dist_specs = [
        ("Allocation, 236 units", national.our_2pct_gcw_allocation_usd2015_yr / 1e6, "million US$2015/yr"),
        ("GCW, 236 units", national.gcw_usd2015_yr_mean / 1e9, "billion US$2015/yr"),
    ]
    add(markdown([[name, unit, *[fmt(describe(v)[x], 4) for x in ("min", "p05", "p25", "median", "p75", "p95", "max")],
                   str(describe(v)["zero"])] for name, v, unit in dist_specs],
                 ["Series / n", "Unit", "Min", "P05", "P25", "P50", "P75", "P95", "Max", "Zeros"]))
    add("\n**Ranked national allocations (top 25).** Full rankings, including zero-valued units, are in the 236-row CSV.\n")
    add(markdown([[int(r.allocation_rank), r.UNIT_CODE, r.name, r.groups,
                   fmt(r.our_2pct_gcw_allocation_usd2015_yr / 1e9, 6),
                   fmt(r.cumulative_allocation_share_pct, 4)]
                  for r in order.head(25).itertuples()],
                 ["Rank", "Unit", "Name", "Group", "Allocation (billion US$2015/yr)", "Cumulative share (%)"]))
    add("\n**Observed zero allocations:** " + ", ".join(
        f"{r.iso3} ({r.name})" for r in national.loc[national.our_2pct_gcw_allocation_usd2015_yr.eq(0)].itertuples()
    ) + ". Zero here means the input GCW estimate is zero, not a filled missing value.\n")
    add("### Economic-group allocation and loss composition\n")
    add(markdown([[r.group, r.units_236, fmt(r.allocation_total_usd2015_yr / 1e9, 6),
                   fmt(r.allocation_share_global_pct, 4),
                   fmt(r.allocation_median_usd2015_yr / 1e6, 4),
                   fmt(r.allocation_p25_usd2015_yr / 1e6, 4),
                   fmt(r.allocation_p75_usd2015_yr / 1e6, 4),
                   fmt(r.allocation_gini_within_group, 4), r.allocation_zero_units]
                  for r in groups.itertuples()],
                 ["Exclusive project group", "n", "Total (billion)", "World share (%)", "Median (million)", "P25", "P75", "Within-group Gini", "Zeros"]))
    add("\nThe four project groups are mutually exclusive accounting categories (62 + 80 + 37 + 57 = 236), not independent overlapping UN LDC and SIDS flags. There are zero unclassified **GCW** units after the current territorial fallback, although other marine-only or special units can remain unclassified outside this 236-unit population. Each group allocation statistic is exactly 2% of its GCW counterpart.\n")
    add("## 4. Exhaustive reconstructed reforestation results\n")
    loss_total = sample.lost_capacity_tco2_yr.sum()
    status_rows = []
    for label, part in [
        ("Within supply, non-positive marginal", zero_price),
        ("Within supply, positive marginal", positive),
        ("Within supply, all", matched),
        ("Insufficient modeled supply", insufficient),
        ("No published country curve", missing),
        ("All positive-loss reporters", sample),
    ]:
        status_rows.append([label, len(part), fmt(part.lost_capacity_tco2_yr.sum(), 3),
                            fmt(100 * part.lost_capacity_tco2_yr.sum() / loss_total, 4),
                            fmt(part.lost_capacity_tco2_yr.sum() * SOURCE_FACTOR / 1e6, 6),
                            fmt(part.our_2pct_gcw_allocation_usd2015_yr.sum() / 1e9, 6)])
    add(markdown(status_rows, ["Disjoint status except subtotal rows", "Units", "Loss (tCO₂/yr)", "% of 105-unit loss", "30y target (MtCO₂)", "2% allocation (billion/yr)"]))
    add("\nOf the " + str(n_insufficient) + " insufficient units, " + str(n_zero_supply) + " have exactly zero reconstructed supply and " + str(n_positive_insufficient) + " have positive but inadequate supply. Of " + str(n_source_curves) + " matched source curves, " + str(n_core_curves) + " are on `Core results` and " + str(n_other_curves) + " on `Other results`; across the full workbook there are 115 and 23, respectively. Seven published zero curves are reproduced exactly.\n")
    add("### Source-curve reproduction and correction stages\n")
    at100 = price.loc[price.price_usd2020_per_tco2.eq(100)].iloc[0]
    at50 = price.loc[price.price_usd2020_per_tco2.eq(50)].iloc[0]
    add(markdown([
        ["Curve validation", "71/71", "Max source-supply-normalized difference " + fmt(source_curves.source_reconstruction_max_supply_normalized_error_pct.max(), 6) + "% of each curve maximum"],
        ["Original grid ceiling −20 to 100", "25", "US$2020/tCO₂ points, increment 5; source numeric quantity labels are disputed"],
        ["Published numeric, Core only at 100", str(summary["grid_100_coverage_stages"]["core_only_published_numeric"]), "Historical source-number comparison with target"],
        ["Published numeric, Core + Other at 100", str(summary["grid_100_coverage_stages"]["both_sheets_published_numeric"]), "Adds 11 sample countries with curves from Other"],
        ["×(44/12) carbon conversion at 100", str(summary["grid_100_coverage_stages"]["both_sheets_verified_carbon_conversion"]), "Source tC-like numbers converted to tCO₂"],
        ["×(44/12) and soil counted once at 100", str(summary["grid_100_coverage_stages"]["both_sheets_conversion_and_soil_once"]), "Corrected 25-price supply"],
        ["US$50: converted without soil adjustment", fmt(at50.verified_conversion_tco2_sum / 1e9, 6), "GtCO₂ discounted, 71 countries"],
        ["US$50: conversion + soil adjustment", fmt(at50.conversion_and_soil_once_tco2_sum / 1e9, 6), "GtCO₂ discounted, 71 countries; delta " + fmt(at50.soil_correction_delta_pct, 4) + "%"],
        ["US$100: conversion + soil adjustment", fmt(at100.conversion_and_soil_once_tco2_sum / 1e9, 6), "GtCO₂ discounted, 71 countries, not annual or global"],
        ["Output cells inspected", fmt(source_curves.output_cells.sum(), 0), "Rows across 71 national source DTAs"],
        ["Eligible priced cells", fmt(source_curves.priced_cells.sum(), 0), "Corrected finance-curve cells (nonzero supply only)"],
        ["Cells switching selected method", fmt(source_curves.soil_correction_strategy_switch_cells.sum(), 0), "Count after soil correction; source algorithm reapplied"],
    ], ["Stage / diagnostic", "Value", "Meaning / denominator"]))
    add("\nThe source workbook is preserved. The `×(44/12)` and soil-once series are **derived interpretations** of publicly available cell outputs and code, not corrected values endorsed or published by Busch et al. A repeated soil addition in code is an observed code-path issue; its effect is estimated here but remains subject to author clarification. At US$50, the 71 matched workbook curves sum to "
        + fmt(at50.published_numeric_sum / 1e9, 6) + " billion in their labelled quantity, whereas the converted and soil-adjusted reconstruction sums to "
        + fmt(at50.conversion_and_soil_once_tco2_sum / 1e9, 6) + " billion tCO₂. The workbook's 138-country total is "
        + fmt(at50.published_global_workbook_numeric / 1e9, 6) + " billion, matching the 31.4 GtCO₂ that [Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1) report below US$50. Since our adjusted **71-country subset** exceeds that published global result, the carbon-unit interpretation is scientifically unresolved. Do not combine the adjusted volumes with published totals or describe them as Busch's published findings until this discrepancy is resolved with the authors.\n")
    add("**Full 25-price audit for the 71 matched country curves.** All volume columns below are billions of workbook-labelled units or derived tCO₂ over the source 30-year discounted horizon. The workbook column retains its published numeric value without endorsing its physical unit. The companion CSV retains unrounded values and the soil-correction percentage.\n")
    add(markdown([[fmt(r.price_usd2020_per_tco2, 0), fmt(r.published_global_workbook_numeric / 1e9, 5),
                   fmt(r.published_numeric_sum / 1e9, 5),
                   fmt(r.reconstructed_source_tC_sum / 1e9, 5),
                   fmt(r.verified_conversion_tco2_sum / 1e9, 5),
                   fmt(r.conversion_and_soil_once_tco2_sum / 1e9, 5),
                   fmt(r.soil_correction_delta_pct, 3), int(r.countries_nonzero_corrected)]
                  for r in price.itertuples()],
                 ["Price (US$2020/tCO₂)", "Workbook 138-country total (bn)", "Matched 71 numeric (bn)", "Reproduced 71 numeric (bn)",
                  "×(44/12) (GtCO₂)", "×(44/12) and soil once (GtCO₂)", "Soil change (%)", "Nonzero curves / 71"]))
    add("### Prices, costs and payments at the " + str(n_matched) + " comparable targets\n")
    price_dist = describe(matched.marginal_effective_cost_usd2015_per_discounted_tco2)
    add(markdown([
        ["Marginal effective price", "US$2015/tCO₂", *[fmt(price_dist[k], 4) for k in ("min", "p05", "p25", "median", "p75", "p95", "max")], f"{n_matched} ({n_nonpositive_price} non-positive; {n_positive_price} positive)"],
        *[[name, unit, *[fmt(describe(values)[k], 4) for k in ("min", "p05", "p25", "median", "p75", "p95", "max")], str(len(values))]
          for name, values, unit in [
              ("Positive project cost", matched.positive_project_cost_annual_usd2015 / 1e6, "million US$2015/yr"),
              ("Uniform payment", matched.uniform_carbon_payment_annual_usd2015 / 1e6, "million US$2015/yr"),
              ("Signed net economic cost", matched.net_economic_cost_annual_usd2015 / 1e6, "million US$2015/yr"),
              ("Corrected available supply", source_curves.available_discounted_tco2 / 1e9, "GtCO₂ PV (n=71)"),
              ("Target coverage", source_curves.target_coverage_pct, "% of 30y target (n=71)"),
          ]],
    ], ["Series", "Unit", "Min", "P05", "P25", "P50", "P75", "P95", "Max", "n"]))
    add("\nFor the " + str(n_matched) + " sufficient-supply units, the 30-year present values and annual equivalents reconcile as follows. The " + str(n_nonpositive_price) + " units with non-positive marginal price have a **zero modeled uniform payment**, whereas their signed project costs can be negative; neither result proves zero implementation cost.\n")
    add(markdown([
        ["Signed net economic cost", fmt(matched.net_economic_cost_pv_usd2015.sum() / 1e6, 6), fmt(matched.net_economic_cost_annual_usd2015.sum() / 1e6, 6), str(n_matched), "full signed modeled cost of selected cells"],
        ["Positive project cost", fmt(matched.positive_project_cost_pv_usd2015.sum() / 1e6, 6), fmt(matched.positive_project_cost_annual_usd2015.sum() / 1e6, 6), str(n_matched), "only positive cell net costs"],
        ["Uniform carbon payment", fmt(matched.uniform_carbon_payment_pv_usd2015.sum() / 1e6, 6), fmt(matched.uniform_carbon_payment_annual_usd2015.sum() / 1e6, 6), f"{n_matched} (positive in {n_positive_price})", "positive cutoff price × full discounted target"],
    ], ["Distinct quantity", "30y PV (million US$2015)", "Annual equivalent (million US$2015/yr)", "Population", "Definition"]))
    add("\n**Highest positive marginal-payment cases (all " + str(n_positive_price) + " listed).** Prices are derived cell effective costs, not interpolated values from the published 25-point curve. Zero-payment countries are retained in the 236-unit CSV.\n")
    add(markdown([[r.UNIT_CODE, r.name, r.groups, fmt(r.lost_capacity_tco2_yr, 2),
                   fmt(r.marginal_effective_cost_usd2015_per_discounted_tco2, 4),
                   fmt(r.positive_project_cost_annual_usd2015 / 1e6, 6),
                   fmt(r.uniform_carbon_payment_annual_usd2015 / 1e6, 6),
                   fmt(r.our_2pct_gcw_allocation_usd2015_yr / 1e6, 4),
                   fmt(r.allocation_over_uniform_payment_defined, 4)]
                  for r in positive.sort_values("uniform_carbon_payment_annual_usd2015", ascending=False).itertuples()],
                 ["Unit", "Name", "Group", "Loss (tCO₂/yr)", "Price (US$2015/tCO₂)", "Positive cost (M/yr)", "Payment (M/yr)", "Allocation (M/yr)", "Allocation/payment"]))
    add("\n**Insufficient modeled supply (all " + str(n_insufficient) + "):**\n")
    add(markdown([[r.UNIT_CODE, r.name, fmt(r.lost_capacity_tco2_yr, 2),
                   fmt(r.scenario_target_30yr_tco2_all_positive_loss / 1e6, 5),
                   fmt(r.available_discounted_tco2 / 1e6, 5),
                   fmt(r.target_coverage_pct, 3)]
                  for r in insufficient.sort_values("lost_capacity_tco2_yr", ascending=False).itertuples()],
                 ["Unit", "Name", "Loss (tCO₂/yr)", "Target (MtCO₂)", "Available (MtCO₂)", "Coverage (%)"]))
    add("\n**No source curve (all " + str(n_missing) + "):** " + ", ".join(
        f"{r.UNIT_CODE} ({r.name})" for r in missing.sort_values("lost_capacity_tco2_yr", ascending=False).itertuples()
    ) + ". Their `Q_i` is computable from our loss scenario but supply, price and financing remain unavailable.\n")
    add("## 5. Allocation–mitigation comparisons\n")
    pay_ratio = describe(positive.allocation_over_uniform_payment_defined)
    cost_ratio = describe(matched.allocation_over_positive_cost_defined)
    add(markdown([
        ["2% allocation, all forest-account units", "236", fmt(a_total / 1e9, 6), "billion US$2015/yr", "policy rule, not a budget"],
        ["2% allocation, positive-loss sample", "105", fmt(sample.our_2pct_gcw_allocation_usd2015_yr.sum() / 1e9, 6), "billion US$2015/yr", "broader than cost-comparable sample"],
        ["2% allocation, cost-comparable sample", str(n_matched), fmt(matched.our_2pct_gcw_allocation_usd2015_yr.sum() / 1e9, 6), "billion US$2015/yr", f"same {n_matched} as cost/payment rows"],
        ["Modeled positive project cost", str(n_matched), fmt(matched.positive_project_cost_annual_usd2015.sum() / 1e6, 6), "million US$2015/yr", "annual equivalent of selected positive project costs"],
        ["Modeled uniform payment", str(n_matched), fmt(matched.uniform_carbon_payment_annual_usd2015.sum() / 1e6, 6), "million US$2015/yr", "conditional carbon-price mechanism"],
    ], ["Measure", "n", "Value", "Unit", "Interpretation"]))
    add("\nThe three emphasized figures reconcile exactly: **" + fmt(matched.our_2pct_gcw_allocation_usd2015_yr.sum() / 1e9, 6) + " billion**, **" + fmt(matched.positive_project_cost_annual_usd2015.sum() / 1e6, 6) + " million**, and **" + fmt(matched.uniform_carbon_payment_annual_usd2015.sum() / 1e6, 6) + " million** US$2015/year for the same " + str(n_matched) + " units. Cell-level monetary inputs are converted to US$2015 before cost calculation; present values are annualized by dividing by the 30-year source discount factor. The allocation is itself an annual hypothetical amount; comparing them assumes a constant real annual allocation for 30 years. Cost, payment and allocation are different economic objects, so subtracting them does **not** measure a financing gap.\n")
    add(markdown([
        ["Allocation / positive project cost", int(cost_ratio["n"]), fmt(cost_ratio["min"], 4), fmt(cost_ratio["median"], 4), fmt(cost_ratio["max"], 4), "defined only where positive project cost > 0"],
        ["Allocation / uniform payment", int(pay_ratio["n"]), fmt(pay_ratio["min"], 4), fmt(pay_ratio["median"], 4), fmt(pay_ratio["max"], 4), f"defined only for {n_positive_price} positive-price units"],
    ], ["Ratio", "n", "Minimum", "Median", "Maximum", "Denominator rule"]))
    add("\nFor the " + str(n_positive_price) + " positive-payment units, " + str(int(positive.allocation_over_uniform_payment_defined.gt(1).sum())) + "/" + str(n_positive_price) + " allocations exceed the modeled payment under this mechanism; this does not show real programs are affordable or funded. Ratios are undefined (not zero or infinite) for the " + str(n_nonpositive_price) + " modeled zero-payment units.\n")
    add("## 6. Country-level and economic-group findings\n")
    add(markdown([[r.group, r.units_236, r.positive_loss_units_105,
                   r.available_curve_units, r.no_curve_units,
                   r.insufficient_supply_units, r.within_supply_units,
                   r.positive_price_units,
                   fmt(r.loss_tco2_yr / 1e6, 5),
                   fmt(r.within_supply_share_of_group_loss_pct, 3),
                   fmt(r.matched_allocation_usd2015_yr / 1e9, 5),
                   fmt(r.matched_positive_cost_usd2015_yr / 1e6, 5),
                   fmt(r.matched_uniform_payment_usd2015_yr / 1e6, 5)]
                  for r in groups.itertuples()],
                 ["Group", "GCW n", "Loss n", "Curve n", "No curve n", "Short supply n", "Supply n", "+ price n", "Loss (Mt/yr)", "Group loss covered (%)", "Matched allocation (B/yr)", "+ cost (M/yr)", "Payment (M/yr)"]))
    add("\nCountry-level rows include all 236 allocations and group metadata, all 105 positive-loss targets (including those without source curves), the source-curve sheet, verification errors and cell counts for 71 countries, prices and three cost/payment concepts where supply is sufficient, plus explicitly undefined ratios. This is the complete national inventory for ranking and selection; absence from a source curve is not a zero cost.\n")
    add("## 7. Sensitivity analyses, uncertainties, and methodological limitations\n")
    add(markdown([
        ["Monetary valuation", "Current GCW draw P05–P95 → 2% allocation P05–P95", fmt(gcw_row.value_p05_trillion_usd2015_yr * 20, 3) + "–" + fmt(gcw_row.value_p95_trillion_usd2015_yr * 20, 3) + " billion/yr", "fixed forest rates/areas and fixed 2% rule"],
        ["Current valuation-fraction sensitivity", "25%, 33%, 50%, 75%, 100%", "100% mean " + fmt(full_fraction.mean_billion_usd2015_yr, 3) + " billion GCW/yr", "100% row reconciles with current Table 1"],
        ["Carbon-unit correction", "source numeric ×(44/12)", "at 100: " + str(summary["grid_100_coverage_stages"]["both_sheets_published_numeric"]) + " → " + str(summary["grid_100_coverage_stages"]["both_sheets_verified_carbon_conversion"]) + " covered", "classification effect on same 71"],
        ["Natural soil counted once", "reselect cell method and recalc curves", "at 50: " + fmt(at50.soil_correction_delta_pct, 3) + "% corrected supply", "source interpretation awaiting author clarification"],
        ["Discount timing", "source 15.707225 versus conventional 15.372451", fmt(100 * (SOURCE_FACTOR / CONVENTIONAL_FACTOR - 1), 4) + "% factor difference", "alternative target and annualization require full re-evaluation"],
        ["Published workbook price grid", "Core-only, unconverted, 25 points", str(old["busch_supply_sufficient_by_100_units"]) + " covered at US$100/tCO₂", "separate workbook-grid diagnostic; not the corrected cell-level cost result"],
    ], ["Sensitivity / version", "Change", "Observed diagnostic", "Limit"]))
    add("\nAdditional unpropagated uncertainties: four biome-rate uncertainty, FRA/GEZ forest surface error, mangrove overlap, deforestation coverage and time path, persistence of stored carbon, cell carbon and cost parameters, forest suitability and adoption, transaction costs, governance, wood revenues, future exchange rates and CPI choice. The 2% rule is a policy thought experiment. Busch's 30-year reforestation carbon pools and ecological trajectory are not the same physical service as current annual additions to living forest biomass; equal `Q_i` is scenario matching, not replacement or causal mitigation.\n")
    add("## 8. Validation and reproducibility evidence\n")
    add("- Input workbook, transcribed Python parameter module and current national allocation CSV hashes are recorded in `busch_" + CURRENT_BUSCH_RUN + "_summary.json`; the Zenodo source archive MD5 is `af26192c9349150071e4e4f40ba1f456`. The Stata source values are documented in `code/scripts/busch_stata_parameters.py`; the source script is not parsed at runtime.\n- The " + str(n_source_curves) + " national source curves are re-aggregated from published cell outputs at all 25 price points. The largest error normalized by a country's maximum source quantity is " + fmt(source_curves.source_reconstruction_max_supply_normalized_error_pct.max(), 6) + "%; seven all-zero curves match exactly. Brazil, China and Tanzania were individually checked across all 25 source prices.\n- This script checks unique keys, n=236/105/1,775, the 2% national identity, the global Table 1 reconciliation, and the current " + str(n_matched) + "/" + str(n_insufficient) + "/" + str(n_missing) + " cell-level status counts. It writes the climate-finance inventory files only.\n- The separate workbook-grid summary and this current cell-level reconstruction use different cost definitions and coverage tests. Neither should be substituted for the other.\n- The source workbook's carbon units and the natural-soil code require external author clarification. The current cell-level finance comparison is validated internally against the cell outputs and equations, yet remains provisional scientifically.\n")
    add("## 9. Assessment of scientific relevance\n")
    add(markdown([
        ["New conditional information", f"{n_source_curves} source curves recovered; {n_matched} equal-tonnage targets within corrected modeled supply; {matched_loss_share_pct:.2f}% of the 105-unit annual loss; differentiated project cost and carbon-payment estimates", "Useful for a carefully labelled complementary scenario; not a replacement-cost estimate"],
        ["Mechanically implied", "All national and group 2% totals, rankings, Gini, top-N shares, P05–P95 scaling", "Describes the distribution of GCW under a stipulated rule; no independent finance observation"],
        ["Scientifically informative with caution", f"{n_nonpositive_price} non-positive and {n_positive_price} positive marginal-price cases; {n_insufficient} supply-insufficient; {n_missing} no curve; allocation/payment ratios", "Source corrections, selected coverage and implementation limits must remain visible"],
        ["Provisional interpretation", "tC/tCO₂ and natural-soil corrections; workbook-grid versus cell-level coverage", "Clarify with Busch authors before presenting the derived curves as definitive"],
        ["Strengthen from existing data", f"Show group selection into 105/{n_source_curves}/{n_matched}, country price/payment rank distribution, 25-price correction stages, conventional-discount sensitivity", "No new global model required; any full sensitivity must rerun the cost selection"],
    ], ["Evidence class", "Finding", "Use / boundary"]))
    add("## 10. Proposed Figure 4 designs and supplementary materials\n")
    add("**Option 1 — allocation to comparable payments.** A: cumulative 236-unit allocation (top-10 and top-50 markers); B: group-level country distribution with group totals; C: " + str(n_positive_price) + " positive-price units, paired 2% allocation and modeled uniform payment on a log axis, with a separate note that " + str(n_nonpositive_price) + " matched cases have modeled zero payment. Question: where does the stipulated allocation sit relative to a clearly specified payment mechanism? Avoid treating the separation as a financing gap.\n\n**Option 2 — coverage before comparison.** A: 236-unit concentration; B: transition 105 → " + str(n_source_curves) + " → " + str(n_matched) + ", with disjoint " + str(n_nonpositive_price) + "/" + str(n_positive_price) + "/" + str(n_insufficient) + "/" + str(n_missing) + " loss shares; C: distribution of marginal effective prices for " + str(n_matched) + " and paired allocation/payment for positive-price units. Question: for whom can this comparison be made, and what does selection omit?\n\n**Option 3 — within-sample cost structure.** A: group allocation distributions; B: " + str(n_matched) + "-unit signed economic cost versus positive project cost (separate scales/labels); C: allocation–uniform-payment scatter for " + str(n_positive_price) + " positive cases, with " + str(n_nonpositive_price) + " zero-payment cases marked separately. Question: how do economic resource costs, incentive transfers and hypothetical allocations differ? This is the most technical option.\n")
    add("**Supplementary tables:** full 236-unit country inventory; four-group distribution and sample selection table; all 71 × 25 published/reconstructed/corrected curve points; 25-price aggregate correction table; 100-point effective-cost curve per 64 nonzero-supply units; country-level validation errors and source hashes. **Supplementary figures:** Lorenz and ranked allocation curves; group-specific coverage flow; correction-stage supply curves at all 25 prices; marginal-price and payment distribution with explicit missing and zero cases. These are proposals only; no figure is produced here.\n")
    add("## 11. Complete source and output file references\n")
    add(markdown([
        ["Current GCW", "`data/derived/accounts/country_level_gcw.csv`", "`gcw_usd2015_yr_mean`, P05/P50/P95; 236 rows"],
        ["National 2%, pledge and loss", "`data/derived/validation/our_2pct_gcw_allocation_and_pledge.csv`", "`our_2pct_gcw_allocation_usd2015_yr`, `share_of_30yr_100bn_pledge_usd_cumulative`, `lost_capacity_tco2_yr`, group, 236 rows"],
        ["Global valuation draws", "`results/tables/manuscript/Table1_global_carbon_wealth.csv`", "Green carbon wealth mean/P05/P50/P95"],
        ["Allocation and legacy Busch script", "`code/scripts/compare_finance_and_action_costs.py`", "2% and 105-unit positive-loss sample; old conventional target"],
        ["Latest Busch reconstruction script", "`code/scripts/rebuild_busch_sample_finance.py`", "source reconstruction, carbon/soil correction, effective-price selection, annualization"],
        ["Latest sample coverage", f"`data/derived/busch_reconstruction/busch_{CURRENT_BUSCH_RUN}_coverage_105.csv`", "105 rows; current loss, target and finance status"],
        ["Latest national finance", f"`data/derived/busch_reconstruction/busch_{CURRENT_BUSCH_RUN}_country_finance.csv`", f"{n_source_curves} source curves, of which {n_matched} have target costs"],
        ["All source-price curves", f"`data/derived/busch_reconstruction/busch_{CURRENT_BUSCH_RUN}_25_price_curves.csv`", f"{len(curves)} price-point records, four versioned series"],
        ["Derived detailed curves", "`data/derived/busch_reconstruction/busch_full_effective_cost_curves.csv`", "64 × 100 = 6,400 supply-percentile records; source reconstruction independent of target, re-targeted by current run"],
        ["Validation and input hashes", f"`data/derived/busch_reconstruction/busch_{CURRENT_BUSCH_RUN}_summary.json`", "current sample, coverage, correction stages, source hashes"],
        ["Published source workbook/code", "`data/raw/economic/busch_2024/11_MAC_curves_consolidated.xlsx`; `data/raw/economic/busch_2024/stata_code/10_stata_code/1. Model loop all data.do`", "115 Core + 23 Other country columns; cell model code"],
        ["Public cell outputs", "[Busch et al. Zenodo record 19239386](https://zenodo.org/records/19239386)", "`09_output_dtas.zip`, MD5 as above"],
        ["Currency conversion", "[BLS annual CPI-U](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm)", "2015 = 237.017; 2020 = 258.811"],
        ["Published article", "[Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1)", "published study; derived corrections are ours"],
        ["Workbook-grid Figure 4 outputs", "`data/derived/validation/finance_figure4_summary.json`; `docs/FINANCE_FIGURE4_METHODS_AND_RESULTS.md`", "published-grid test; distinct from current cell-level reconstruction"],
        ["Inventory builder", "`code/scripts/build_climate_finance_results_inventory.py`", "reads only inputs above; writes four new CLIMATE_FINANCE files"],
        ["Complete national inventory", "`data/derived/validation/CLIMATE_FINANCE_country_inventory_236.csv`", "all 236 units with matching/undefined finance fields"],
        ["Group inventory", "`data/derived/validation/CLIMATE_FINANCE_group_inventory.csv`", "group quantiles, totals, sample composition"],
        ["25-price aggregate", "`data/derived/validation/CLIMATE_FINANCE_price_grid_aggregate_71.csv`", "price-by-price carbon and soil correction effects"],
    ], ["Role", "File / source", "Relevant columns / status"]))
    add("\n**Reproduce this inventory:** from the repository root run `python code/scripts/build_climate_finance_results_inventory.py`. This uses the latest existing files and writes only the four inventory artifacts. It does not rerun the 2.94 GB cell reconstruction, modify canonical tables, or export a figure. Source values should be re-audited before any manuscript claim because the Busch interpretations remain provisional.\n")
    OUT.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(json.dumps({"document": str(OUT), "country_rows": len(national),
                      "group_rows": len(groups), "price_rows": len(price),
                      "matched": len(matched), "allocation_usd2015_yr": a_total}, indent=2))


if __name__ == "__main__":
    main()
