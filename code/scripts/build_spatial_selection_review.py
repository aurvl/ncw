"""Build a researcher-facing review dossier for the nine spatial relationships.

The script consolidates Moran, LM, nested LR, and fit statistics for every
candidate model and both spatial weights. It reports ranks and coefficient
intervals but deliberately leaves the final model/weight decision to the
researcher.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data" / "derived" / "validation"
TABLES = ROOT / "results" / "tables" / "manuscript"

RELATIONS = [
    ("baseline_2024_same_sample", "lost_capacity_mtco2_yr", "Capacity-loss outcome", "Primary"),
    ("baseline_2024_same_sample", "erosion_pct_of_gcw", "Relative-erosion outcome", "Primary"),
    ("baseline_2024_same_sample", "gcw_gdp_pct_2024", "GCW/GDP 2024 outcome", "Primary"),
    ("add_emissions_2024_as_x", "lost_capacity_mtco2_yr", "Capacity-loss outcome with emissions as X", "Extended"),
    ("add_emissions_2024_as_x", "erosion_pct_of_gcw", "Relative-erosion outcome with emissions as X", "Extended"),
    ("add_emissions_2024_as_x", "gcw_gdp_pct_2024", "GCW/GDP outcome with emissions as X", "Extended"),
    ("emissions_2024_as_y_plus_lost_capacity_x", "emissions_mtco2_yr_2024", "Emissions outcome with capacity loss as X", "Extended"),
    ("emissions_2024_as_y_plus_erosion_x", "emissions_mtco2_yr_2024", "Emissions outcome with relative erosion as X", "Extended"),
    ("emissions_2024_as_y_plus_gcw_gdp_x", "emissions_mtco2_yr_2024", "Emissions outcome with GCW/GDP as X", "Extended"),
]

BASE_PREDICTORS = [
    "ln_gdp_per_capita_2024",
    "ln_forest_area_mha",
    "warm_biome_share",
]
PREDICTOR_LABELS = {
    "ln_gdp_per_capita_2024": "GDP per capita",
    "ln_forest_area_mha": "Forest area",
    "warm_biome_share": "Tropical and subtropical forest share",
}


def standardized_estimate(beta: float, standard_error: float, sd_x: float, sd_y: float) -> tuple[float, float]:
    """Return beta*SD(X)/SD(Y) and its scaled standard error."""
    if not np.isfinite([beta, standard_error, sd_x, sd_y]).all() or sd_y <= 0:
        raise ValueError("Coefficient standardisation needs finite inputs and positive SD(Y).")
    scale = sd_x / sd_y
    return beta * scale, standard_error * scale


def build_fit_and_test_dossier() -> pd.DataFrame:
    evidence = pd.read_csv(VALIDATION / "spatial_emissions_2024_model_selection_evidence.csv")
    fits = pd.read_csv(VALIDATION / "spatial_emissions_2024_model_fit.csv")
    if not fits["optimizer_success"].all() or not fits["covariance_status"].eq("ok").all():
        raise ValueError("The dossier requires all fitted candidates to converge with valid covariance.")

    evidence_columns = [
        "specification", "outcome", "weight", "n",
        "moran_y_log1p_moran_i", "moran_y_log1p_p_holm_within_specification_measure",
        "moran_ols_residual_moran_i", "moran_ols_residual_p_holm_within_specification_measure",
        "lm_robust_LM_lag_statistic", "lm_robust_LM_lag_p_holm_within_specification_test",
        "lm_robust_LM_error_statistic", "lm_robust_LM_error_p_holm_within_specification_test",
        "lr_SDM_vs_SAR_lr_statistic", "lr_SDM_vs_SAR_p_holm_within_specification_comparison",
        "lr_SDEM_vs_SEM_lr_statistic", "lr_SDEM_vs_SEM_p_holm_within_specification_comparison",
        "lr_GNS_vs_SDM_lr_statistic", "lr_GNS_vs_SDM_p_holm_within_specification_comparison",
        "moran_ols_residual_islands", "moran_ols_residual_components",
    ]
    rows: list[pd.DataFrame] = []
    relation_lookup = {(spec, outcome): (label, role) for spec, outcome, label, role in RELATIONS}
    primary = evidence.loc[
        evidence[["specification", "outcome"]].apply(tuple, axis=1).isin(relation_lookup),
        evidence_columns,
    ].copy()
    relation_names = primary[["specification", "outcome"]].apply(
        lambda row: relation_lookup[(row.iloc[0], row.iloc[1])], axis=1
    )
    primary["relationship"] = [item[0] for item in relation_names]
    primary["role"] = [item[1] for item in relation_names]
    fit_subset = fits.merge(
        primary,
        on=["specification", "outcome", "weight"],
        how="inner",
        validate="many_to_one",
        suffixes=("_fit", "_test"),
    )
    fit_subset["relationship_order"] = fit_subset.apply(
        lambda row: next(i for i, item in enumerate(RELATIONS) if item[:2] == (row["specification"], row["outcome"])),
        axis=1,
    )
    fit_subset["model_weight_status"] = "candidate; researcher decision pending"
    fit_subset = fit_subset.sort_values(
        ["relationship_order", "weight", "bic_rank", "model"],
        key=lambda col: col.map({"queen_contiguity": 0, "symmetric_knn5": 1}) if col.name == "weight" else col,
    ).reset_index(drop=True)
    expected = len(RELATIONS) * 2 * 6
    if len(fit_subset) != expected or fit_subset[["specification", "outcome"]].drop_duplicates().shape[0] != 9:
        raise ValueError(f"Expected {expected} candidate fits across nine relationships; found {len(fit_subset)}.")
    return fit_subset


def build_decision_template(dossier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for order, (specification, outcome, label, role) in enumerate(RELATIONS, start=1):
        group = dossier.loc[
            dossier["specification"].eq(specification) & dossier["outcome"].eq(outcome)
        ]
        rows.append(
            {
                "relationship_order": order,
                "relationship": label,
                "role": role,
                "specification": specification,
                "outcome": outcome,
                "sample_n": int(group["n_fit"].iloc[0]),
                "minimum_bic_candidate_by_weight": "; ".join(
                    f"{weight}: {row.model} (BIC={row.bic:.3f})"
                    for weight, row in group.sort_values("bic").groupby("weight", sort=False).head(1).set_index("weight").iterrows()
                ),
                "final_model_decision": pd.NA,
                "final_weight_decision": pd.NA,
                "researcher_rationale": pd.NA,
                "status": "Pending researcher choice",
            }
        )
    return pd.DataFrame(rows)


def build_primary_candidate_coefficients() -> pd.DataFrame:
    sys.path.insert(0, str(ROOT / "code" / "scripts"))
    from run_spatial_emissions_extension import _load_2024_data, _matched_sample, spatial

    data, geometries, _ = _load_2024_data()
    weights = spatial._build_weights(geometries)
    coefficients = pd.read_csv(VALIDATION / "spatial_emissions_2024_model_coefficients.csv")
    fit = pd.read_csv(VALIDATION / "spatial_emissions_2024_model_fit.csv")
    rows: list[dict] = []

    outcome_labels = {
        "lost_capacity_mtco2_yr": "Annual forest addition-capacity loss",
        "erosion_pct_of_gcw": "Relative erosion of GCW",
        "gcw_gdp_pct_2024": "GCW / GDP 2024",
    }
    for specification, outcome, relation_label, role in RELATIONS[:3]:
        sample = _matched_sample(
            data,
            outcome,
            BASE_PREDICTORS,
            outcome in {"lost_capacity_mtco2_yr", "erosion_pct_of_gcw"},
        )
        y_sd = float(np.std(np.log1p(sample[outcome].to_numpy(dtype=float)), ddof=1))
        x = sample[BASE_PREDICTORS].to_numpy(dtype=float)
        ids = sample.index.tolist()
        predictor_index = {name: i for i, name in enumerate(BASE_PREDICTORS)}
        for weight_name in ("queen_contiguity", "symmetric_knn5"):
            weight = spatial._weight_subsample(weights[weight_name], ids)
            wx = np.asarray(weight.sparse @ x)
            candidates = fit.loc[
                fit["specification"].eq(specification)
                & fit["outcome"].eq(outcome)
                & fit["weight"].eq(weight_name)
            ]
            for model in candidates["model"].unique():
                estimates = coefficients.loc[
                    coefficients["specification"].eq(specification)
                    & coefficients["outcome"].eq(outcome)
                    & coefficients["weight"].eq(weight_name)
                    & coefficients["model"].eq(model)
                ]
                for estimate in estimates.itertuples(index=False):
                    if estimate.term in {"constant", "rho", "lambda"}:
                        continue
                    is_spatial_x = estimate.term.startswith("W_")
                    predictor = estimate.term.removeprefix("W_")
                    if predictor not in predictor_index:
                        continue
                    column = predictor_index[predictor]
                    sd_x = float(np.std(wx[:, column] if is_spatial_x else x[:, column], ddof=1))
                    std_beta, std_se = standardized_estimate(
                        float(estimate.coefficient), float(estimate.std_error_ml), sd_x, y_sd
                    )
                    rows.append(
                        {
                            "relationship": relation_label,
                            "role": role,
                            "specification": specification,
                            "outcome": outcome,
                            "outcome_label": outcome_labels[outcome],
                            "model": model,
                            "weight": weight_name,
                            "n": int(estimate.n),
                            "term": estimate.term,
                            "term_label": PREDICTOR_LABELS[predictor]
                            + (" in neighbouring units" if is_spatial_x else " in this unit"),
                            "term_order": column + 1 + (3 if is_spatial_x else 0),
                            "effect_scope": "spatially lagged covariate" if is_spatial_x else "unit covariate",
                            "coefficient_raw": float(estimate.coefficient),
                            "std_error_raw": float(estimate.std_error_ml),
                            "standardized_coefficient": std_beta,
                            "standardized_std_error": std_se,
                            "ci95_low": std_beta - 1.96 * std_se,
                            "ci95_high": std_beta + 1.96 * std_se,
                            "p_wald": float(estimate.p_wald_ml),
                            "predictor_sd": sd_x,
                            "outcome_sd_log1p": y_sd,
                            "standardization": "beta * SD(X or WX) / SD(log1p(Y))",
                            "interval_method": "95% Wald interval using fitted model covariance",
                            "selection_status": "candidate estimate; model not selected",
                        }
                    )
    result = pd.DataFrame(rows)
    if result.empty or result["relationship"].nunique() != 3:
        raise ValueError("Could not construct coefficient review for the three primary relationships.")
    if not result["ci95_low"].le(result["ci95_high"]).all():
        raise ValueError("A standardized coefficient interval is malformed.")
    return result.sort_values(
        ["relationship", "term_order", "weight", "model"],
        key=lambda col: col.map({"queen_contiguity": 0, "symmetric_knn5": 1}) if col.name == "weight" else col,
    ).reset_index(drop=True)


def build_selection_review(root: Path = ROOT) -> dict[str, Path]:
    global VALIDATION, TABLES
    VALIDATION = root / "data" / "derived" / "validation"
    TABLES = root / "results" / "tables" / "manuscript"
    TABLES.mkdir(parents=True, exist_ok=True)
    dossier = build_fit_and_test_dossier()
    coeffs = build_primary_candidate_coefficients()
    decisions = build_decision_template(dossier)
    paths = {
        "dossier": TABLES / "Supplementary_spatial_selection_dossier.csv",
        "candidate_coefficients": TABLES / "Supplementary_spatial_candidate_standardized_coefficients.csv",
        "decision_template": VALIDATION / "spatial_model_decision_template.csv",
    }
    dossier.to_csv(paths["dossier"], index=False)
    coeffs.to_csv(paths["candidate_coefficients"], index=False)
    decisions.to_csv(paths["decision_template"], index=False)
    return paths


def main() -> None:
    paths = build_selection_review()
    print("Wrote spatial selection review; final decisions remain blank:")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
