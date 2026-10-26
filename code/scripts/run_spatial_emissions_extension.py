"""Run the full exploratory spatial sequence with 2024 emissions and controls.

The three prior outcomes are re-run with 2024 socioeconomic controls on a common
complete-case sample, then with 2024 fossil/industrial CO2 added as an X variable.
2024 emissions are also analysed as Y. All outcomes remain cross-sectional and
associational; the script does not estimate causal effects or choose a winner.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from libpysal.weights import W
from scipy.stats import chi2
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import run_spatial_full_sequence as spatial  # noqa: E402


OUT = ROOT / "results" / "validation"
DATE = "2026-10-23"


def _load_2024_data() -> tuple[pd.DataFrame, gpd.GeoDataFrame, list[str]]:
    data, geometries, missing_geometry = spatial._prepare_data()
    socio = pd.read_csv(ROOT / "data" / "derived" / "socioeconomic_2024_by_unit.csv")
    socio = socio.set_index("iso3")
    data = data.drop(columns=["gdp", "population"], errors="ignore")
    data = data.join(socio[[
        "population_2024", "gdp_2015usd_2024", "gdp_per_capita_2024",
        "co2_emissions_tco2_2024",
    ]], how="left")
    data["emissions_mtco2_yr_2024"] = data["co2_emissions_tco2_2024"] / 1e6
    data["gcw_gdp_pct_2024"] = 100 * data["gcw_usd2015_yr_mean"] / data["gdp_2015usd_2024"]
    data["ln_gdp_per_capita_2024"] = np.log(data["gdp_per_capita_2024"])
    data["ln_population_2024"] = np.log(data["population_2024"])
    data["ln_emissions_mtco2_2024"] = np.log1p(data["emissions_mtco2_yr_2024"])
    data["ln_forest_area_mha"] = np.log1p(data["forest_area_ha"] / 1e6)
    for outcome in ("lost_capacity_mtco2_yr", "erosion_pct_of_gcw", "gcw_gdp_pct_2024"):
        if data[outcome].dropna().lt(0).any():
            raise ValueError(f"log1p predictor {outcome} contains negative values")
        data[f"log1p_{outcome}"] = np.log1p(data[outcome])
    return data, geometries, missing_geometry


def _matched_sample(
    data: pd.DataFrame,
    outcome: str,
    required_predictors: list[str],
    needs_deforestation_report: bool,
) -> pd.DataFrame:
    columns = [outcome, *required_predictors]
    if needs_deforestation_report:
        columns.append("reported_deforestation")
    sample = data.loc[:, columns].replace([np.inf, -np.inf], np.nan).dropna().copy()
    if needs_deforestation_report:
        sample = sample.loc[sample["reported_deforestation"].astype(bool)].copy()
    return sample


def _holm(frame: pd.DataFrame, p_column: str, group_columns: list[str]) -> pd.Series:
    adjusted = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, indices in frame.groupby(group_columns, dropna=False).groups.items():
        pvalues = frame.loc[indices, p_column].to_numpy(dtype=float)
        valid = np.isfinite(pvalues)
        if valid.any():
            adjusted.loc[np.asarray(indices)[valid]] = multipletests(pvalues[valid], method="holm")[1]
    return adjusted


def _nested_block_tests(fits: pd.DataFrame) -> pd.DataFrame:
    """Compare matched nested specifications for the same outcome/weight/model."""
    comparisons = [
        ("emissions_as_x", "baseline_2024_same_sample", "add_emissions_2024_as_x"),
        ("population_as_x_sensitivity", "emissions_2024_as_y", "emissions_2024_as_y_plus_population_sensitivity"),
        ("lost_capacity_as_x", "emissions_y_baseline_matched_lost_capacity", "emissions_2024_as_y_plus_lost_capacity_x"),
        ("erosion_as_x", "emissions_y_baseline_matched_erosion", "emissions_2024_as_y_plus_erosion_x"),
        ("gcw_gdp_as_x", "emissions_y_baseline_matched_gcw_gdp", "emissions_2024_as_y_plus_gcw_gdp_x"),
    ]
    rows = []
    for block, restricted_spec, unrestricted_spec in comparisons:
        restricted = fits.loc[fits["specification"].eq(restricted_spec)]
        unrestricted = fits.loc[fits["specification"].eq(unrestricted_spec)]
        keys = ["outcome", "weight", "model"]
        joined = restricted.merge(
            unrestricted,
            on=keys,
            suffixes=("_restricted", "_unrestricted"),
            validate="one_to_one",
        )
        for _, row in joined.iterrows():
            df = int(row["n_parameters_unrestricted"] - row["n_parameters_restricted"])
            raw = 2 * (float(row["log_likelihood_unrestricted"]) - float(row["log_likelihood_restricted"]))
            status = "ok" if df > 0 and raw >= -1e-5 else "nested-fit check failed"
            statistic = max(raw, 0.0) if status == "ok" else raw
            rows.append({
                "block_test": block,
                "outcome": row["outcome"],
                "weight": row["weight"],
                "model": row["model"],
                "restricted_specification": restricted_spec,
                "unrestricted_specification": unrestricted_spec,
                "n": int(row["n_restricted"]),
                "df": df,
                "lr_statistic": statistic,
                "p_value": float(chi2.sf(statistic, df)) if status == "ok" else np.nan,
                "delta_log_likelihood": float(row["log_likelihood_unrestricted"] - row["log_likelihood_restricted"]),
                "delta_aic": float(row["aic_unrestricted"] - row["aic_restricted"]),
                "delta_bic": float(row["bic_unrestricted"] - row["bic_restricted"]),
                "test_status": status,
            })
    result = pd.DataFrame(rows)
    result["p_holm_within_block_model"] = _holm(result, "p_value", ["block_test", "model"])
    return result


def _predictor_diagnostics(
    data: pd.DataFrame,
    base_predictors: list[str],
    emissions_predictor: str,
    outcome_map: dict[str, bool],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    correlation_rows, vif_rows = [], []
    for outcome, needs_report in outcome_map.items():
        diagnostics = [(f"{outcome}_with_emissions_x", [*base_predictors, emissions_predictor], needs_report)]
        diagnostics.append((
            f"emissions_y_with_{outcome}_x",
            [*base_predictors, f"log1p_{outcome}"],
            False,
        ))
        for specification, predictors, use_report_filter in diagnostics:
            sample = _matched_sample(data, outcome if use_report_filter else "emissions_mtco2_yr_2024", predictors, use_report_filter)
            corr = sample[predictors].corr(method="pearson")
            for left_index, left in enumerate(predictors):
                for right in predictors[left_index + 1:]:
                    correlation_rows.append({
                        "specification": specification,
                        "outcome_sample": outcome if use_report_filter else "emissions_mtco2_yr_2024",
                        "n": len(sample),
                        "predictor_1": left,
                        "predictor_2": right,
                        "pearson_r": float(corr.loc[left, right]),
                    })
            x = sm.add_constant(sample[predictors].to_numpy(dtype=float), has_constant="add")
            for idx, name in enumerate(["constant", *predictors]):
                try:
                    value = float(variance_inflation_factor(x, idx))
                except (ValueError, np.linalg.LinAlgError, ZeroDivisionError):
                    value = float("inf")
                if name != "constant":
                    vif_rows.append({
                        "specification": specification,
                        "outcome_sample": outcome if use_report_filter else "emissions_mtco2_yr_2024",
                        "n": len(sample),
                        "predictor": name,
                        "vif": value,
                    })
    return pd.DataFrame(correlation_rows), pd.DataFrame(vif_rows)


def _accounting_balance_2024(socio: pd.DataFrame) -> dict:
    """Re-evaluate descriptive GCW/NCW accounting balances with 2024 emissions."""
    gcw_archive = np.load(ROOT / "results" / "draws" / "gcw_draws.npz", allow_pickle=True)
    ncw_archive = np.load(ROOT / "results" / "draws" / "ncw_draws.npz", allow_pickle=True)
    # The combined archive stores the aligned GCW and NCW draws; the standalone
    # GCW archive is used only for the matching GSCC draw vector.
    units = ncw_archive["iso3"].astype(str)
    gcw_draws = ncw_archive["gcw_usd2015_yr"].astype(float)
    gscc = gcw_archive["gscc"].astype(float)
    ncw_draws = ncw_archive["ncw_usd2015_yr"].astype(float)
    if gcw_draws.shape[1] != len(gscc) or ncw_draws.shape[1] != len(gscc):
        raise ValueError("GSCC draw count does not align with wealth draw arrays")

    emissions_map = socio.set_index("iso3")["co2_emissions_tco2_2024"]
    emissions = emissions_map.reindex(units).to_numpy(dtype=float)
    covered = np.isfinite(emissions)
    gcw_balance = gcw_draws[covered] / gscc - emissions[covered, None]
    ncw_balance = ncw_draws[covered] / gscc - emissions[covered, None]
    base = pd.read_csv(ROOT / "results" / "country_level_gcw.csv").set_index("iso3")
    ncw_base = pd.read_csv(ROOT / "results" / "country_level_ncw.csv").set_index("iso3")
    details = pd.DataFrame({
        "iso3": units[covered],
        "co2_emissions_tco2_2024": emissions[covered],
        "gcw_additions_tco2_yr": base.reindex(units[covered])["uptake_tco2_yr_mean"].to_numpy(dtype=float),
        "gcw_accounting_balance_mean_tco2_yr": np.mean(gcw_balance, axis=1),
        "gcw_accounting_balance_p05_tco2_yr": np.percentile(gcw_balance, 5, axis=1),
        "gcw_accounting_balance_p50_tco2_yr": np.percentile(gcw_balance, 50, axis=1),
        "gcw_accounting_balance_p95_tco2_yr": np.percentile(gcw_balance, 95, axis=1),
        "ncw_accounting_balance_mean_tco2_yr": np.mean(ncw_balance, axis=1),
        "ncw_accounting_balance_p05_tco2_yr": np.percentile(ncw_balance, 5, axis=1),
        "ncw_accounting_balance_p50_tco2_yr": np.percentile(ncw_balance, 50, axis=1),
        "ncw_accounting_balance_p95_tco2_yr": np.percentile(ncw_balance, 95, axis=1),
    })
    details = details.merge(
        base.reset_index()[["iso3", "name", "continent", "fra_region", "groups"]],
        on="iso3", how="left", validate="one_to_one",
    )
    details["gcw_additions_to_emissions_ratio"] = details["gcw_additions_tco2_yr"] / details["co2_emissions_tco2_2024"]
    details.to_csv(OUT / "emissions_2024_accounting_balance_by_unit.csv", index=False)

    group_rows = []
    for dimension in ("continent", "groups"):
        for label, part in details.groupby(dimension, dropna=False):
            group_rows.append({
                "dimension": dimension,
                "group": label,
                "units_with_emissions": int(len(part)),
                "emissions_sum_tco2_yr": float(part["co2_emissions_tco2_2024"].sum()),
                "gcw_uptake_sum_tco2_yr": float(part["gcw_additions_tco2_yr"].sum()),
                "positive_gcw_accounting_balance_units": int(part["gcw_accounting_balance_mean_tco2_yr"].gt(0).sum()),
                "positive_ncw_accounting_balance_units": int(part["ncw_accounting_balance_mean_tco2_yr"].gt(0).sum()),
            })
    pd.DataFrame(group_rows).to_csv(OUT / "emissions_2024_accounting_balance_groups.csv", index=False)
    summary = {
        "units_with_emissions": int(len(details)),
        "units_with_gcw_account_balance": int(np.isfinite(gcw_balance).all(axis=1).sum()),
        "units_with_ncw_account_balance": int(np.isfinite(ncw_balance).all(axis=1).sum()),
        "gcb_emissions_sum_covered_units_tco2_yr": float(details["co2_emissions_tco2_2024"].sum()),
        "gcw_gross_additions_sum_covered_units_tco2_yr": float(details["gcw_additions_tco2_yr"].sum()),
        "gcw_accounting_balance_positive_units": int(details["gcw_accounting_balance_mean_tco2_yr"].gt(0).sum()),
        "ncw_accounting_balance_positive_units": int(details["ncw_accounting_balance_mean_tco2_yr"].gt(0).sum()),
        "gcw_accounting_balance_world_sum_tco2_yr": float(details["gcw_accounting_balance_mean_tco2_yr"].sum()),
        "ncw_accounting_balance_world_sum_tco2_yr": float(details["ncw_accounting_balance_mean_tco2_yr"].sum()),
        "uncertainty_scope": "Percentiles propagate the existing GSCC/wealth draws only; 2024 emissions are held fixed.",
        "interpretation_note": "This is a country-boundary accounting comparison, not a national climate-neutrality test or an estimate of total net ecosystem emissions.",
    }
    (OUT / "emissions_2024_accounting_balance_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def _run_one(
    sample: pd.DataFrame,
    outcome: str,
    specification: str,
    predictor_names: list[str],
    full_weights: dict[str, W],
    seed_offset: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    y_raw = sample[outcome].to_numpy(dtype=float)
    if np.any(y_raw < 0):
        raise ValueError(f"log1p outcome {outcome} contains negative values")
    y = np.log1p(y_raw).reshape(-1, 1)
    x = sample[predictor_names].to_numpy(dtype=float)
    ids = sample.index.tolist()
    moran_rows, lm_rows, fit_rows, coefficient_rows, lr_rows = [], [], [], [], []

    for weight_index, (weight_name, full_weight) in enumerate(full_weights.items()):
        weight = spatial._weight_subsample(full_weight, ids)
        ols_hc3 = sm.OLS(y, sm.add_constant(x, has_constant="add")).fit(cov_type="HC3")
        for measure, values in (("y_log1p", y.ravel()), ("ols_residual", np.asarray(ols_hc3.resid).ravel())):
            moran_rows.append({
                "specification": specification,
                "outcome": outcome,
                "weight": weight_name,
                "measure": measure,
                "n": len(sample),
                "islands": len(weight.islands),
                "components": len(set(weight.component_labels)),
                **spatial._moran(values, weight, spatial.SEED + seed_offset + weight_index),
            })
        for row in spatial._step2_lm(y, x, weight, outcome, weight_name, len(sample)):
            lm_rows.append({"specification": specification, **row})

        fits = {
            name: spatial._fit_spatial_mle(y, x, weight, name, predictor_names)
            for name in spatial.MODEL_FLAGS
        }
        for model_name, fit in fits.items():
            fit_rows.append({
                "specification": specification,
                "outcome": outcome,
                "weight": weight_name,
                "model": model_name,
                "n": fit["n"],
                "log_likelihood": fit["log_likelihood"],
                "aic": fit["aic"],
                "bic": fit["bic"],
                "n_parameters": fit["n_parameters"],
                "rho": fit["rho"],
                "lambda": fit["lambda"],
                "sigma2": fit["sigma2"],
                "optimizer_success": fit["optimizer_success"],
                "optimizer_message": fit["optimizer_message"],
                "covariance_status": fit["covariance_status"],
            })
            for estimate in fit["estimates"]:
                coefficient_rows.append({
                    "specification": specification,
                    "outcome": outcome,
                    "weight": weight_name,
                    "model": model_name,
                    "n": fit["n"],
                    **estimate,
                    "optimizer_success": fit["optimizer_success"],
                    "covariance_status": fit["covariance_status"],
                })
        for comparison, restricted, unrestricted in (
            ("SDM_vs_SAR", "SAR", "SDM"),
            ("SDEM_vs_SEM", "SEM", "SDEM"),
            ("GNS_vs_SDM", "SDM", "GNS"),
        ):
            lr_rows.append({
                "specification": specification,
                "outcome": outcome,
                "weight": weight_name,
                "comparison": comparison,
                "restricted_model": restricted,
                "unrestricted_model": unrestricted,
                "n": len(sample),
                **spatial._lr_test(fits[restricted], fits[unrestricted]),
            })
    return moran_rows, lm_rows, fit_rows, coefficient_rows, lr_rows


def _self_test() -> dict:
    """Small synthetic checks for sample matching and log transforms."""
    frame = pd.DataFrame({
        "y": [1.0, 2.0, 3.0, 4.0],
        "x1": [2.0, 3.0, 4.0, 5.0],
        "emissions": [10.0, np.nan, 30.0, 40.0],
        "reported_deforestation": [True, True, False, True],
    }, index=["A", "B", "C", "D"])
    base = _matched_sample(frame, "y", ["x1", "emissions"], True)
    assert list(base.index) == ["A", "D"]
    assert np.allclose(np.log1p([1.0, 2.0]), [np.log(2), np.log(3)])
    return {"status": "passed", "matched_sample_iso3": list(base.index), "n": len(base)}


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    data, geometries, missing_geometry = _load_2024_data()
    full_weights = spatial._build_weights(geometries)

    base_predictors = ["ln_gdp_per_capita_2024", "ln_forest_area_mha", "warm_biome_share"]
    emissions_predictor = "ln_emissions_mtco2_2024"
    outcome_map = {
        "lost_capacity_mtco2_yr": True,
        "erosion_pct_of_gcw": True,
        "gcw_gdp_pct_2024": False,
    }
    case_specs = []
    sample_rows = []
    seed = 0

    # Matched 2024 baselines and 2024 emissions-X additions for the three prior outcomes.
    for outcome, needs_deforestation in outcome_map.items():
        matched = _matched_sample(data, outcome, [*base_predictors, emissions_predictor], needs_deforestation)
        for specification, predictors in (
            ("baseline_2024_same_sample", base_predictors),
            ("add_emissions_2024_as_x", [*base_predictors, emissions_predictor]),
        ):
            case_specs.append((matched, outcome, specification, predictors, needs_deforestation))
            sample_rows.append({
                "specification": specification,
                "outcome": outcome,
                "n": len(matched),
                "geometry_units": len(data),
                "reported_deforestation_complete_cases_only": needs_deforestation,
                "zero_values_y": int(matched[outcome].eq(0).sum()),
                "y_transform": "log1p",
                "predictors": ";".join(predictors),
                "matched_sample_hash_codes": ";".join(matched.index.astype(str)),
            })

    # Emissions as Y: keep the base-controls model and population sensitivity as
    # auxiliary references, then add each prior outcome as a separate X. Each
    # extension is compared with its own same-sample reduced model for LR tests.
    emissions_outcome = "emissions_mtco2_yr_2024"
    matched_emissions = _matched_sample(data, emissions_outcome, [*base_predictors, "ln_population_2024"], False)
    for specification, predictors in (
        ("emissions_2024_as_y", base_predictors),
        ("emissions_2024_as_y_plus_population_sensitivity", [*base_predictors, "ln_population_2024"]),
    ):
        case_specs.append((matched_emissions, emissions_outcome, specification, predictors, False))
        sample_rows.append({
            "specification": specification,
            "outcome": emissions_outcome,
            "n": len(matched_emissions),
            "geometry_units": len(data),
            "reported_deforestation_complete_cases_only": False,
            "zero_values_y": int(matched_emissions[emissions_outcome].eq(0).sum()),
            "y_transform": "log1p",
            "predictors": ";".join(predictors),
            "matched_sample_hash_codes": ";".join(matched_emissions.index.astype(str)),
        })

    emissions_y_extensions = {
        "lost_capacity_mtco2_yr": "emissions_2024_as_y_plus_lost_capacity_x",
        "erosion_pct_of_gcw": "emissions_2024_as_y_plus_erosion_x",
        "gcw_gdp_pct_2024": "emissions_2024_as_y_plus_gcw_gdp_x",
    }
    for prior_outcome, specification in emissions_y_extensions.items():
        added_predictor = f"log1p_{prior_outcome}"
        predictors = [*base_predictors, added_predictor]
        matched = _matched_sample(data, emissions_outcome, predictors, False)
        baseline_specification = {
            "lost_capacity_mtco2_yr": "emissions_y_baseline_matched_lost_capacity",
            "erosion_pct_of_gcw": "emissions_y_baseline_matched_erosion",
            "gcw_gdp_pct_2024": "emissions_y_baseline_matched_gcw_gdp",
        }[prior_outcome]
        for spec, selected_predictors in (
            (baseline_specification, base_predictors),
            (specification, predictors),
        ):
            case_specs.append((matched, emissions_outcome, spec, selected_predictors, False))
            sample_rows.append({
                "specification": spec,
                "outcome": emissions_outcome,
                "added_outcome_as_predictor": prior_outcome if spec == specification else "",
                "n": len(matched),
                "geometry_units": len(data),
                "reported_deforestation_complete_cases_only": False,
                "zero_values_y": int(matched[emissions_outcome].eq(0).sum()),
                "y_transform": "log1p",
                "predictors": ";".join(selected_predictors),
                "matched_sample_hash_codes": ";".join(matched.index.astype(str)),
            })

    moran_rows, lm_rows, fit_rows, coefficient_rows, lr_rows = [], [], [], [], []
    for matched, outcome, specification, predictors, _ in case_specs:
        m, lm, fits, coefficients, lrs = _run_one(
            matched, outcome, specification, predictors, full_weights, seed
        )
        moran_rows.extend(m)
        lm_rows.extend(lm)
        fit_rows.extend(fits)
        coefficient_rows.extend(coefficients)
        lr_rows.extend(lrs)
        seed += 100

    moran = pd.DataFrame(moran_rows)
    moran["p_holm_within_specification_measure"] = _holm(
        moran, "p_permutation_two_sided", ["specification", "measure"]
    )
    lms = pd.DataFrame(lm_rows)
    lms["p_holm_within_specification_test"] = _holm(lms, "p_value", ["specification", "test"])
    lrs = pd.DataFrame(lr_rows)
    lrs["p_holm_within_specification_comparison"] = _holm(lrs, "p_value", ["specification", "comparison"])
    fits = pd.DataFrame(fit_rows)
    fits["aic_rank"] = fits.groupby(["specification", "outcome", "weight"])["aic"].rank(method="min").astype(int)
    fits["bic_rank"] = fits.groupby(["specification", "outcome", "weight"])["bic"].rank(method="min").astype(int)
    block_tests = _nested_block_tests(fits)
    correlations, vifs = _predictor_diagnostics(data, base_predictors, emissions_predictor, outcome_map)

    moran.to_csv(OUT / "spatial_emissions_2024_step1_moran.csv", index=False)
    lms.to_csv(OUT / "spatial_emissions_2024_step2_lm_tests.csv", index=False)
    lrs.to_csv(OUT / "spatial_emissions_2024_step3_nested_tests.csv", index=False)
    fits.to_csv(OUT / "spatial_emissions_2024_model_fit.csv", index=False)
    pd.DataFrame(coefficient_rows).to_csv(OUT / "spatial_emissions_2024_model_coefficients.csv", index=False)
    pd.DataFrame(sample_rows).to_csv(OUT / "spatial_emissions_2024_sample_audit.csv", index=False)
    block_tests.to_csv(OUT / "spatial_emissions_2024_predictor_block_tests.csv", index=False)
    correlations.to_csv(OUT / "spatial_emissions_2024_predictor_correlations.csv", index=False)
    vifs.to_csv(OUT / "spatial_emissions_2024_predictor_vif.csv", index=False)

    # A compact, factual coefficient table to support inventory browsing.
    coefficient_frame = pd.DataFrame(coefficient_rows)
    coefficient_frame.loc[
        coefficient_frame["term"].isin([
            *base_predictors,
            emissions_predictor,
            "ln_population_2024",
            "log1p_lost_capacity_mtco2_yr",
            "log1p_erosion_pct_of_gcw",
            "log1p_gcw_gdp_pct_2024",
        ])
    ].to_csv(OUT / "spatial_emissions_2024_focus_coefficients.csv", index=False)
    balance_summary = _accounting_balance_2024(pd.read_csv(ROOT / "data" / "derived" / "socioeconomic_2024_by_unit.csv"))

    checks = {
        "date": DATE,
        "status": "complete",
        "geographic_units": int(len(data)),
        "units_without_geometry": missing_geometry,
        "spatial_weights": list(full_weights),
        "number_of_specification_outcome_weight_cases": int(len(case_specs) * len(full_weights)),
        "number_of_primary_relationship_profiles": 9,
        "number_of_primary_relationship_weight_cases": int(9 * len(full_weights)),
        "number_of_auxiliary_specification_weight_cases": int(2 * len(full_weights)),
        "number_of_matched_reference_weight_cases": int(3 * len(full_weights)),
        "number_of_requested_emissions_x_cases": int(3 * len(full_weights)),
        "number_of_requested_emissions_y_plus_prior_outcome_cases": int(3 * len(full_weights)),
        "number_of_emissions_y_base_auxiliary_cases": int(len(full_weights)),
        "number_of_additional_population_sensitivity_cases": int(len(full_weights)),
        "predictor_block_nested_tests": int(len(block_tests)),
        "model_fit_rows": int(len(fits)),
        "moran_rows": int(len(moran)),
        "lm_rows": int(len(lms)),
        "nested_lr_rows": int(len(lrs)),
        "permutations": spatial.PERMUTATIONS,
        "seeds": {"base": spatial.SEED, "step": 100},
        "model_families": list(spatial.MODEL_FLAGS),
        "p_value_adjustment": "Holm within each specification and diagnostic family, across that specification's outcome-weight cases",
        "same_sample_comparison": "For each of the three existing outcomes, baseline and add-emissions-X models use identical 2024 complete-case rows. Each emissions-Y plus prior-outcome-X model is compared with a reduced emissions-Y model on the exact same complete-case rows. The emissions-Y baseline and population sensitivity also use identical rows.",
        "predictors": {
            "base_2024": base_predictors,
            "emissions_added_as_x": emissions_predictor,
            "emissions_y_added_x_by_model": {
                "lost_capacity_mtco2_yr": "log1p_lost_capacity_mtco2_yr",
                "erosion_pct_of_gcw": "log1p_erosion_pct_of_gcw",
                "gcw_gdp_pct_2024": "log1p_gcw_gdp_pct_2024",
            },
            "emissions_y_population_sensitivity": "ln_population_2024 added to base controls",
        },
        "transform": "log1p for all four outcomes and for each prior outcome when used as an emissions-Y predictor; emissions X uses log1p(MtCO2/year); GDP per capita and forest area use natural logs",
        "interpretation_boundary": "Cross-sectional associations; no causal impact is estimated and the script does not select a preferred model.",
        "limitations": [
            "GCB emission values are mapped only where a country/territory row directly matches a study ISO3; parent-country totals are not copied to split territories.",
            "World Bank 2024 GDP/population coverage is incomplete; model samples are complete cases, not imputed.",
            "GDP-per-capita and GCW/GDP use WDI 2024 GDP and population; the ratio outcome uses 2024 GDP in constant 2015 US dollars.",
            "The GCB 2025 country series is a recent estimated emissions vintage; it is not a direct emissions-monitoring measure.",
            "Queen isolates are retained as zero-neighbour rows; kNN-5 links units to nearest representative points, sometimes across water.",
        ],
        "outputs": [
            "results/validation/spatial_emissions_2024_step1_moran.csv",
            "results/validation/spatial_emissions_2024_step2_lm_tests.csv",
            "results/validation/spatial_emissions_2024_step3_nested_tests.csv",
            "results/validation/spatial_emissions_2024_model_fit.csv",
            "results/validation/spatial_emissions_2024_model_coefficients.csv",
            "results/validation/spatial_emissions_2024_sample_audit.csv",
            "results/validation/spatial_emissions_2024_predictor_block_tests.csv",
            "results/validation/spatial_emissions_2024_predictor_correlations.csv",
            "results/validation/spatial_emissions_2024_predictor_vif.csv",
            "results/validation/emissions_2024_accounting_balance_by_unit.csv",
            "results/validation/emissions_2024_accounting_balance_groups.csv",
            "results/validation/emissions_2024_accounting_balance_summary.json",
        ],
        "accounting_balance_summary": balance_summary,
    }
    (OUT / "spatial_emissions_2024_diagnostics.json").write_text(
        json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return checks


def main() -> None:
    if "--self-test" in sys.argv:
        print(json.dumps(_self_test(), indent=2))
        return
    if "--balances-only" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        socio = pd.read_csv(ROOT / "data" / "derived" / "socioeconomic_2024_by_unit.csv")
        balance_summary = _accounting_balance_2024(socio)
        diagnostics_path = OUT / "spatial_emissions_2024_diagnostics.json"
        if diagnostics_path.exists():
            diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
            diagnostics["accounting_balance_summary"] = balance_summary
            diagnostics_path.write_text(
                json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        print(json.dumps(balance_summary, indent=2, ensure_ascii=False))
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        checks = run()
    print(json.dumps(checks, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
