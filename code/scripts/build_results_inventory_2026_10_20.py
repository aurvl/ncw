"""Build the exhaustive results inventory including the 2024 emissions update.

The 2026-10-19 inventory is retained as the complete prior analysis record.
Its stale GCB-status paragraph is replaced and all 2024 source, country,
accounting, and spatial outputs are appended verbatim as TSV/JSON tables.
This script does not edit manuscript files or figures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "results" / "validation"
SUMMARY = ROOT / "data" / "derived"
BASE = VALIDATION / "RESULTS_INVENTORY_2026-10-19.txt"
DEST = VALIDATION / "RESULTS_INVENTORY_2026-10-20.txt"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def tsv(frame: pd.DataFrame) -> str:
    return frame.to_csv(
        index=False,
        sep="\t",
        float_format="%.8g",
        na_rep="NA",
        lineterminator="\n",
    ).rstrip()


def block(title: str, path: Path, frame: pd.DataFrame | None = None) -> str:
    if frame is None:
        frame = read_csv(path)
    return f"### {title}\nSource: `{path.relative_to(ROOT).as_posix()}`\n\n{tsv(frame)}"


def json_block(title: str, path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"### {title}\nSource: `{path.relative_to(ROOT).as_posix()}`\n\n```json\n{body}\n```"


def main() -> None:
    base = BASE.read_text(encoding="utf-8")
    replacement = (
        "Vérification GCB au 2026-10-20 : le Data Hub officiel présente le Global Carbon Budget 2025 "
        "comme l’édition la plus récente disponible; aucune édition 2026 n’y est publiée à cette date. "
        "Le classeur national v2025 fournit les émissions territoriales fossiles et industrielles jusqu’en 2024. "
        "Les séries de population et de PIB 2024 viennent de WDI. Les extractions, contrôles de couverture, "
        "comparaisons de millésimes et modèles spatiaux 2024 sont maintenant exécutés et détaillés dans la "
        "section d’extension ci-dessous. La dette n’est pas utilisée. Sources : "
        "https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/ ; "
        "https://data.worldbank.org/indicator/SP.POP.TOTL ; "
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD."
    )
    pattern = re.compile(
        r"Vérification GCB au 2026-10-20:.*?(?=\n\n1\. Périmètre)",
        flags=re.DOTALL,
    )
    base, replaced = pattern.subn(replacement, base, count=1)
    if replaced != 1:
        raise RuntimeError(f"Expected to replace one stale GCB note; replaced {replaced}")

    socio = read_csv(SUMMARY / "socioeconomic_2024_by_unit.csv")
    emissions_change = read_csv(VALIDATION / "gcb2025_emissions_change_2023_2024_by_unit.csv")
    vintage = read_csv(VALIDATION / "gcb2025_2023_vintage_vs_bcw_2023_by_unit.csv")
    coverage = json.loads((VALIDATION / "socioeconomic_2024_coverage_audit.json").read_text(encoding="utf-8"))
    accounting = json.loads((VALIDATION / "emissions_2024_accounting_balance_summary_2026-10-20.json").read_text(encoding="utf-8"))
    diag = json.loads((VALIDATION / "spatial_emissions_2024_diagnostics_2026-10-20.json").read_text(encoding="utf-8"))

    fit = read_csv(VALIDATION / "spatial_emissions_2024_model_fit_2026-10-20.csv")
    sample = read_csv(VALIDATION / "spatial_emissions_2024_sample_audit_2026-10-20.csv")
    moran = read_csv(VALIDATION / "spatial_emissions_2024_step1_moran_2026-10-20.csv")
    lm = read_csv(VALIDATION / "spatial_emissions_2024_step2_lm_tests_2026-10-20.csv")
    nested = read_csv(VALIDATION / "spatial_emissions_2024_step3_nested_tests_2026-10-20.csv")
    block_tests = read_csv(VALIDATION / "spatial_emissions_2024_predictor_block_tests_2026-10-20.csv")
    focus_coefficients = read_csv(VALIDATION / "spatial_emissions_2024_focus_coefficients_2026-10-20.csv")

    required = {
        "study_units": len(socio),
        "matched_emissions": int(socio["co2_emissions_tco2_2024"].notna().sum()),
        "matched_population": int(socio["population_2024"].notna().sum()),
        "matched_gdp": int(socio["gdp_2015usd_2024"].notna().sum()),
        "common": int(socio[["co2_emissions_tco2_2024", "population_2024", "gdp_2015usd_2024"]].notna().all(axis=1).sum()),
    }
    if required != {
        "study_units": 236,
        "matched_emissions": 210,
        "matched_population": 213,
        "matched_gdp": 196,
        "common": 193,
    }:
        raise RuntimeError(f"Coverage changed unexpectedly: {required}")
    if not fit["optimizer_success"].all() or not fit["covariance_status"].eq("ok").all():
        raise RuntimeError("At least one spatial fit/covariance did not pass its status check")
    if len(fit) != 168 or len(moran) != 56 or len(lm) != 168 or len(nested) != 84 or len(block_tests) != 84:
        raise RuntimeError("Unexpected number of spatial output rows")

    common_vintage = vintage.dropna(subset=["CO2_emissions_2023", "co2_emissions_tco2_2023_gcb2025"])
    abs_pct = common_vintage["pct_difference"].abs()
    world_change = emissions_change["absolute_change_tco2"].sum()
    top_increases = emissions_change.nlargest(10, "absolute_change_tco2")[["iso3", "name", "absolute_change_tco2", "pct_change"]]
    top_decreases = emissions_change.nsmallest(10, "absolute_change_tco2")[["iso3", "name", "absolute_change_tco2", "pct_change"]]

    y_emissions = moran[
        (moran["specification"] == "emissions_2024_as_y")
        & (moran["measure"] == "y_log1p")
    ][["weight", "n", "islands", "components", "moran_i", "p_permutation_two_sided", "p_holm_within_specification_measure"]]
    residual_emissions = moran[
        (moran["specification"] == "emissions_2024_as_y")
        & (moran["measure"] == "ols_residual")
    ][["weight", "n", "moran_i", "p_permutation_two_sided", "p_holm_within_specification_measure"]]
    test_counts = block_tests.groupby("block_test").agg(
        comparisons=("p_value", "size"),
        Holm_p_below_005=("p_holm_within_block_model", lambda x: int((x < 0.05).sum())),
        Holm_p_below_001=("p_holm_within_block_model", lambda x: int((x < 0.01).sum())),
        smallest_Holm_p=("p_holm_within_block_model", "min"),
    ).reset_index()
    target_y_specs = [
        "emissions_2024_as_y_plus_lost_capacity_x",
        "emissions_2024_as_y_plus_erosion_x",
        "emissions_2024_as_y_plus_gcw_gdp_x",
    ]
    added_y_moran = moran[
        moran["specification"].isin(target_y_specs) & moran["measure"].eq("y_log1p")
    ][["specification", "weight", "n", "moran_i", "p_permutation_two_sided", "p_holm_within_specification_measure"]]
    added_y_ols = focus_coefficients[
        focus_coefficients["specification"].isin(target_y_specs)
        & focus_coefficients["model"].eq("OLS")
        & focus_coefficients["term"].str.startswith("log1p_")
    ][["specification", "weight", "n", "term", "coefficient", "std_error_ml", "p_wald_ml"]]
    added_y_block_counts = block_tests[
        block_tests["block_test"].isin(["lost_capacity_as_x", "erosion_as_x", "gcw_gdp_as_x"])
    ].groupby(["block_test", "model"], as_index=False).agg(
        comparisons=("p_value", "size"),
        Holm_p_below_005=("p_holm_within_block_model", lambda x: int((x < 0.05).sum())),
        smallest_Holm_p=("p_holm_within_block_model", "min"),
    )
    evidence = read_csv(VALIDATION / "spatial_emissions_2024_model_selection_evidence_2026-10-20.csv")
    aic_bic_divergent = int((~evidence["aic_bic_minima_agree"]).sum())

    overview = [
        "# Extension 2024 des émissions et des modèles spatiaux",
        "",
        "Cette extension met à jour les variables d’émissions, de population et de PIB à l’année de référence 2024, puis reprend les séquences de tests spatiaux sur des échantillons appariés. La dette n’est pas téléchargée ni utilisée. Elle ne modifie pas les figures ni le manuscrit. Les résultats antérieurs restent conservés; cette section est la référence pour les analyses dépendant des émissions au millésime 2024.",
        "",
        "## Sources, périmètres et couverture",
        "Le Global Carbon Budget 2025 est la dernière édition présente sur le Data Hub officiel au 2026-10-20; l’édition 2026 n’y est pas disponible à cette date. Le classeur national utilise des émissions territoriales fossiles et des procédés industriels en MtC/an; les émissions d’usage des terres sont exclues. Conversion du classeur : 1 MtC = 3,664 MtCO₂. Les valeurs sont des estimations harmonisées, pas des mesures directes pays par pays. Source : https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/.",
        "La population 2024 et le PIB en dollars constants de 2015 proviennent des indicateurs WDI SP.POP.TOTL et NY.GDP.MKTP.KD. WDI décrit la population comme une estimation de milieu d’année et fournit la série à partir de sources nationales, ONU et Eurostat; un millésime commun ne signifie pas que toutes les observations sont directement mesurées. La dette reste hors du calcul. Sources : https://data.worldbank.org/indicator/SP.POP.TOTL ; https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.",
        f"Sur les {required['study_units']} unités de l’étude : émissions disponibles pour {required['matched_emissions']}, population pour {required['matched_population']}, PIB pour {required['matched_gdp']}; {required['common']} unités ont les trois variables. Seules les correspondances pays/territoire directes sont utilisées; aucun total souverain n’est recopié sur un territoire distinct et aucune valeur manquante n’est remplacée par zéro. Les modèles qui nécessitent la géométrie excluent aussi Gibraltar, sans géométrie exploitable.",
        "",
        "## Comparabilité des émissions et variations 2023-2024",
        f"La comparaison croisée de la série GCB 2025 pour 2023 avec l’ancienne série 2023 de BCW porte sur {len(common_vintage)} unités : corrélation de Pearson r = {common_vintage[['CO2_emissions_2023','co2_emissions_tco2_2023_gcb2025']].corr().iloc[0,1]:.6f}; écart absolu médian = {abs_pct.median():.3f}%; écart absolu moyen = {abs_pct.mean():.3f}%. Une corrélation élevée indique un classement/co-mouvement proche, mais ne prouve pas l’identité des définitions ou des niveaux.",
        f"Dans les unités appariées, le changement agrégé 2023-2024 est de {world_change/1e9:.3f} GtCO₂/an. Ce total couvre les unités directement appariées et ne doit pas être assimilé au total mondial exhaustif. Les dix augmentations et diminutions absolues les plus grandes sont listées ci-dessous; le fichier complet contient toutes les unités appariées.",
        "### Plus fortes hausses absolues 2023-2024 (unités appariées)",
        tsv(top_increases),
        "### Plus fortes baisses absolues 2023-2024 (unités appariées)",
        tsv(top_decreases),
        "",
        "## Comparaison comptable GCW/NCW et émissions 2024",
        f"Pour les {accounting['units_with_emissions']} unités appariées, les émissions GCB 2024 totalisent {accounting['gcb_emissions_sum_covered_units_tco2_yr']/1e9:.3f} GtCO₂/an et les ajouts GCW à la biomasse vivante {accounting['gcw_gross_additions_sum_covered_units_tco2_yr']/1e9:.3f} GtCO₂/an. La somme des différences GCW-émissions est {accounting['gcw_accounting_balance_world_sum_tco2_yr']/1e9:.3f} GtCO₂/an; celle NCW-émissions est {accounting['ncw_accounting_balance_world_sum_tco2_yr']/1e9:.3f} GtCO₂/an. Les balances GCW sont positives pour {accounting['gcw_accounting_balance_positive_units']} unités, et NCW pour {accounting['ncw_accounting_balance_positive_units']} unités. C’est une comparaison comptable territoriale, pas un test de neutralité nationale ni le bilan net de tous les écosystèmes. Les émissions sont fixes; les quantiles propagés viennent uniquement des tirages antérieurs de richesse/GSCC.",
        "",
        "## Séquence spatiale 2024 : plan et principaux constats descriptifs",
        f"La séquence reprend les quatre étapes de la feuille de processus : Moran sur Y et résidus OLS ({diag['permutations']:,} permutations), tests LM/LM robustes, tests LR des modèles emboîtés (SAR-SDM, SEM-SDEM, SDM-GNS), puis comparaison des coefficients et classements AIC/BIC. Les {len(fit)} ajustements des six familles (OLS, SAR, SEM, SDM, SDEM, GNS) convergent et les statuts de covariance sont valides. Deux matrices sont comparées : contiguïté Queen et k plus proches voisins symétrisés (k=5). Les résultats restent des associations transversales, pas des effets causaux. Le plan contient neuf relations principales (18 cas avec deux matrices), deux modèles émissions-Y auxiliaires, et trois références réduites appariées utilisées seulement pour les tests d'ajout de covariables. Aucun modèle final n'est choisi.",
        "Les neuf relations principales sont : (1) les trois résultats antérieurs - capacité annuelle perdue, érosion rapportée au GCW et GCW/PIB 2024 - avec contrôles de base; (2) ces mêmes résultats avec les émissions GCB 2024 ajoutées aux contrôles; (3) émissions GCB 2024 comme résultat, avec chacun des trois résultats antérieurs ajouté séparément aux contrôles de base. Les trois dernières relations utilisent log1p de l’ancien résultat comme X et gardent les contrôles de base (PIB par habitant, surface forestière, part des biomes chauds). Pour chacune, l’ajout de X est comparé à un modèle réduit sur le même échantillon complet. Le modèle émissions-Y sans résultat antérieur et sa version avec population restent des références auxiliaires, pas des relations principales.",
        "Effectifs : les modèles capacité perdue et érosion ont n=120; GCW/PIB 2024 a n=191. Avec émissions comme Y, les trois modèles ajoutant capacité perdue, érosion ou GCW/PIB ont respectivement n=120, 120 et 191; les références réduites ont exactement les mêmes unités que leur modèle étendu. Le modèle émissions-Y de base a n=191. Les contrôles spatiaux enregistrent 19 ou 45 isolats Queen selon l'échantillon, contre un composant principal sous kNN-5; l'interprétation spatiale dépend donc aussi de la définition du voisinage.",
        "Pour l’émission comme Y, Moran indique une autocorrélation spatiale positive de Y sous les deux matrices :",
        tsv(y_emissions),
        "Après OLS avec les contrôles principaux, l’autocorrélation des résidus reste positive et détectable sous les deux matrices :",
        tsv(residual_emissions),
        "### Relations principales avec émissions 2024 comme résultat",
        "Les trois modèles conservent les contrôles de base et ajoutent séparément log1p de la capacité perdue, de l'érosion/GCW ou de GCW/PIB. Chaque modèle réduit est réestimé sur le même échantillon complet avant de tester l'ajout. Moran de Y transformé :",
        tsv(added_y_moran),
        "Coefficients OLS des covariables ajoutées (associations conditionnelles, pas effets causaux) :",
        tsv(added_y_ols),
        "Résultats des tests de bloc appariés par famille de modèle; chaque ligne compare le modèle réduit et le modèle étendu sur le même échantillon :",
        tsv(added_y_block_counts),
        "Dans les modèles OLS de l’émission comme Y, la surface forestière et le PIB/habitant ont des coefficients positifs avec p<0,001; la part des biomes chauds a p=0,057 dans la spécification sans population. Lorsque la population est ajoutée, le coefficient de population est positif (p très inférieur à 0,001), tandis que surface forestière et part des biomes chauds ne sont pas significatives aux seuils usuels dans l’OLS. Ces associations ne permettent pas d’attribuer un effet causal aux facteurs naturels.",
        "Quand les émissions sont ajoutées comme X aux trois résultats antérieurs, le test global d’ajout du bloc (correction de Holm dans chaque résultat/matrice/famille) est significatif dans 12/12 comparaisons pour GCW/PIB, 2/12 pour l’érosion/GCW, et 0/12 pour la perte absolue. En OLS, le coefficient log émissions est négatif pour GCW/PIB (−0,535, p<0,001), mais n’est pas distinguable de zéro pour la perte absolue ou l’érosion relative. Les tests restent conditionnels aux variables, périmètres, tailles d’échantillon et matrices définis ici; la forte relation du ratio GCW/PIB avec une mesure d’émissions totale doit être lue en tenant compte de la taille économique, déjà partiellement contrôlée par le PIB/habitant.",
        f"Les trois modèles émissions-Y étendus ne sont pas des régressions causales des forêts sur les émissions : ils testent des associations conditionnelles transversales. En particulier, GCW/PIB contient le PIB au dénominateur, alors que le modèle conserve aussi le PIB par habitant comme contrôle. La table de preuve distingue les neuf relations principales, les deux références auxiliaires et les trois modèles réduits appariés. Les minima AIC/BIC diffèrent dans {aic_bic_divergent} des {len(evidence)} cas; cela ne désigne pas automatiquement un modèle gagnant. Aucun modèle final n'est déclaré.",
        "",
        "## Fichiers détaillés et tables complètes",
    ]

    sections: list[str] = ["\n".join(overview)]
    sections.append(json_block("Audit de couverture socioéconomique 2024", VALIDATION / "socioeconomic_2024_coverage_audit.json"))
    sections.append(json_block("Diagnostics du protocole spatial 2024", VALIDATION / "spatial_emissions_2024_diagnostics_2026-10-20.json"))
    sections.append(json_block("Résumé du bilan comptable 2024", VALIDATION / "emissions_2024_accounting_balance_summary_2026-10-20.json"))
    sections.append(json_block("Audit de la table pays/territoires consolidée", VALIDATION / "country_level_results_master_audit_2026-10-20.json"))
    dictionary_path = ROOT / "docs" / "COUNTRY_LEVEL_RESULTS_MASTER_DATA_DICTIONARY_2026-10-20.md"
    sections.append("### Dictionnaire des données de la table pays/territoires consolidée\n\n" + dictionary_path.read_text(encoding="utf-8"))

    csv_specs = [
        ("Table complète des unités et variables socioéconomiques 2024", SUMMARY / "socioeconomic_2024_by_unit.csv"),
        ("Émissions GCB v2025 par unité pour 2023 et 2024", SUMMARY / "gcb2025_national_fossil_emissions_2023_2024_by_entity.csv"),
        ("Table consolidée par pays/territoire pour la rédaction des Results", VALIDATION / "country_level_results_master_2026-10-20.csv"),
        ("Variation 2023-2024 par unité", VALIDATION / "gcb2025_emissions_change_2023_2024_by_unit.csv"),
        ("Comparaison de millésime GCB 2025 2023 contre BCW 2023", VALIDATION / "gcb2025_2023_vintage_vs_bcw_2023_by_unit.csv"),
        ("Bilan comptable 2024 par unité", VALIDATION / "emissions_2024_accounting_balance_by_unit_2026-10-20.csv"),
        ("Bilan comptable 2024 par groupes", VALIDATION / "emissions_2024_accounting_balance_groups_2026-10-20.csv"),
        ("Audit des échantillons spatiaux", VALIDATION / "spatial_emissions_2024_sample_audit_2026-10-20.csv"),
        ("Étape 1 - Moran sur Y et résidus OLS", VALIDATION / "spatial_emissions_2024_step1_moran_2026-10-20.csv"),
        ("Étape 2 - tests LM et robustes", VALIDATION / "spatial_emissions_2024_step2_lm_tests_2026-10-20.csv"),
        ("Étape 3 - rapports de vraisemblance des modèles emboîtés", VALIDATION / "spatial_emissions_2024_step3_nested_tests_2026-10-20.csv"),
        ("Table consolidée des quatre étapes de comparaison spatiale", VALIDATION / "spatial_emissions_2024_model_selection_evidence_2026-10-20.csv"),
        ("Estimation et critères d’ajustement des 168 modèles", VALIDATION / "spatial_emissions_2024_model_fit_2026-10-20.csv"),
        ("Coefficients de tous les modèles spatiaux", VALIDATION / "spatial_emissions_2024_model_coefficients_2026-10-20.csv"),
        ("Coefficients ciblés pour les variables étudiées", VALIDATION / "spatial_emissions_2024_focus_coefficients_2026-10-20.csv"),
        ("Tests d’ajout des blocs émissions/population sur échantillons identiques", VALIDATION / "spatial_emissions_2024_predictor_block_tests_2026-10-20.csv"),
        ("Corrélations entre prédicteurs", VALIDATION / "spatial_emissions_2024_predictor_correlations_2026-10-20.csv"),
        ("Facteurs d’inflation de variance (VIF)", VALIDATION / "spatial_emissions_2024_predictor_vif_2026-10-20.csv"),
    ]
    sections.extend(block(title, path) for title, path in csv_specs)

    DEST.write_text(base.rstrip() + "\n\n" + "\n\n".join(sections) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(DEST), "bytes": DEST.stat().st_size, "coverage": required,
                      "models": len(fit), "all_models_converged": bool(fit.optimizer_success.all()),
                      "moran_rows": len(moran), "lm_rows": len(lm), "nested_rows": len(nested)}, indent=2))


if __name__ == "__main__":
    main()
