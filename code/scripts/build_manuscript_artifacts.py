"""Build the current manuscript figures and tables from canonical project outputs.

The script updates the four main tables and the first three figures described in
``docs/RESULTS_REWRITE_PLAN_2026-10-19.md``. Figure 4 is generated only after an
author-supplied spatial-model selection file exists; competing specifications are
never selected automatically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.patches import Patch, Rectangle
from scipy import stats


GROUP_ORDER = ["Developed economies", "Developing economies", "LDCs", "SIDS"]
BIOME_ORDER = ["tropical", "subtropical", "temperate", "boreal"]
GROUP_COLORS = {
    "Developed economies": "#4C78A8",
    "Developing economies": "#59A14F",
    "LDCs": "#E15759",
    "SIDS": "#8E79B5",
    "Unclassified": "#858585",
}
CO2_PER_C = 44.0 / 12.0
PROFILE_THRESHOLD_PCT = 66.7
IBRAHIM_ALLOCATION_RATE = 0.02
DISCOUNT_RATE = 0.02
EXPECTED_COUNTS = {
    "gcw_units": 236,
    "both_accounts": 175,
    "balance_common_sample": 162,
    "deforestation_reporters": 139,
    "positive_loss_units": 105,
    "units_with_2024_gdp": 196,
    "units_with_2024_emissions": 210,
    "units_with_all_2024_socioeconomics": 193,
}
NE_TO_UNIT = {
    "SDS": "SSD", "SAH": "ESH", "PSX": "PSE", "HKG": "CHN",
    "MAC": "CHN", "TWN": "CHN", "CYN": "CYP", "SOL": "SOM",
    "ALD": "FIN", "ATC": "AUS", "IOA": "AUS",
}


def repository_root() -> Path:
    """Resolve the repository from this script, independently of notebook cwd."""
    return Path(__file__).resolve().parents[2]


def as_bool(series: pd.Series) -> pd.Series:
    """Normalize boolean columns from CSV inputs."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def require_columns(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def load_inputs(root: Path) -> dict[str, pd.DataFrame | np.ndarray]:
    """Read only current canonical accounts and 2024 analysis outputs."""
    results = root / "results"
    validation = results / "validation"
    derived = root / "data" / "derived"

    master = pd.read_csv(validation / "country_level_results_master.csv", low_memory=False)
    require_columns(
        master,
        [
            "iso3", "name", "continent", "groups", "has_gcw", "has_bcw",
            "gcw_usd2015_yr_mean", "bcw_usd2015_yr_mean", "ncw_usd2015_yr_mean",
            "gdp_2015usd_2024", "population_2024", "co2_emissions_tco2_2024", "reported_deforestation",
            "loss_tco2_mean", "loss_value_usd2015_yr_mean", "erosion_pct_of_gcw",
            "forest_additions_from_area_rates_tCO2_yr", "ibrahim_2pct_usd2015_yr",
        ],
        "country_level_results_master.csv",
    )
    master["has_gcw"] = as_bool(master["has_gcw"])
    master["has_bcw"] = as_bool(master["has_bcw"])
    master["reported_deforestation"] = as_bool(master["reported_deforestation"])

    rates = pd.read_csv(derived / "gfw_gibbs_biome_rates_non_mangrove.csv")
    area = pd.read_csv(derived / "forest_area_by_biome.csv")
    pan = pd.read_csv(derived / "biome_rates.csv")
    balance = pd.read_csv(validation / "emissions_2024_accounting_balance_by_unit.csv")
    busch_status = pd.read_csv(validation / "busch_action_curve_status_summary.csv")
    busch_units = pd.read_csv(validation / "busch_action_curve_country_scenarios.csv")
    spatial_evidence = pd.read_csv(validation / "spatial_emissions_2024_model_selection_evidence.csv")
    spatial_coefficients = pd.read_csv(validation / "spatial_emissions_2024_model_coefficients.csv")

    gcw_archive = np.load(results / "draws" / "gcw_draws.npz", allow_pickle=True)
    ncw_archive = np.load(results / "draws" / "ncw_draws.npz", allow_pickle=True)
    inputs: dict[str, pd.DataFrame | np.ndarray] = {
        "master": master,
        "rates": rates,
        "area": area,
        "pan": pan,
        "balance": balance,
        "busch_status": busch_status,
        "busch_units": busch_units,
        "spatial_evidence": spatial_evidence,
        "spatial_coefficients": spatial_coefficients,
        "gcw_draws": gcw_archive["gcw_usd2015_yr"].astype("float64"),
        "gcw_units": gcw_archive["iso3"].astype(str),
        "bcw_draws": ncw_archive["bcw_usd2015_yr"].astype("float64"),
        "ncw_draws": ncw_archive["ncw_usd2015_yr"].astype("float64"),
    }
    return inputs


def validate_samples(inputs: dict[str, pd.DataFrame | np.ndarray]) -> dict[str, int]:
    """Check the agreed sample counts before writing paper-facing artefacts."""
    master = inputs["master"]
    balance = inputs["balance"]
    assert isinstance(master, pd.DataFrame) and isinstance(balance, pd.DataFrame)
    both = master["has_gcw"] & master["has_bcw"]
    reporters = master["reported_deforestation"]
    positive = master["loss_tco2_mean"].gt(0)
    balance_units = set(balance["iso3"].astype(str))
    common_balance = int((both & master["iso3"].astype(str).isin(balance_units)).sum())
    counts = {
        "gcw_units": int(master.loc[master["has_gcw"], "iso3"].nunique()),
        "both_accounts": int(master.loc[both, "iso3"].nunique()),
        "balance_common_sample": common_balance,
        "deforestation_reporters": int(reporters.sum()),
        "positive_loss_units": int((reporters & positive).sum()),
        "units_with_2024_gdp": int(master.loc[master["has_gcw"], "gdp_2015usd_2024"].notna().sum()),
        "units_with_2024_emissions": int(master["co2_emissions_tco2_2024"].notna().sum()),
        "units_with_all_2024_socioeconomics": int(
            (
                master["population_2024"].notna()
                & master["gdp_2015usd_2024"].notna()
                & master["co2_emissions_tco2_2024"].notna()
            ).sum()
        ),
    }
    mismatches = {
        name: {"expected": EXPECTED_COUNTS[name], "actual": value}
        for name, value in counts.items()
        if value != EXPECTED_COUNTS[name]
    }
    if mismatches:
        raise ValueError(f"Canonical sample-count check failed: {mismatches}")
    return counts


def draw_summary(draws: np.ndarray) -> dict[str, float]:
    values = np.asarray(draws, dtype="float64")
    return {
        "mean": float(np.nanmean(values)),
        "p05": float(np.nanpercentile(values, 5)),
        "p50": float(np.nanpercentile(values, 50)),
        "p95": float(np.nanpercentile(values, 95)),
    }


def gini_coefficient(values: pd.Series) -> float:
    """Compute the Gini coefficient for a finite non-negative series."""
    x = np.sort(pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float))
    if len(x) == 0 or np.any(x < 0) or x.sum() == 0:
        return float("nan")
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def group_frame(master: pd.DataFrame) -> pd.DataFrame:
    data = master.copy()
    data["group_label"] = data["groups"].fillna("Unclassified")
    return data


def build_tables(root: Path, inputs: dict[str, pd.DataFrame | np.ndarray]) -> dict[str, pd.DataFrame]:
    """Create the four proposed main tables and the key reproducibility tables."""
    out = root / "results" / "tables" / "manuscript"
    out.mkdir(parents=True, exist_ok=True)
    master = group_frame(inputs["master"])
    rates = inputs["rates"].copy()
    area = inputs["area"].query("variant == 'documented_overlap_removed'").copy()
    balance = inputs["balance"].copy()
    gcw_draws = inputs["gcw_draws"]
    bcw_draws = inputs["bcw_draws"]
    ncw_draws = inputs["ncw_draws"]
    gcw_units = inputs["gcw_units"]

    # Table 1: global monetary distributions from the aligned Monte Carlo draws.
    global_draws = {
        "Green carbon wealth": np.nansum(gcw_draws, axis=0),
        "Blue carbon wealth": np.nansum(bcw_draws, axis=0),
        "Natural carbon wealth": np.nansum(ncw_draws, axis=0),
    }
    summaries = {name: draw_summary(draws) for name, draws in global_draws.items()}
    total_mean = summaries["Natural carbon wealth"]["mean"]
    table1 = pd.DataFrame(
        [
            {
                "component": name,
                "value_mean_trillion_usd2015_yr": stats["mean"] / 1e12,
                "value_p05_trillion_usd2015_yr": stats["p05"] / 1e12,
                "value_p50_trillion_usd2015_yr": stats["p50"] / 1e12,
                "value_p95_trillion_usd2015_yr": stats["p95"] / 1e12,
                "share_of_ncw_pct": 100 * stats["mean"] / total_mean,
            }
            for name, stats in summaries.items()
        ]
    )
    table1.to_csv(out / "Table1_global_carbon_wealth.csv", index=False)

    # Supplement S1: physical forest account and four non-mangrove biome rates.
    area_totals = area.groupby("biome", as_index=False)["area_ha"].sum()
    s1 = area_totals.merge(
        rates[["biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "period", "source"]],
        on="biome",
        how="left",
        validate="one_to_one",
    )
    s1["gross_additions_tc_yr"] = s1["area_ha"] * s1["rate_tc_ha_yr_mean"]
    s1["gross_additions_gtco2_yr"] = s1["gross_additions_tc_yr"] * CO2_PER_C / 1e9
    s1["spatial_rate_low_tc_ha_yr"] = (s1["rate_tc_ha_yr_mean"] - s1["rate_tc_ha_yr_spatial_sd"]).clip(lower=0)
    s1["spatial_rate_high_tc_ha_yr"] = s1["rate_tc_ha_yr_mean"] + s1["rate_tc_ha_yr_spatial_sd"]
    s1 = s1.set_index("biome").reindex(BIOME_ORDER).reset_index()
    total_row = {
        "biome": "Total",
        "area_ha": s1["area_ha"].sum(),
        "rate_tc_ha_yr_mean": np.nan,
        "rate_tc_ha_yr_spatial_sd": np.nan,
        "period": "2001-2023 source rates; FRA 2025 forest area",
        "source": "Gibbs et al. (2025), Gibbs/GFW; FRA 2025 and GEZ allocation",
        "gross_additions_tc_yr": s1["gross_additions_tc_yr"].sum(),
        "gross_additions_gtco2_yr": s1["gross_additions_gtco2_yr"].sum(),
        "spatial_rate_low_tc_ha_yr": np.nan,
        "spatial_rate_high_tc_ha_yr": np.nan,
    }
    s1 = pd.concat([s1, pd.DataFrame([total_row])], ignore_index=True)
    s1["spatial_rate_interpretation"] = "Spatial dispersion sensitivity; not a confidence interval"
    s1.to_csv(out / "Supplementary_forest_biome_accounting.csv", index=False)

    # Paper-ready summary in the requested units and display precision.
    global_flow = float(s1.loc[s1["biome"].eq("Total"), "gross_additions_gtco2_yr"].iloc[0])
    paper_s1 = pd.DataFrame(
        {
            "Forest biome": s1["biome"].str.title(),
            "Forest area (Mha)": s1["area_ha"] / 1e6,
            "Removal rate (tC ha⁻¹ yr⁻¹)": s1["rate_tc_ha_yr_mean"],
            "Gross additions (GtCO₂ yr⁻¹)": s1["gross_additions_gtco2_yr"],
            "Global share (%)": 100 * s1["gross_additions_gtco2_yr"] / global_flow,
        }
    )
    paper_s1["Forest area (Mha)"] = paper_s1["Forest area (Mha)"].map(lambda x: f"{x:,.1f}")
    # Make the displayed total agree with the displayed biome areas; the
    # calculation table above retains the unrounded total.
    paper_s1.loc[paper_s1["Forest biome"].eq("Total"), "Forest area (Mha)"] = f"{sum(float(v.replace(',', '')) for v in paper_s1.loc[~paper_s1['Forest biome'].eq('Total'), 'Forest area (Mha)']):,.1f}"
    paper_s1["Removal rate (tC ha⁻¹ yr⁻¹)"] = paper_s1["Removal rate (tC ha⁻¹ yr⁻¹)"].map(
        lambda x: "—" if pd.isna(x) else f"{x:.3f}"
    )
    paper_s1["Gross additions (GtCO₂ yr⁻¹)"] = paper_s1["Gross additions (GtCO₂ yr⁻¹)"].map(lambda x: f"{x:.3f}")
    paper_s1["Global share (%)"] = paper_s1["Global share (%)"].map(lambda x: f"{x:.1f}")
    paper_s1.to_csv(out / "TableS1_forest_biome_additions.csv", index=False)

    # Pan remains the sole comparison-rate source; it is not mixed into the main estimate.
    pan = inputs["pan"].copy()
    gfw_compare = rates[["biome", "rate_tc_ha_yr_mean", "period", "source"]].rename(
        columns={
            "rate_tc_ha_yr_mean": "gibbs_gfw_rate_tc_ha_yr",
            "period": "gibbs_gfw_period",
            "source": "gibbs_gfw_source",
        }
    )
    pan_compare = pan[["pan_biome", "pan_row", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_sd", "source"]].rename(
        columns={
            "pan_biome": "biome",
            "rate_tc_ha_yr_mean": "pan_rate_tc_ha_yr",
            "rate_tc_ha_yr_sd": "pan_rate_sd_tc_ha_yr",
            "source": "pan_source",
        }
    )
    pan_compare["pan_period"] = "2010-2019"
    pan_merge = gfw_compare.merge(
        pan_compare,
        left_on="biome",
        right_on="biome",
        how="outer",
    )
    pan_merge["comparison_note"] = (
        "Contextual comparison only: periods and source biome definitions differ; "
        "Pan has no separate subtropical estimate."
    )
    pan_merge.to_csv(out / "Supplementary_Pan_rate_comparison.csv", index=False)

    # Prepare two-account composition and 2024 GDP ratios on their own valid samples.
    master["gcw_gdp_2024_pct"] = 100 * master["gcw_usd2015_yr_mean"] / master["gdp_2015usd_2024"]
    both = master.loc[
        master["has_gcw"] & master["has_bcw"] & master["ncw_usd2015_yr_mean"].gt(0)
    ].copy()
    both["gcw_share_ncw_pct"] = 100 * both["gcw_usd2015_yr_mean"] / both["ncw_usd2015_yr_mean"]
    both["profile"] = np.select(
        [
            both["gcw_share_ncw_pct"] >= PROFILE_THRESHOLD_PCT,
            both["gcw_share_ncw_pct"] <= 100 - PROFILE_THRESHOLD_PCT,
        ],
        ["Green-dominant", "Blue-dominant"],
        default="Mixed",
    )
    group_records = []
    for group in [*GROUP_ORDER, "Unclassified"]:
        group_all = master.loc[master["group_label"] == group]
        group_profiles = both.loc[both["group_label"] == group]
        ratio_values = group_all.loc[group_all["gcw_gdp_2024_pct"].notna(), "gcw_gdp_2024_pct"]
        group_records.append(
            {
                "group": group,
                "units_with_gcw": int(group_all["has_gcw"].sum()),
                "units_with_gcw_and_bcw": int(len(group_profiles)),
                "units_with_2024_gdp": int(group_all["gcw_gdp_2024_pct"].notna().sum()),
                "gcw_trillion_usd2015_yr": group_all["gcw_usd2015_yr_mean"].sum(min_count=1) / 1e12,
                "median_gcw_gdp_2024_pct": ratio_values.median(),
                "green_dominant_units": int(group_profiles["profile"].eq("Green-dominant").sum()),
                "mixed_units": int(group_profiles["profile"].eq("Mixed").sum()),
                "blue_dominant_units": int(group_profiles["profile"].eq("Blue-dominant").sum()),
            }
        )
    all_profiles = both
    total = {
        "group": "Total",
        "units_with_gcw": int(master["has_gcw"].sum()),
        "units_with_gcw_and_bcw": len(all_profiles),
        "units_with_2024_gdp": int(master.loc[master["has_gcw"], "gcw_gdp_2024_pct"].notna().sum()),
        "gcw_trillion_usd2015_yr": master.loc[master["has_gcw"], "gcw_usd2015_yr_mean"].sum() / 1e12,
        "median_gcw_gdp_2024_pct": master.loc[master["has_gcw"], "gcw_gdp_2024_pct"].median(),
        "green_dominant_units": int(all_profiles["profile"].eq("Green-dominant").sum()),
        "mixed_units": int(all_profiles["profile"].eq("Mixed").sum()),
        "blue_dominant_units": int(all_profiles["profile"].eq("Blue-dominant").sum()),
    }
    table2 = pd.DataFrame(group_records + [total])
    table2.to_csv(out / "Table2_geographic_economic_profiles.csv", index=False)

    # Supplementary current geographic profiles and distribution diagnostics.
    continent_rows = []
    master["continent_label"] = master["continent"].fillna("Unclassified")
    for continent, subset in master.groupby("continent_label", sort=True):
        gcw_units = subset.loc[subset["has_gcw"]]
        bcw_units = subset.loc[subset["has_bcw"]]
        both_units = subset.loc[subset["has_gcw"] & subset["has_bcw"]]
        continent_rows.append(
            {
                "continent": continent,
                "units_with_gcw": int(gcw_units["iso3"].nunique()),
                "units_with_bcw": int(bcw_units["iso3"].nunique()),
                "units_with_both_accounts": int(both_units["iso3"].nunique()),
                "gcw_trillion_usd2015_yr": gcw_units["gcw_usd2015_yr_mean"].sum(min_count=1) / 1e12,
                "bcw_trillion_usd2015_yr": bcw_units["bcw_usd2015_yr_mean"].sum(min_count=1) / 1e12,
                "ncw_trillion_usd2015_yr": both_units["ncw_usd2015_yr_mean"].sum(min_count=1) / 1e12,
                "units_with_2024_gdp": int(gcw_units["gcw_gdp_2024_pct"].notna().sum()),
                "median_gcw_gdp_2024_pct": gcw_units["gcw_gdp_2024_pct"].median(),
            }
        )
    continent_table = pd.DataFrame(continent_rows)
    continent_total = {
        "continent": "All units",
        "units_with_gcw": int(master["has_gcw"].sum()),
        "units_with_bcw": int(master["has_bcw"].sum()),
        "units_with_both_accounts": int((master["has_gcw"] & master["has_bcw"]).sum()),
        "gcw_trillion_usd2015_yr": master.loc[master["has_gcw"], "gcw_usd2015_yr_mean"].sum() / 1e12,
        "bcw_trillion_usd2015_yr": master.loc[master["has_bcw"], "bcw_usd2015_yr_mean"].sum() / 1e12,
        "ncw_trillion_usd2015_yr": master.loc[master["has_gcw"] & master["has_bcw"], "ncw_usd2015_yr_mean"].sum() / 1e12,
        "units_with_2024_gdp": int(master.loc[master["has_gcw"], "gcw_gdp_2024_pct"].notna().sum()),
        "median_gcw_gdp_2024_pct": master.loc[master["has_gcw"], "gcw_gdp_2024_pct"].median(),
    }
    continent_table = pd.concat([continent_table, pd.DataFrame([continent_total])], ignore_index=True)
    continent_table.to_csv(out / "Supplementary_continent_profiles_2024.csv", index=False)

    distribution_rows = []
    concentration_specs = [
        ("GCW", master.loc[master["has_gcw"], "gcw_usd2015_yr_mean"]),
        ("BCW", master.loc[master["has_bcw"], "bcw_usd2015_yr_mean"]),
        ("NCW", master.loc[master["has_gcw"] & master["has_bcw"], "ncw_usd2015_yr_mean"]),
    ]
    for measure, values in concentration_specs:
        values = pd.to_numeric(values, errors="coerce").dropna()
        ordered = values.sort_values(ascending=False)
        distribution_rows.append(
            {
                "measure": measure,
                "n_units": int(len(values)),
                "gini": gini_coefficient(values),
                "top_10_share_pct": 100 * ordered.head(10).sum() / values.sum(),
                "top_50_share_pct": 100 * ordered.head(50).sum() / values.sum(),
                "median_usd2015_yr": float(values.median()),
            }
        )
    distribution_table = pd.DataFrame(distribution_rows)
    distribution_table.to_csv(out / "Supplementary_account_concentration_2024.csv", index=False)

    ratio_samples = {
        group: master.loc[
            master["group_label"].eq(group), "gcw_gdp_2024_pct"
        ].dropna().to_numpy(dtype=float)
        for group in GROUP_ORDER
    }
    ratio_samples = {group: values for group, values in ratio_samples.items() if len(values) > 2}
    kw_stat, kw_p = stats.kruskal(*ratio_samples.values())
    pairwise_rows = [
        {
            "test": "Kruskal-Wallis across economic groups",
            "group_a": "All classified groups",
            "group_b": "",
            "n_a": int(sum(len(values) for values in ratio_samples.values())),
            "n_b": np.nan,
            "statistic": float(kw_stat),
            "p_raw": float(kw_p),
            "p_holm": np.nan,
        }
    ]
    pairwise_start = len(pairwise_rows)
    group_names = list(ratio_samples)
    for i, group_a in enumerate(group_names):
        for group_b in group_names[i + 1 :]:
            u_stat, p_value = stats.mannwhitneyu(
                ratio_samples[group_a], ratio_samples[group_b], alternative="two-sided"
            )
            pairwise_rows.append(
                {
                    "test": "Mann-Whitney U; Holm-adjusted pairwise comparison",
                    "group_a": group_a,
                    "group_b": group_b,
                    "n_a": int(len(ratio_samples[group_a])),
                    "n_b": int(len(ratio_samples[group_b])),
                    "statistic": float(u_stat),
                    "p_raw": float(p_value),
                    "p_holm": np.nan,
                }
            )
    raw_pairwise = np.array([row["p_raw"] for row in pairwise_rows[pairwise_start:]], dtype=float)
    if len(raw_pairwise):
        order = np.argsort(raw_pairwise)
        adjusted = np.maximum.accumulate((len(raw_pairwise) - np.arange(len(raw_pairwise))) * raw_pairwise[order])
        adjusted = np.clip(adjusted, 0, 1)
        for rank, idx in enumerate(order):
            pairwise_rows[pairwise_start + int(idx)]["p_holm"] = float(adjusted[rank])
    pd.DataFrame(pairwise_rows).to_csv(out / "Supplementary_GCW_GDP_group_tests_2024.csv", index=False)

    scatter = master.loc[
        master["reported_deforestation"] & master["loss_tco2_mean"].gt(0),
        ["gcw_usd2015_yr_mean", "erosion_pct_of_gcw"],
    ].dropna()
    rho, rho_p = stats.spearmanr(scatter["gcw_usd2015_yr_mean"], scatter["erosion_pct_of_gcw"])
    pd.DataFrame(
        [
            {
                "association": "GCW versus relative annual capacity loss",
                "n": int(len(scatter)),
                "spearman_rho": float(rho),
                "p_value": float(rho_p),
                "interpretive_note": "Descriptive; relative loss includes GCW in its denominator.",
            }
        ]
    ).to_csv(out / "Supplementary_GCW_erosion_association.csv", index=False)

    # Figure 2 transition matrix source: same units with both accounts and GCB 2024 emissions.
    common = balance.merge(
        master[["iso3", "has_gcw", "has_bcw"]], on="iso3", how="left", validate="one_to_one"
    )
    common = common.loc[common["has_gcw"] & common["has_bcw"]].copy()
    common["before_positive"] = common["gcw_accounting_balance_mean_tco2_yr"].gt(0)
    common["after_positive"] = common["ncw_accounting_balance_mean_tco2_yr"].gt(0)
    transitions = (
        common.groupby(["before_positive", "after_positive"], dropna=False)
        .size()
        .rename("units")
        .reset_index()
    )
    transition_matrix = pd.crosstab(common["before_positive"], common["after_positive"])
    transition_rows = []
    for before in [True, False]:
        for after in [True, False]:
            transition_rows.append(
                {
                    "before_gcw_balance_positive": before,
                    "after_ncw_balance_positive": after,
                    "units": int(transition_matrix.get(after, pd.Series(dtype=int)).get(before, 0)),
                    "common_sample_n": int(len(common)),
                }
            )
    transition_table = pd.DataFrame(transition_rows)
    expected_transitions = {(True, True): 56, (True, False): 0, (False, True): 35, (False, False): 71}
    actual_transitions = {
        (bool(row.before_gcw_balance_positive), bool(row.after_ncw_balance_positive)): int(row.units)
        for row in transition_table.itertuples(index=False)
    }
    if actual_transitions != expected_transitions:
        raise ValueError(f"2024 balance-transition check failed: {actual_transitions}")
    transition_table.to_csv(out / "Supplementary_accounting_balance_transitions.csv", index=False)
    balance.merge(
        master[["iso3", "has_gcw", "has_bcw", "groups", "gcw_usd2015_yr_mean", "bcw_usd2015_yr_mean"]],
        on="iso3",
        how="left",
        validate="one_to_one",
    ).to_csv(out / "Supplementary_accounting_balances_2024_by_unit.csv", index=False)

    # Table 3: losses among reporting units; unreported units remain missing.
    report = master.loc[master["reported_deforestation"]].copy()
    report["positive_loss"] = report["loss_tco2_mean"].gt(0)
    table3_rows = []
    for group in [*GROUP_ORDER, "Unclassified"]:
        subset = report.loc[report["group_label"] == group]
        table3_rows.append(
            {
                "group": group,
                "reporting_units": int(len(subset)),
                "positive_loss_units": int(subset["positive_loss"].sum()),
                "lost_capacity_mtco2_yr": subset["loss_tco2_mean"].sum(min_count=1) / 1e6,
                "lost_gcw_billion_usd2015_yr": subset["loss_value_usd2015_yr_mean"].sum(min_count=1) / 1e9,
                "median_erosion_pct_of_gcw": subset["erosion_pct_of_gcw"].median(),
            }
        )
    all_report = report
    table3_rows.append(
        {
            "group": "Total",
            "reporting_units": len(all_report),
            "positive_loss_units": int(all_report["positive_loss"].sum()),
            "lost_capacity_mtco2_yr": all_report["loss_tco2_mean"].sum(min_count=1) / 1e6,
            "lost_gcw_billion_usd2015_yr": all_report["loss_value_usd2015_yr_mean"].sum(min_count=1) / 1e9,
            "median_erosion_pct_of_gcw": np.nan,
        }
    )
    table3 = pd.DataFrame(table3_rows)
    table3.to_csv(out / "Table3_forest_capacity_erosion.csv", index=False)
    erosion_country = master.loc[
        master["has_gcw"],
        [
            "iso3", "name", "continent", "groups", "gdp_2015usd_2024",
            "gcw_usd2015_yr_mean", "reported_deforestation", "loss_tco2_mean",
            "loss_value_usd2015_yr_mean", "loss_value_usd2015_yr_p05", "loss_value_usd2015_yr_p95",
            "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
            "loss_spatial_sd_low_usd2015_yr", "loss_spatial_sd_high_usd2015_yr",
            "erosion_pct_of_gcw", "loss_pct_of_gdp",
        ],
    ].copy()
    erosion_country = erosion_country.rename(
        columns={
            "gdp_2015usd_2024": "gdp",
            "loss_value_usd2015_yr_mean": "loss_usd_mean",
            "loss_value_usd2015_yr_p05": "loss_usd_p05",
            "loss_value_usd2015_yr_p95": "loss_usd_p95",
        }
    )
    erosion_country.to_csv(out / "Supplementary_country_level_erosion.csv", index=False)

    # Country-level manuscript file: one current row per unit. Historical
    # emissions/mangrove baselines and non-Pan alternative forest estimates stay
    # in provenance/archive files, not in the canonical drafting table.
    obsolete_country_fields = {
        "population_bcw_reference",
        "gdp_2015usd_bcw_reference",
        "ncw_per_capita_usd2015_bcw_reference",
        "ncw_share_of_gdp_bcw_reference",
        "bcw_published_usd2015_yr_mean",
        "bcw_mangrove_gapfill_usd2015_yr_mean",
        "bcw_mangrove_gapfilled",
        "ncw_alt_mangroves_usd2015_yr_mean",
        "co2_emissions_tco2_2023_gcb2025",
        "gcb_2023_mtC_yr",
        "gcb_2023_mtco2_yr",
        "bcw_mangroves_before_gmw_ha",
        "gmw_minus_preupdate_mangrove_area_ha",
        "mangrove_area_km2_hilmi_source",
        "mangrove_uptake_tC_yr_hilmi_source_mean",
        "coastal_uptake_tC_yr_hilmi_source_mean",
        "gcw_no_overlap_removed_usd2015_yr_mean",
    }
    country = master.drop(
        columns=[
            column
            for column in master.columns
            if column in obsolete_country_fields or column.startswith("faostat_")
        ],
        errors="ignore",
    ).copy()
    country = country.drop(
        columns=[column for column in country.columns if column.startswith("spatial_sample_legacy")],
        errors="ignore",
    )
    country = country.sort_values("iso3").reset_index(drop=True)
    country.to_csv(out / "Supplementary_country_level_accounts_2024.csv", index=False)

    # Supplement S3: align the FRA overlap audit, GMW 2025 area, updated BCW
    # mangrove contribution, and national identifiers in one traceable table.
    derived = root / "data" / "derived"
    overlap = pd.read_csv(derived / "fra_mangrove_forest_overlap_2025.csv")
    gmw_area = pd.read_csv(derived / "gmw_2025_mangrove_area_by_unit.csv")
    mangrove_columns = [
        "iso3", "name", "continent", "groups", "fra_total_forest_area_2025_ha",
        "fra_mangrove_category_2025_ha", "fra_other_wooded_land_2025_ha",
        "gmw_2025_mangrove_area_applied_ha", "gmw_mangrove_uptake_tC_yr_mean",
        "gmw_mangrove_uptake_tCO2_yr_mean", "gmw_mangrove_uptake_tC_yr_p05",
        "gmw_mangrove_uptake_tC_yr_p50", "gmw_mangrove_uptake_tC_yr_p95",
        "bcw_gmw_mangroves_usd2015_yr_mean", "bcw_usd2015_yr_mean",
        "gmw_name", "gmw_minus_fra_mangroves_ha",
    ]
    available_mangrove_columns = [column for column in mangrove_columns if column in master.columns]
    mangrove = overlap.merge(gmw_area, on="iso3", how="outer", validate="one_to_one")
    mangrove = mangrove.merge(
        master[available_mangrove_columns], on="iso3", how="left", validate="one_to_one"
    )
    mangrove = mangrove.sort_values("iso3").reset_index(drop=True)
    mangrove["accounting_note"] = (
        "FRA mangrove hectares are removed from GCW only where national documentation verifies "
        "their inclusion in the strict forest total; GMW 2025 is the applied BCW mangrove area. "
        "Unresolved FRA overlap is retained and reported as a limitation."
    )
    mangrove.to_csv(out / "Supplementary_mangrove_reconciliation.csv", index=False)

    # The projection/capitalisation are distinct from the 2% allocation scenario.
    annual_loss_tco2 = float(all_report["loss_tco2_mean"].sum(min_count=1))
    annual_loss_value = float(all_report["loss_value_usd2015_yr_mean"].sum(min_count=1))
    global_forest_flow_tco2 = float(master.loc[master["has_gcw"], "forest_additions_from_area_rates_tCO2_yr"].sum())
    scenarios = pd.DataFrame(
        [
            {
                "metric": "Current annual lost forest addition capacity",
                "value": annual_loss_tco2 / 1e6,
                "unit": "MtCO2/yr",
                "assumption_or_formula": "Sum of reported-unit estimates; 139 reporting units, including zero-loss reports",
            },
            {
                "metric": "Ten-year cumulative capacity not supplied",
                "value": annual_loss_tco2 * 10 / 1e9,
                "unit": "GtCO2 over 10 years",
                "assumption_or_formula": "Current annual loss repeats for 10 years; no regrowth or rate change",
            },
            {
                "metric": "Ten-year cumulative loss relative to current annual forest flow",
                "value": 100 * annual_loss_tco2 * 10 / global_forest_flow_tco2,
                "unit": "% of current annual forest additions",
                "assumption_or_formula": "Ten-year cumulative loss / global annual forest additions",
            },
            {
                "metric": "Current annual lost GCW value",
                "value": annual_loss_value / 1e9,
                "unit": "billion US$2015/yr",
                "assumption_or_formula": "Sum of reported-unit annual lost GCW estimates",
            },
            {
                "metric": "Perpetuity value of annual lost GCW at 2% discount rate",
                "value": annual_loss_value / DISCOUNT_RATE / 1e12,
                "unit": "trillion US$2015",
                "assumption_or_formula": "Annual lost GCW value / 0.02; perpetual constant stream, no growth",
            },
        ]
    )
    scenarios["discount_rate"] = np.where(
        scenarios["metric"].str.contains("Perpetuity"), DISCOUNT_RATE, np.nan
    )
    scenarios["ibrahim_allocation_rate"] = np.nan
    scenarios.to_csv(out / "Supplementary_deforestation_scenarios.csv", index=False)

    # Table 4: Ibrahim's stipulated 2% of annual GCW; Busch remains separate.
    allocation = master.loc[master["has_gcw"]].copy()
    allocation["allocation_usd2015_yr"] = allocation["ibrahim_2pct_usd2015_yr"]
    allocation["group_label"] = allocation["groups"].fillna("Unclassified")
    finance_rows = []
    for group in [*GROUP_ORDER, "Unclassified"]:
        subset = allocation.loc[allocation["group_label"] == group]
        amount = float(subset["allocation_usd2015_yr"].sum())
        finance_rows.append(
            {
                "group": group,
                "units": len(subset),
                "annual_allocation_billion_usd2015": amount / 1e9,
                "share_of_total_pct": np.nan,
                "median_allocation_per_unit_million_usd2015": subset["allocation_usd2015_yr"].median() / 1e6,
            }
        )
    total_allocation = float(allocation["allocation_usd2015_yr"].sum())
    table4 = pd.DataFrame(finance_rows)
    table4["share_of_total_pct"] = 100 * table4["annual_allocation_billion_usd2015"] / (total_allocation / 1e9)
    table4 = pd.concat(
        [
            table4,
            pd.DataFrame(
                [
                    {
                        "group": "Total",
                        "units": len(allocation),
                        "annual_allocation_billion_usd2015": total_allocation / 1e9,
                        "share_of_total_pct": 100.0,
                        "median_allocation_per_unit_million_usd2015": np.nan,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    table4.to_csv(out / "Table4_Ibrahim_2pct_allocation.csv", index=False)

    ranking_specs = [
        ("GCW", "gcw_usd2015_yr_mean", "US$2015/yr", master["has_gcw"]),
        ("BCW", "bcw_usd2015_yr_mean", "US$2015/yr", master["has_bcw"]),
        ("NCW", "ncw_usd2015_yr_mean", "US$2015/yr", master["has_gcw"] & master["has_bcw"]),
        ("GCW / GDP 2024", "gcw_gdp_2024_pct", "%", master["has_gcw"]),
        ("GDP 2024", "gdp_2015usd_2024", "US$2015/yr", master["gdp_2015usd_2024"].notna()),
        ("Population 2024", "population_2024", "people", master["population_2024"].notna()),
        ("GCB emissions 2024", "co2_emissions_tco2_2024", "tCO2/yr", master["co2_emissions_tco2_2024"].notna()),
        ("GCW accounting balance 2024", "gcw_accounting_balance_mean_tco2_yr", "tCO2/yr", master["gcw_accounting_balance_mean_tco2_yr"].notna()),
        ("NCW accounting balance 2024", "ncw_accounting_balance_mean_tco2_yr", "tCO2/yr", master["ncw_accounting_balance_mean_tco2_yr"].notna()),
        ("Lost annual forest addition capacity", "loss_tco2_mean", "tCO2/yr", master["reported_deforestation"] & master["loss_tco2_mean"].gt(0)),
        ("Relative forest-capacity erosion", "erosion_pct_of_gcw", "% of GCW", master["reported_deforestation"] & master["loss_tco2_mean"].gt(0)),
        ("Ibrahim 2% GCW allocation", "ibrahim_2pct_usd2015_yr", "US$2015/yr", master["has_gcw"]),
    ]
    ranking_rows = []
    for metric, column, unit, mask in ranking_specs:
        ranked = master.loc[mask, ["iso3", "name", "continent", "groups", column]].dropna(subset=[column])
        ranked = ranked.sort_values(column, ascending=False).head(10)
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            ranking_rows.append(
                {
                    "metric": metric,
                    "rank_descending": rank,
                    "iso3": row.iso3,
                    "name": row.name,
                    "continent": row.continent,
                    "group": row.groups,
                    "value": float(getattr(row, column)),
                    "unit": unit,
                }
            )
    national_rankings = pd.DataFrame(ranking_rows)
    national_rankings.to_csv(out / "Supplementary_national_top10_2024.csv", index=False)

    # Busch categories are a separate, exhaustive classification of 105 positive-loss cases.
    busch_status = inputs["busch_status"].copy()
    if int(busch_status["countries"].sum()) != len(inputs["busch_units"]):
        raise ValueError("Busch status categories do not form an exhaustive disjoint partition of the positive-loss sample")
    status_labels = {
        "no_country_curve_in_published_table": "No country curve in published table",
        "target_exceeds_published_supply_at_100": "Target exceeds published supply at $100/tCO2",
        "target_within_positive_price_curve": "Target within positive-price range",
        "target_within_supply_at_nonpositive_price": "Above -$20 and at or below $0/tCO2",
        "target_within_supply_at_or_below_minus20": "At or below -$20/tCO2",
    }
    busch_status["category"] = busch_status["status"].map(status_labels).fillna(busch_status["status"])
    busch_status = busch_status.rename(
        columns={
            "countries": "units",
            "lost_capacity_tco2_yr": "reported_loss_capacity_tco2_yr",
            "target_discounted_30yr_tco2": "target_discounted_30yr_tco2",
        }
    )
    busch_status.to_csv(out / "Supplementary_Busch_action_cost_coverage.csv", index=False)
    inputs["busch_units"].to_csv(out / "Supplementary_Busch_action_cost_by_unit.csv", index=False)

    # Retain all competing specifications until the researcher validates selection.
    spatial_evidence = inputs["spatial_evidence"]
    spatial_coefficients = inputs["spatial_coefficients"]
    spatial_evidence.to_csv(out / "Supplementary_spatial_model_selection_evidence.csv", index=False)
    spatial_coefficients.to_csv(out / "Supplementary_spatial_coefficients_all_candidates.csv", index=False)

    tables = {
        "Table 1": table1,
        "Table 2": table2,
        "Table 3": table3,
        "Table 4": table4,
        "Table S1 - Forest biome additions": paper_s1,
        "Continent profiles 2024": continent_table,
        "Account concentration 2024": distribution_table,
        "GCW/GDP group tests 2024": pd.DataFrame(pairwise_rows),
        "National top-ten rankings 2024": national_rankings,
        "Country-level accounts 2024": country,
        "Mangrove reconciliation": mangrove,
        "Forest biome accounting": s1,
        "Pan rate comparison": pan_merge,
        "Accounting balance transitions": transition_table,
        "Deforestation scenarios": scenarios,
        "Busch coverage": busch_status,
        "Spatial selection evidence": spatial_evidence,
        "Spatial selection dossier": pd.read_csv(out / "Supplementary_spatial_selection_dossier.csv"),
        "Standardized spatial candidate coefficients": pd.read_csv(out / "Supplementary_spatial_candidate_standardized_coefficients.csv"),
    }
    return tables


def load_world(root: Path) -> gpd.GeoDataFrame:
    boundary = root / "data" / "raw" / "geospatial" / "boundaries" / "ne_50m_admin_0_countries.zip"
    world = gpd.read_file(f"zip://{boundary.as_posix()}!ne_50m_admin_0_countries.shp")
    world["iso3"] = world["ADM0_A3"].replace(NE_TO_UNIT)
    world = world.dissolve("iso3", as_index=False)[["iso3", "geometry"]]
    world = world.loc[world["iso3"] != "ATA"].to_crs("+proj=robin")
    return world


def draw_map_base(ax: plt.Axes, world: gpd.GeoDataFrame) -> None:
    world.plot(ax=ax, color="#ECEFEC", edgecolor="white", linewidth=0.22)
    xmin, ymin, xmax, ymax = world.total_bounds
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_axis_off()


def map_join(world: gpd.GeoDataFrame, values: pd.DataFrame) -> gpd.GeoDataFrame:
    return world.merge(values, on="iso3", how="left", validate="one_to_one")


def build_figures(root: Path, inputs: dict[str, pd.DataFrame | np.ndarray]) -> list[Path]:
    """Render the three fully specified figures; gate Figure 4 on author selection."""
    figures_dir = root / "results" / "figures" / "manuscript"
    figures_dir.mkdir(parents=True, exist_ok=True)
    master = group_frame(inputs["master"])
    world = load_world(root)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    outputs: list[Path] = []

    # Figure 1: the 2024 GDP denominator is explicit and the >100% class is visible.
    map1 = master.loc[master["has_gcw"], ["iso3", "gcw_usd2015_yr_mean", "gdp_2015usd_2024"]].copy()
    map1["gcw_gdp_pct"] = 100 * map1["gcw_usd2015_yr_mean"] / map1["gdp_2015usd_2024"]
    map1 = map1[["iso3", "gcw_gdp_pct"]]
    geo1 = map_join(world, map1)
    edges = [0, 1, 5, 10, 25, 50, 100, np.inf]
    labels = ["0-1%", "1-5%", "5-10%", "10-25%", "25-50%", "50-100%", ">100%"]
    colors = ["#F0F7EC", "#D9EBCB", "#B8D9A7", "#88BE79", "#5B9E5A", "#337B43", "#15552F"]
    geo1["ratio_class"] = pd.cut(geo1["gcw_gdp_pct"], bins=edges, labels=labels, include_lowest=True)
    fig, ax = plt.subplots(figsize=(10, 5.3), layout="constrained")
    draw_map_base(ax, world)
    for label, color in zip(labels, colors):
        subset = geo1.loc[geo1["ratio_class"] == label]
        if not subset.empty:
            subset.plot(ax=ax, color=color, edgecolor="white", linewidth=0.2)
    missing = geo1.loc[geo1["gcw_gdp_pct"].isna()]
    if not missing.empty:
        missing.plot(ax=ax, color="#D5D8D7", edgecolor="white", linewidth=0.2)
    handles = [Patch(facecolor=c, label=l) for l, c in zip(labels, colors)]
    handles.append(Patch(facecolor="#D5D8D7", label="No GCW or 2024 GDP"))
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=4, frameon=False, fontsize=8)
    ax.set_title("GCW / GDP, 2024 (%; GDP in 2015 US$)", loc="left", fontweight="bold", pad=4)
    fig1 = figures_dir / "Figure1_GCW_relative_to_GDP_2024.png"
    fig.savefig(fig1, bbox_inches="tight")
    plt.close(fig)
    outputs.append(fig1)

    # Figure 2a: show composition only where both accounts are available.
    map2 = master[
        ["iso3", "has_gcw", "has_bcw", "gcw_usd2015_yr_mean", "bcw_usd2015_yr_mean", "ncw_usd2015_yr_mean"]
    ].copy()
    map2["gcw_share_pct"] = 100 * map2["gcw_usd2015_yr_mean"] / map2["ncw_usd2015_yr_mean"]
    geo2 = map_join(world, map2)
    has_gcw_map = geo2["has_gcw"].astype("boolean").fillna(False).astype(bool)
    has_bcw_map = geo2["has_bcw"].astype("boolean").fillna(False).astype(bool)
    both = has_gcw_map & has_bcw_map & geo2["gcw_share_pct"].notna()
    forest_only = has_gcw_map & ~has_bcw_map
    blue_only = ~has_gcw_map & has_bcw_map
    cmap = LinearSegmentedColormap.from_list("blue_to_green", ["#2878A5", "#F4F1D0", "#2E7D4F"])
    fig, (ax_map, ax_matrix) = plt.subplots(
        1, 2, figsize=(13, 5.8), gridspec_kw={"width_ratios": [1.65, 1]}, layout="constrained"
    )
    draw_map_base(ax_map, world)
    if forest_only.any():
        geo2.loc[forest_only].plot(ax=ax_map, color="#D2D4D4", edgecolor="white", linewidth=0.2)
    if blue_only.any():
        geo2.loc[blue_only].plot(ax=ax_map, color="#989E9D", edgecolor="white", linewidth=0.2)
    if both.any():
        geo2.loc[both].plot(
            ax=ax_map, column="gcw_share_pct", cmap=cmap, vmin=0, vmax=100,
            edgecolor="white", linewidth=0.2,
        )
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=0, vmax=100), cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax_map, orientation="horizontal", fraction=0.045, pad=0.035)
    cbar.set_label("GCW share of NCW among units with both accounts (%)")
    missing_handles = [
        Patch(facecolor="#D2D4D4", label="GCW available; BCW unavailable"),
        Patch(facecolor="#989E9D", label="BCW available; GCW unavailable"),
    ]
    ax_map.legend(handles=missing_handles, loc="lower left", bbox_to_anchor=(0.01, 0.01), frameon=True, fontsize=7)
    ax_map.set_title("a  Green-blue composition (n=175 with both accounts)", loc="left", fontweight="bold")

    # Figure 2b: 2 x 2 transition matrix on the 162-unit complete sample.
    common = inputs["balance"].merge(
        master[["iso3", "has_gcw", "has_bcw"]], on="iso3", how="left", validate="one_to_one"
    )
    common = common.loc[common["has_gcw"] & common["has_bcw"]].copy()
    n_before_pos = int((common["gcw_accounting_balance_mean_tco2_yr"] > 0).sum())
    n_after_pos = int((common["ncw_accounting_balance_mean_tco2_yr"] > 0).sum())
    n_pos_pos = int(((common["gcw_accounting_balance_mean_tco2_yr"] > 0) & (common["ncw_accounting_balance_mean_tco2_yr"] > 0)).sum())
    n_pos_nonpos = int(((common["gcw_accounting_balance_mean_tco2_yr"] > 0) & (common["ncw_accounting_balance_mean_tco2_yr"] <= 0)).sum())
    n_nonpos_pos = int(((common["gcw_accounting_balance_mean_tco2_yr"] <= 0) & (common["ncw_accounting_balance_mean_tco2_yr"] > 0)).sum())
    n_nonpos_nonpos = int(((common["gcw_accounting_balance_mean_tco2_yr"] <= 0) & (common["ncw_accounting_balance_mean_tco2_yr"] <= 0)).sum())
    matrix = np.array([[n_pos_pos, n_pos_nonpos], [n_nonpos_pos, n_nonpos_nonpos]])
    cell_colors = np.array([["#84B88B", "#E6B9B4"], ["#70B6B7", "#D6D8D7"]])
    ax_matrix.set_xlim(-0.5, 1.5)
    ax_matrix.set_ylim(1.5, -0.5)
    for i in range(2):
        for j in range(2):
            ax_matrix.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=cell_colors[i, j], edgecolor="white", lw=2))
            ax_matrix.text(j, i, f"{matrix[i, j]}", ha="center", va="center", fontsize=18, fontweight="bold")
    ax_matrix.set_xticks([0, 1], ["Positive", "Non-positive"])
    ax_matrix.set_yticks([0, 1], ["Positive", "Non-positive"])
    ax_matrix.set_xlabel("After adding marine carbon (NCW − emissions 2024)")
    ax_matrix.set_ylabel("Forest account (GCW − emissions 2024)")
    ax_matrix.set_title("b  Accounting-balance transitions (n=162)", loc="left", fontweight="bold")
    ax_matrix.tick_params(length=0)
    for spine in ax_matrix.spines.values():
        spine.set_visible(False)
    ax_matrix.text(
        0.5, -0.17,
        f"Positive: {n_before_pos} before, {n_after_pos} after.\n"
        "A country-boundary accounting comparison, not a climate-neutrality test.",
        transform=ax_matrix.transAxes, ha="center", va="top", fontsize=8,
    )
    fig2 = figures_dir / "Figure2_marine_composition_and_balance_transitions.png"
    fig.savefig(fig2, bbox_inches="tight")
    plt.close(fig)
    outputs.append(fig2)

    # Figure 3: map of relative erosion and descriptive GCW-erosion scatter.
    erosion = master.loc[
        master["has_gcw"],
        ["iso3", "groups", "gcw_usd2015_yr_mean", "reported_deforestation", "loss_tco2_mean", "loss_value_usd2015_yr_mean", "erosion_pct_of_gcw"],
    ].copy()
    geo3 = map_join(world, erosion)
    reported = geo3["reported_deforestation"].astype("boolean").fillna(False).astype(bool)
    zero = reported & geo3["loss_tco2_mean"].fillna(0).le(0)
    positive = reported & geo3["loss_tco2_mean"].gt(0) & geo3["erosion_pct_of_gcw"].gt(0)
    missing = ~reported
    positive_values = geo3.loc[positive, "erosion_pct_of_gcw"].dropna()
    vmin = max(float(positive_values.min()), 1e-4)
    vmax = max(float(positive_values.max()), vmin * 1.01)
    norm = LogNorm(vmin=vmin, vmax=vmax)
    fig, (ax_map, ax_scatter) = plt.subplots(
        1, 2, figsize=(13, 5.7), gridspec_kw={"width_ratios": [1.25, 1]}, layout="constrained"
    )
    draw_map_base(ax_map, world)
    if missing.any():
        geo3.loc[missing].plot(ax=ax_map, color="#B9BDBB", edgecolor="white", linewidth=0.2)
    if zero.any():
        geo3.loc[zero].plot(ax=ax_map, color="#F3F0E8", edgecolor="white", linewidth=0.2)
    if positive.any():
        geo3.loc[positive].plot(
            ax=ax_map, column="erosion_pct_of_gcw", cmap="OrRd", norm=norm,
            edgecolor="white", linewidth=0.2,
        )
    map_sm = mpl.cm.ScalarMappable(norm=norm, cmap="OrRd")
    cbar = fig.colorbar(map_sm, ax=ax_map, orientation="horizontal", fraction=0.045, pad=0.035)
    cbar.set_label("Annual capacity loss as share of GCW (%) - logarithmic scale")
    ax_map.legend(
        handles=[
            Patch(facecolor="#B9BDBB", label="No FRA deforestation report"),
            Patch(facecolor="#F3F0E8", label="Reported; zero estimated loss"),
        ],
        loc="lower left", bbox_to_anchor=(0.01, 0.01), frameon=True, fontsize=7,
    )
    ax_map.set_title("a  Geographic intensity of forest-capacity erosion", loc="left", fontweight="bold")

    scatter = erosion.loc[
        erosion["reported_deforestation"].fillna(False)
        & erosion["loss_tco2_mean"].gt(0)
        & erosion["gcw_usd2015_yr_mean"].gt(0)
        & erosion["erosion_pct_of_gcw"].gt(0)
    ].copy()
    for group, subset in scatter.groupby("groups", dropna=False):
        label = group if pd.notna(group) else "Unclassified"
        ax_scatter.scatter(
            subset["gcw_usd2015_yr_mean"] / 1e9,
            subset["erosion_pct_of_gcw"],
            s=22,
            alpha=0.72,
            label=label,
            color=GROUP_COLORS.get(label, "#858585"),
            edgecolor="white",
            linewidth=0.25,
        )
    median_gcw = float(scatter["gcw_usd2015_yr_mean"].median() / 1e9)
    median_erosion = float(scatter["erosion_pct_of_gcw"].median())
    ax_scatter.axvline(median_gcw, color="#555555", ls="--", lw=0.8)
    ax_scatter.axhline(median_erosion, color="#555555", ls="--", lw=0.8)
    ax_scatter.set_xscale("log")
    ax_scatter.set_yscale("log")
    ax_scatter.set_xlabel("GCW (billion US$2015/year)")
    ax_scatter.set_ylabel("Annual lost addition capacity (% of GCW)")
    ax_scatter.set_title(f"b  GCW and relative erosion (n={len(scatter)})", loc="left", fontweight="bold")
    ax_scatter.grid(alpha=0.2, which="both")
    ax_scatter.legend(frameon=False, fontsize=7, loc="upper left")
    ax_scatter.text(
        0.98, 0.02,
        "Descriptive association; erosion ratio includes GCW in its denominator.",
        transform=ax_scatter.transAxes, ha="right", va="bottom", fontsize=7,
    )
    fig3 = figures_dir / "Figure3_forest_capacity_erosion.png"
    fig.savefig(fig3, bbox_inches="tight")
    plt.close(fig)
    outputs.append(fig3)

    # Figure 4 is generated only from the researcher's completed decision file.
    selection_file = root / "results" / "validation" / "manuscript_spatial_model_selection.csv"
    status_path = figures_dir / "Figure4_spatial_associations_status.json"
    evidence = inputs["spatial_evidence"]
    selected_count = int(as_bool(evidence["final_model_selected"]).sum())
    figure4: Path | None = None
    status = "pending_researcher_model_selection"
    reason = (
        "No final model/weight choices have been supplied. The selection dossier reports "
        "all diagnostics and candidate fits; the researcher must complete the decision template."
    )
    if selection_file.exists():
        selection = pd.read_csv(selection_file)
        require_columns(selection, ["outcome", "specification", "weight", "model"], selection_file.name)
        required_outcomes = {
            "lost_capacity_mtco2_yr", "erosion_pct_of_gcw", "gcw_gdp_pct_2024"
        }
        if (
            len(selection) == 3
            and set(selection["outcome"]) == required_outcomes
            and selection["specification"].eq("baseline_2024_same_sample").all()
            and selection["model"].isin({"OLS", "SAR", "SEM", "SDM", "SDEM", "GNS"}).all()
            and selection["weight"].isin({"queen_contiguity", "symmetric_knn5"}).all()
        ):
            standardized_path = root / "results" / "tables" / "manuscript" / "Supplementary_spatial_candidate_standardized_coefficients.csv"
            if standardized_path.exists():
                candidate_coefficients = pd.read_csv(standardized_path)
                chosen_rows = []
                for row in selection.itertuples(index=False):
                    selected_coefficients = candidate_coefficients.loc[
                        candidate_coefficients["specification"].eq(row.specification)
                        & candidate_coefficients["outcome"].eq(row.outcome)
                        & candidate_coefficients["weight"].eq(row.weight)
                        & candidate_coefficients["model"].eq(row.model)
                    ].copy()
                    if selected_coefficients.empty:
                        chosen_rows = []
                        break
                    chosen_rows.append(selected_coefficients)
                if chosen_rows:
                    chosen = pd.concat(chosen_rows, ignore_index=True)
                    outcome_order = {
                        "lost_capacity_mtco2_yr": 0,
                        "erosion_pct_of_gcw": 1,
                        "gcw_gdp_pct_2024": 2,
                    }
                    outcome_colors = {
                        "lost_capacity_mtco2_yr": "#D55E00",
                        "erosion_pct_of_gcw": "#0072B2",
                        "gcw_gdp_pct_2024": "#009E73",
                    }
                    fig, ax = plt.subplots(figsize=(10.2, 5.4))
                    ylabels = {
                        1: "GDP per capita · unit",
                        2: "Forest area · unit",
                        3: "Warm-biome share · unit",
                        4: "GDP per capita · neighbours",
                        5: "Forest area · neighbours",
                        6: "Warm-biome share · neighbours",
                    }
                    offsets = {
                        "lost_capacity_mtco2_yr": -0.16,
                        "erosion_pct_of_gcw": 0.0,
                        "gcw_gdp_pct_2024": 0.16,
                    }
                    for outcome, group in chosen.groupby("outcome", sort=False):
                        for estimate in group.itertuples(index=False):
                            y = estimate.term_order + offsets[outcome]
                            ax.errorbar(
                                estimate.standardized_coefficient,
                                y,
                                xerr=[[estimate.standardized_coefficient - estimate.ci95_low],
                                      [estimate.ci95_high - estimate.standardized_coefficient]],
                                fmt="o",
                                color=outcome_colors[outcome],
                                markersize=5,
                                capsize=2.5,
                                linewidth=1.15,
                                label=estimate.outcome_label if estimate.term_order == 1 else None,
                            )
                    ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--")
                    ax.axhline(3.5, color="#B8B8B8", linewidth=0.8)
                    ax.set_yticks(list(ylabels), [ylabels[i] for i in ylabels])
                    ax.invert_yaxis()
                    ax.set_xlabel("Standardized coefficient (95% Wald interval)")
                    ax.set_title("Estimated associations in the three baseline relations", loc="left", fontweight="bold")
                    ax.text(
                        0,
                        1.02,
                        "Standardized as β × SD(X or WX) / SD(log1p(Y)); controls and model/weight choices in Supplementary Table S5",
                        transform=ax.transAxes,
                        ha="left",
                        va="bottom",
                        fontsize=8,
                    )
                    ax.legend(frameon=False, loc="lower right", fontsize=8)
                    ax.grid(axis="x", color="#E5E5E5", linewidth=0.6)
                    fig4 = figures_dir / "Figure4_spatial_associations.png"
                    fig.savefig(fig4, bbox_inches="tight")
                    plt.close(fig)
                    outputs.append(fig4)
                    figure4 = fig4
                    status = "ready_after_researcher_model_selection"
                    reason = "Figure generated from the completed researcher decision file and standardized candidate coefficient table."
                else:
                    status = "invalid_model_selection_manifest"
                    reason = "At least one chosen model has no valid standardized coefficient rows in the candidate table."
            else:
                status = "missing_standardized_candidate_coefficients"
                reason = "Run the manuscript-table workflow to build the standardized candidate coefficient table."
        else:
            status = "invalid_model_selection_manifest"
    status_path.write_text(
        json.dumps(
            {
                "status": status,
                "figure": "Figure 4 - coefficient plot for three selected spatial relationships",
                "generated_file": figure4.name if figure4 else None,
                "candidate_contexts": int(len(evidence)),
                "contexts_flagged_selected_in_source": selected_count,
                "selection_manifest_expected": "results/validation/manuscript_spatial_model_selection.csv",
                "decision_template": "results/validation/spatial_model_decision_template.csv",
                "reason": reason,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tables-only", action="store_true", help="Write tables only.")
    mode.add_argument("--figures-only", action="store_true", help="Write figures only.")
    args = parser.parse_args()
    root = repository_root()
    from build_spatial_selection_review import build_selection_review

    build_selection_review(root)
    inputs = load_inputs(root)
    counts = validate_samples(inputs)
    if not args.figures_only:
        tables = build_tables(root, inputs)
        print(f"Wrote {len(tables)} main and supplementary table sets to {root / 'results' / 'tables' / 'manuscript'}")
    if not args.tables_only:
        figures = build_figures(root, inputs)
        print("Wrote current figures:")
        for path in figures:
            print(f"  {path.name}")
        status = json.loads((root / "results" / "figures" / "manuscript" / "Figure4_spatial_associations_status.json").read_text(encoding="utf-8"))
        if status["status"] != "ready_after_researcher_model_selection":
            print("Figure 4 awaits the human model/weight choices in results/validation/spatial_model_decision_template.csv.")
    print("Validated samples:", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
