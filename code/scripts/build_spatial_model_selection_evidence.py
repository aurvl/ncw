"""Consolidate the four requested spatial-model screening steps for human review.

This script joins diagnostics and information-criterion rankings already produced
by ``run_spatial_emissions_extension.py``. It does not select a final
model or interpret coefficients.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data" / "outputs" / "validation"
CASE_KEYS = ["specification", "outcome", "weight"]


def load_table(filename: str) -> pd.DataFrame:
    """Load one analysis output and fail if it is absent."""
    path = VALIDATION / filename
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def pivot_diagnostics(
    frame: pd.DataFrame,
    value_columns: list[str],
    row_keys: list[str],
    column_key: str,
    prefix: str,
) -> pd.DataFrame:
    """Pivot one diagnostic stage into one record per model case."""
    values = frame.pivot(index=row_keys, columns=column_key, values=value_columns)
    values.columns = [f"{prefix}_{measure}_{stat}" for stat, measure in values.columns]
    return values.reset_index()


def build_evidence_table() -> pd.DataFrame:
    """Join Moran, LM, nested LR and AIC/BIC evidence without choosing a model."""
    moran = load_table("spatial_emissions_2024_step1_moran.csv")
    moran = pivot_diagnostics(
        moran,
        ["moran_i", "p_permutation_two_sided", "p_holm_within_specification_measure", "islands", "components"],
        CASE_KEYS,
        "measure",
        "moran",
    )

    lm = load_table("spatial_emissions_2024_step2_lm_tests.csv")
    lm = pivot_diagnostics(
        lm,
        ["statistic", "p_value", "p_holm_within_specification_test"],
        CASE_KEYS,
        "test",
        "lm",
    )

    nested = load_table("spatial_emissions_2024_step3_nested_tests.csv")
    nested = pivot_diagnostics(
        nested,
        ["lr_statistic", "df", "p_value", "p_holm_within_specification_comparison"],
        CASE_KEYS,
        "comparison",
        "lr",
    )

    fit = load_table("spatial_emissions_2024_model_fit.csv")
    fit_records: list[dict[str, object]] = []
    for keys, group in fit.groupby(CASE_KEYS, sort=True):
        ordered_aic = group.sort_values(["aic", "model"])
        ordered_bic = group.sort_values(["bic", "model"])
        minimum_aic = ordered_aic["aic"].min()
        minimum_bic = ordered_bic["bic"].min()
        record = dict(zip(CASE_KEYS, keys))
        record.update(
            {
                "n": int(group["n"].iloc[0]),
                "models_estimated": int(group["model"].nunique()),
                "all_models_converged": bool(group["optimizer_success"].all()),
                "all_covariance_status_ok": bool(group["covariance_status"].eq("ok").all()),
                "aic_model_order_low_to_high": " < ".join(ordered_aic["model"].astype(str)),
                "bic_model_order_low_to_high": " < ".join(ordered_bic["model"].astype(str)),
                "minimum_aic_model": ";".join(
                    group.loc[group["aic"].eq(minimum_aic), "model"].astype(str)
                ),
                "minimum_aic": float(minimum_aic),
                "minimum_bic_model": ";".join(
                    group.loc[group["bic"].eq(minimum_bic), "model"].astype(str)
                ),
                "minimum_bic": float(minimum_bic),
                "aic_bic_minima_agree": bool(
                    set(group.loc[group["aic"].eq(minimum_aic), "model"])
                    == set(group.loc[group["bic"].eq(minimum_bic), "model"])
                ),
                "final_model_selected": False,
            }
        )
        fit_records.append(record)
    fit_summary = pd.DataFrame(fit_records)

    result = fit_summary.merge(moran, on=CASE_KEYS, how="left", validate="one_to_one")
    result = result.merge(lm, on=CASE_KEYS, how="left", validate="one_to_one")
    result = result.merge(nested, on=CASE_KEYS, how="left", validate="one_to_one")

    result["outcome_family"] = result["outcome"].map(
        {
            "lost_capacity_mtco2_yr": "deforestation: absolute lost annual capacity",
            "erosion_pct_of_gcw": "deforestation: lost capacity relative to GCW",
            "gcw_gdp_pct_2024": "forest wealth relative to 2024 GDP",
            "emissions_mtco2_yr_2024": "fossil and industrial CO2 emissions 2024",
        }
    )
    family = {
        "baseline_2024_same_sample": "base controls, common complete-case sample",
        "add_emissions_2024_as_x": "base controls plus emissions as X",
        "emissions_2024_as_y": "emissions as Y, auxiliary base-controls model",
        "emissions_2024_as_y_plus_population_sensitivity": "emissions as Y plus population sensitivity, auxiliary",
        "emissions_y_baseline_matched_lost_capacity": "matched reduced emissions-Y reference for likelihood comparison",
        "emissions_y_baseline_matched_erosion": "matched reduced emissions-Y reference for likelihood comparison",
        "emissions_y_baseline_matched_gcw_gdp": "matched reduced emissions-Y reference for likelihood comparison",
        "emissions_2024_as_y_plus_lost_capacity_x": "emissions as Y plus lost-capacity outcome as X",
        "emissions_2024_as_y_plus_erosion_x": "emissions as Y plus relative-erosion outcome as X",
        "emissions_2024_as_y_plus_gcw_gdp_x": "emissions as Y plus GCW/GDP outcome as X",
    }
    result["specification_family"] = result["specification"].map(family).fillna(result["specification"])
    result["case_role"] = "comparison_only_matched_reference"
    result.loc[result["specification"].eq("baseline_2024_same_sample"), "case_role"] = "primary_relationship"
    result.loc[result["specification"].eq("add_emissions_2024_as_x"), "case_role"] = "primary_relationship"
    result.loc[result["specification"].isin([
        "emissions_2024_as_y_plus_lost_capacity_x",
        "emissions_2024_as_y_plus_erosion_x",
        "emissions_2024_as_y_plus_gcw_gdp_x",
    ]), "case_role"] = "primary_relationship"
    result.loc[result["specification"].isin([
        "emissions_2024_as_y",
        "emissions_2024_as_y_plus_population_sensitivity",
    ]), "case_role"] = "auxiliary"
    result["relationship_profile_count"] = int(result["case_role"].eq("primary_relationship").sum() / 2)
    result["final_model_selected"] = False
    if len(result) != 28 or result.duplicated(CASE_KEYS).any():
        raise ValueError(f"Expected 28 unique outcome-specification-weight cases; found {len(result)}")
    if result.loc[result["case_role"].eq("primary_relationship"), ["specification", "outcome"]].drop_duplicates().shape[0] != 9:
        raise ValueError("Expected exactly nine primary outcome/specification relationships")
    if not result["all_models_converged"].all():
        failed = result.loc[~result["all_models_converged"], CASE_KEYS]
        raise ValueError(f"At least one model did not converge: {failed.to_dict('records')}")
    return result.sort_values(CASE_KEYS).reset_index(drop=True)


def write_note(table: pd.DataFrame) -> None:
    """Document the counts and boundary of the model-comparison output."""
    rows = []
    for (specification, outcome), group in table.groupby(["specification", "outcome"], sort=True):
        rows.append(
            f"| `{specification}` | `{outcome}` | {int(group['n'].iloc[0])} | {len(group)} | "
            f"{'; '.join(group['minimum_aic_model'].astype(str))} | "
            f"{'; '.join(group['minimum_bic_model'].astype(str))} |"
        )
    note = [
        "# Aide de lecture pour la sélection des modèles spatiaux 2024",
        "",
        "Fichier de comparaison : `../repo/data/outputs/validation/spatial_emissions_2024_model_selection_evidence.csv`.",
        "Sorties sources : étapes 1 (Moran), 2 (LM), 3 (LR emboîtés) et ajustements OLS/SAR/SEM/SDM/SDEM/GNS.",
        "",
        "## Ce qui est comparé",
        "",
        "Le plan comprend neuf relations principales : les trois résultats antérieurs avec leurs contrôles, ces mêmes résultats avec les émissions 2024 ajoutées comme X, puis trois modèles où les émissions sont Y et chacun des trois résultats antérieurs est ajouté séparément comme X. Chaque relation est estimée sous Queen et kNN symétrisé à 5 voisins, soit 18 cas principaux. Le modèle émissions-Y de base et la sensibilité avec population restent des comparaisons auxiliaires. Trois régressions émissions-Y de base, réestimées sur les échantillons complets propres à chaque résultat, servent uniquement de références appariées pour les tests LR d’ajout de X; elles ne sont pas comptées comme relations supplémentaires.",
        "",
        "| Spécification | Résultat | n | matrices | Minimum AIC (Queen puis kNN) | Minimum BIC (Queen puis kNN) |",
        "|---|---|---:|---:|---|---|",
        *rows,
        "",
        "## Lecture des étapes",
        "",
        "1. Moran est fourni pour `y` transformé et les résidus OLS. Les p-values de permutation et leurs corrections de Holm restent dans le CSV.",
        "2. Les tests LM simples, robustes et conjoints partent de l’OLS; les statistiques, degrés de liberté et p-values brutes/ajustées sont conservés.",
        "3. Les tests LR comparent SDM à SAR, SDEM à SEM et GNS à SDM. Ils n’ordonnent pas directement SDM et SDEM l’un par rapport à l’autre.",
        "4. Les modèles sont classés par AIC et BIC à effectif identique. Le classement fournit un élément de décision; les critères peuvent diverger et ne constituent pas un choix final.",
        "",
        "Pour les trois modèles émissions-Y étendus, le résultat forestier est introduit en log1p, comme dans les transformations de résultats de l’analyse principale, et les mêmes contrôles de base sont conservés. Les trois références appariées permettent de comparer les modèles sur exactement les mêmes unités. Aucun modèle final n’est sélectionné automatiquement : les diagnostics, classements AIC/BIC et résultats des tests sont présentés comme éléments de comparaison.",
        "",
        "L’analyse est transversale et descriptive. Les coefficients et leurs p-values n’établissent pas un effet causal. Queen comporte des unités isolées; kNN relie les unités éloignées selon la distance des centroïdes représentatifs.",
        "",
    ]
    note_path = ROOT.parent / "NEXT" / "SPATIAL_MODEL_SELECTION_EVIDENCE.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "\n".join(note), encoding="utf-8"
    )


def main() -> None:
    """Write the evidence table and its reading note."""
    table = build_evidence_table()
    path = VALIDATION / "spatial_emissions_2024_model_selection_evidence.csv"
    table.to_csv(path, index=False, float_format="%.10g")
    write_note(table)
    print(f"Wrote {len(table)} spatial evidence rows to {path}")
    print("No final model was selected.")


if __name__ == "__main__":
    main()
