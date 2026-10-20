"""Create a traceable text inventory of current BNC2 results.

The inventory is generated from the current pipeline tables after GMW 2025
replacement and selective FRA mangrove-overlap accounting. It does not rewrite
the manuscript or render figures.
"""

from __future__ import annotations

from pathlib import Path
import json
import zipfile

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
DATA = ROOT / "data"
DEST = OUT / "validation" / "RESULTS_INVENTORY_2026-10-19.txt"
GROUP_ORDER = ["Developed economies", "Developing economies", "LDCs", "SIDS"]
INTERVALS = ["1990-2000", "2000-2010", "2010-2015", "2015-2020", "2020-2025"]
MIDPOINTS = np.array([1995, 2005, 2012.5, 2017.5, 2022.5], dtype=float)


def gini(values) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    x = x[np.isfinite(x)]
    if not len(x) or x.sum() == 0:
        return float("nan")
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def tsv(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if columns is not None:
        frame = frame.loc[:, columns]
    return frame.to_csv(index=False, sep="\t", float_format="%.6g", na_rep="NA", lineterminator="\n")


def mann_kendall(y: np.ndarray) -> tuple[float, float]:
    y = np.asarray(y, dtype=float)
    n = len(y)
    s = float(sum(np.sign(y[j] - y[i]) for i in range(n - 1) for j in range(i + 1, n)))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - np.sign(s)) / np.sqrt(var) if s else 0.0
    return s, float(2 * (1 - stats.norm.cdf(abs(z))))


def main() -> None:
    gcw = pd.read_csv(OUT / "country_level_gcw.csv")
    ncw = pd.read_csv(OUT / "country_level_ncw.csv")
    global_ecosystems = pd.read_csv(OUT / "tables" / "table1_global_by_ecosystem.csv")
    continents = pd.read_csv(OUT / "tables" / "table2_by_continent.csv")
    groups = pd.read_csv(OUT / "tables" / "table3_by_group.csv")
    top_ncw = pd.read_csv(OUT / "tables" / "table4_top_territories.csv")
    erosion = pd.read_csv(OUT / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv")
    erosion_groups = pd.read_csv(OUT / "tables" / "manuscript" / "Table3_erosion_by_group.csv")
    group_profiles = pd.read_csv(OUT / "tables" / "manuscript" / "Table2_group_profiles_and_balances.csv")
    rates = pd.read_csv(DATA / "derived" / "gfw_gibbs_biome_rates.csv")
    rates_with_mangroves = pd.read_csv(DATA / "derived" / "gfw_gibbs_biome_rates_with_mangroves.csv")
    areas = pd.read_csv(DATA / "derived" / "forest_area_by_biome.csv")
    uptake_spatial_sensitivity = pd.read_csv(DATA / "derived" / "forest_uptake_spatial_sensitivity.csv")
    uptake_faostat = pd.read_csv(DATA / "derived" / "forest_uptake_faostat.csv")
    overlap = pd.read_csv(DATA / "derived" / "fra_mangrove_forest_overlap_2025.csv")
    gmw = pd.read_csv(DATA / "derived" / "gmw_2025_mangrove_area_by_unit.csv")
    valuation_fraction = pd.read_csv(OUT / "validation" / "gcw_valuation_fraction_sensitivity_world.csv")
    valuation_fraction_units = pd.read_csv(OUT / "validation" / "gcw_valuation_fraction_sensitivity_by_unit.csv")
    abatement = pd.read_csv(OUT / "validation" / "forest_abatement_no_trade_summary.csv")
    gmw_area_summary = pd.read_csv(OUT / "validation" / "gmw_2025_corrected_area_summary.csv")
    gmw_area_audit = pd.read_csv(OUT / "validation" / "gmw_2025_corrected_area_audit_by_source.csv")
    gmw_bcw_world = pd.read_csv(OUT / "validation" / "gmw_2025_spatial_bcw_world.csv")
    gmw_bcw_units = pd.read_csv(OUT / "validation" / "gmw_2025_spatial_bcw_by_unit.csv")
    spatial_moran = pd.read_csv(OUT / "validation" / "spatial_moran_comparison_2026-10-19.csv")
    spatial_models = pd.read_csv(OUT / "validation" / "spatial_models_comparison_2026-10-19.csv")
    spatial_samples = pd.read_csv(OUT / "validation" / "spatial_sample_audit_2026-10-19.csv")
    spatial_residuals = pd.read_csv(OUT / "validation" / "spatial_ols_residual_moran_2026-10-19.csv")
    spatial_sequence_moran = pd.read_csv(OUT / "validation" / "spatial_sequence_step1_moran_2026-10-19.csv")
    spatial_lm = pd.read_csv(OUT / "validation" / "spatial_sequence_step2_lm_tests_2026-10-19.csv")
    spatial_nested = pd.read_csv(OUT / "validation" / "spatial_sequence_step3_nested_tests_2026-10-19.csv")
    spatial_fit = pd.read_csv(OUT / "validation" / "spatial_sequence_model_fit_2026-10-19.csv")
    spatial_coefficients = pd.read_csv(OUT / "validation" / "spatial_sequence_model_coefficients_2026-10-19.csv")
    ibrahim = pd.read_csv(OUT / "validation" / "ibrahim_2pct_and_pledge_allocations_2026-10-19.csv")
    busch = pd.read_csv(OUT / "validation" / "busch_action_curve_country_scenarios_2026-10-19.csv")
    busch_status = pd.read_csv(OUT / "validation" / "busch_action_curve_status_summary_2026-10-19.csv")
    finance_summary = json.loads((OUT / "validation" / "finance_action_cost_comparison_2026-10-19.json").read_text(encoding="utf-8"))
    spatial_diagnostics = json.loads((OUT / "validation" / "spatial_analysis_diagnostics_2026-10-19.json").read_text(encoding="utf-8"))

    # Per-biome national area x clean rate.
    main_area = areas.loc[areas.variant.eq("documented_overlap_removed")]
    biome = main_area.groupby("biome", as_index=False).agg(area_ha=("area_ha", "sum"))
    biome = biome.merge(rates[["biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd"]], on="biome")
    biome["addition_gtco2_yr"] = biome.area_ha * biome.rate_tc_ha_yr_mean * (44 / 12) / 1e9
    biome["share_of_forest_additions_pct"] = 100 * biome.addition_gtco2_yr / biome.addition_gtco2_yr.sum()

    status = overlap.groupby("overlap_status", as_index=False).agg(
        units=("iso3", "size"), area_ha=("fra_mangroves_2025_ha", "sum"),
        removed_ha=("documented_forest_mangrove_area_ha", "sum"),
    )
    unresolved_codes = overlap.loc[overlap.overlap_status.isin(["unresolved_split", "no_exact_forest_split_verified"])]
    known_forest_codes = overlap.loc[overlap.overlap_status.eq("documented_all_forest"), "iso3"].tolist()
    m = len(spatial_moran)
    order = np.argsort(spatial_moran.p_permutation_two_sided.to_numpy())
    adjusted = np.maximum.accumulate(
        (m - np.arange(m)) * spatial_moran.p_permutation_two_sided.to_numpy()[order]
    )
    spatial_moran["p_holm_six_tests"] = np.nan
    spatial_moran.loc[order, "p_holm_six_tests"] = np.clip(adjusted, 0, 1)
    gmw_main = gmw_bcw_world.loc[
        gmw_bcw_world.case.eq("gmw_official_corrected_spatial_reassigned")
    ].iloc[0]
    hilmi_base = gmw_bcw_world.loc[gmw_bcw_world.case.eq("published_hilmi_area")].iloc[0]
    ibrahim_global_annual = float(ibrahim.ibrahim_2pct_usd2015_yr.sum(skipna=True))
    ibrahim_top10_share = float(ibrahim.nlargest(10, "gcw_usd2015_yr_mean").gcw_usd2015_yr_mean.sum() / ibrahim.gcw_usd2015_yr_mean.sum())
    ibrahim_top50_share = float(ibrahim.nlargest(50, "gcw_usd2015_yr_mean").gcw_usd2015_yr_mean.sum() / ibrahim.gcw_usd2015_yr_mean.sum())
    gmw_corrected_assigned = float(gmw_area_summary.spatial_assigned_corrected_ha.iloc[0])
    gmw_corrected_unassigned = float(gmw_area_summary.spatial_unassigned_corrected_ha.iloc[0])
    gmw_factor = float(gmw_area_summary.documented_factor.iloc[0])
    no_vector = pd.read_csv(DATA / "derived" / "forest_areas.csv")
    no_vector = no_vector.loc[no_vector.year.astype(str).eq("2025") & no_vector.mangroves.gt(0), ["iso3", "mangroves"]]
    no_vector = no_vector.merge(gmw[["iso3", "gmw_2025_mangrove_area_ha"]], on="iso3", how="left")
    no_vector = no_vector.loc[no_vector.gmw_2025_mangrove_area_ha.isna()]

    # Rank and concentration statistics use accounting units with observed components.
    gini_gcw = gini(gcw.gcw_usd2015_yr_mean.dropna())
    gini_bcw = gini(ncw.bcw_usd2015_yr_mean.dropna())
    paired_ncw = ncw.loc[ncw.has_gcw & ncw.has_bcw]
    gini_ncw = gini(paired_ncw.ncw_usd2015_yr_mean)
    top10_gcw = gcw.nlargest(10, "gcw_usd2015_yr_mean").gcw_usd2015_yr_mean.sum() / gcw.gcw_usd2015_yr_mean.sum()
    bcw_valid = ncw.dropna(subset=["bcw_usd2015_yr_mean"])
    top10_bcw = bcw_valid.nlargest(10, "bcw_usd2015_yr_mean").bcw_usd2015_yr_mean.sum() / bcw_valid.bcw_usd2015_yr_mean.sum()
    top10_ncw = paired_ncw.nlargest(10, "ncw_usd2015_yr_mean").ncw_usd2015_yr_mean.sum() / paired_ncw.ncw_usd2015_yr_mean.sum()

    r1 = gcw.dropna(subset=["gcw_usd2015_yr_mean", "gdp"]).query("gdp > 0 and gcw_usd2015_yr_mean > 0").copy()
    rho_gdp, p_gdp = stats.spearmanr(r1.gcw_usd2015_yr_mean, r1.gdp)
    r1["gcw_gdp_pct"] = 100 * r1.gcw_usd2015_yr_mean / r1.gdp
    ratio_by_group = {
        group: r1.loc[r1.groups.eq(group), "gcw_gdp_pct"].dropna().to_numpy()
        for group in GROUP_ORDER
    }
    ratio_by_group = {key: values for key, values in ratio_by_group.items() if len(values) > 2}
    kw_h, kw_p = stats.kruskal(*ratio_by_group.values())
    mw_rows = []
    keys = list(ratio_by_group)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            u, p = stats.mannwhitneyu(ratio_by_group[a], ratio_by_group[b], alternative="two-sided")
            mw_rows.append({"group_a": a, "group_b": b, "U": u, "p_raw": p})
    mw = pd.DataFrame(mw_rows).sort_values("p_raw").reset_index(drop=True)
    if len(mw):
        m = len(mw)
        mw["p_holm"] = np.clip(np.maximum.accumulate((m - np.arange(m)) * mw.p_raw.to_numpy()), 0, 1)

    # Nullable booleans must be filtered explicitly: bool(np.nan) is True in
    # Python, which incorrectly counted non-reporting units as covered.
    covered = erosion.loc[erosion.reported_deforestation.eq(True)].copy()
    loss_gini = gini(covered.loss_tco2_mean)
    loss_value_coverage = covered.loss_usd_mean.sum() / gcw.gcw_usd2015_yr_mean.sum()
    rho_erosion, p_erosion = stats.spearmanr(
        covered.loc[covered.loss_usd_mean.gt(0) & covered.gcw_usd2015_yr_mean.gt(0), "gcw_usd2015_yr_mean"],
        covered.loc[covered.loss_usd_mean.gt(0) & covered.gcw_usd2015_yr_mean.gt(0), "erosion_pct_of_gcw"],
    )
    loss_gc = covered.dropna(subset=["gdp"]).copy()
    loss_gc["domestic_cost_150"] = loss_gc.loss_tco2_mean * 150.0
    loss_gc["gdp_shared_cost_150"] = loss_gc.domestic_cost_150.sum() * loss_gc.gdp / loss_gc.gdp.sum()
    gini_domestic = gini(loss_gc.domestic_cost_150)
    gini_shared = gini(loss_gc.gdp_shared_cost_150)

    # FRA deforestation time series, global reported totals, Sen slope and MK test.
    fra_zip = DATA / "raw" / "environmental" / "forest" / "fra" / "fra2025_bulk_WO.zip"
    with zipfile.ZipFile(fra_zip) as archive:
        name = next(item for item in archive.namelist() if "1d_deforestation" in item)
        defor = pd.read_csv(archive.open(name))
    defor = defor.dropna(subset=["iso3"]).copy()
    for col in INTERVALS:
        defor[col] = pd.to_numeric(defor[col], errors="coerce")
    world_defor = defor[INTERVALS].sum()
    sen_slope, _, sen_low, sen_high = stats.theilslopes(world_defor.to_numpy(dtype=float), MIDPOINTS)
    mk_s, mk_p = mann_kendall(world_defor.to_numpy(dtype=float))
    trend_table = world_defor.rename_axis("fra_interval").reset_index(name="reported_deforestation_kha_per_year")
    trend_table["midpoint_year"] = MIDPOINTS
    trend_table["reported_deforestation_mha_per_year"] = trend_table["reported_deforestation_kha_per_year"] / 1000.0
    trend_table.to_csv(OUT / "tables" / "manuscript" / "Supplementary_deforestation_trend.csv", index=False)
    defor["2010_2020_kha_yr"] = defor[["2010-2015", "2015-2020"]].mean(axis=1)
    top_deforestation = defor.nlargest(10, "2010_2020_kha_yr")[["iso3", "name", "2010_2020_kha_yr"]]

    # Top national values joined into one complete table (all available rows retained).
    national = ncw.merge(
        gcw[["iso3", "uptake_tco2_yr_mean", "gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95", "gcw_share_of_gdp"]],
        on="iso3", how="left", suffixes=("", "_gcw"),
    ).merge(
        erosion[["iso3", "loss_tco2_mean", "loss_usd_mean", "erosion_pct_of_gcw", "loss_pct_of_gdp", "reported_deforestation"]],
        on="iso3", how="left",
    )
    national["gcw_bn_usd2015_yr"] = national.gcw_usd2015_yr_mean / 1e9
    national["bcw_bn_usd2015_yr"] = national.bcw_usd2015_yr_mean / 1e9
    national["ncw_bn_usd2015_yr"] = national.ncw_usd2015_yr_mean / 1e9
    national["lost_capacity_mtco2_yr"] = national.loss_tco2_mean / 1e6
    national["lost_value_bn_usd2015_yr"] = national.loss_usd_mean / 1e9
    national["gcw_gdp_pct"] = 100 * national.gcw_share_of_gdp
    national = national.sort_values("ncw_usd2015_yr_mean", ascending=False)

    sections: list[str] = []
    add = sections.append
    add("BNC2 - INVENTAIRE COMPLET DES RÉSULTATS DISPONIBLES")
    add("Calculs: 2026-10-19; vérification de la version GCB: 2026-10-20. Pipeline, scénarios et notebooks 03-06 recalculés après remplacement effectif de l'aire de mangrove BCW par GMW 2025 corrigé et retrait sélectif des seuls recouvrements FRA explicitement documentés. Le manuscrit principal et ses figures intégrées ne sont pas modifiés ici.")
    add("")
    add("0. Guide de lecture - ordre de priorité éditoriale, du plus secondaire au plus central")
    add("Ce classement sert à organiser le récit; il ne mesure pas l'importance scientifique intrinsèque. Un résultat non significatif après correction de tests ne signifie pas qu'il est sans intérêt: il indique que l'hypothèse statistique correspondante n'est pas rejetée au seuil retenu.")
    add("1) Contrôles et limites: recouvrement FRA mangrove/forêt non résolu, discordances et résidus GMW, couverture marine et de déforestation, différences de millésime et incertitudes non propagées. À traiter dans Methods, supplément et Discussion selon leur rôle.")
    add("2) Résultats secondaires et sensibilités: écart-type spatial des pixels, taux GFW avec/sans pixels source mangrove, Route A FAOSTAT, fractions de valorisation, variantes de superficie GMW, scénarios de baisse BCW, prix uniformes historiques et scénario Rickels M4. Les conserver dans l'inventaire/supplément avec leurs hypothèses; ne pas les présenter comme estimations observées.")
    add("3) Descriptifs et distributions: valeurs nationales exhaustives, classements, agrégats continentaux et économiques, Gini, Spearman, Kruskal-Wallis/Mann-Whitney, profils de bilan et tendance FRA sur cinq intervalles. Ces éléments décrivent des distributions ou associations, sans causalité.")
    add("4) Estimation centrale: quatre taux forestiers par biome, 14.733 GtCO2/an d'ajouts estimés à la biomasse vivante, GCW, BCW et NCW annuels, avec les intervalles et leurs limites. Ce bloc porte l'échelle centrale des comptes.")
    add("5) Déforestation: capacité annuelle d'ajout à la biomasse qui n'est plus fournie, valeur associée, intensité relative, différences nationales/groupes et cumuls sous scénario constant. Ce n'est pas l'émission instantanée du carbone déjà stocké.")
    add("6) Analyse spatiale: les trois résultats (perte absolue, perte/GCW et GCW/PIB), chacun sous Queen et kNN-5, aux étapes Moran, LM, LR et AIC/BIC. Les coefficients sont descriptifs; les rangs AIC/BIC ne décident pas seuls du modèle final.")
    add("7) Finance climatique: scénario principal d'allocation d'Ibrahim (2% du GCW), puis comparaison complémentaire et partielle aux courbes d'action de Busch. Le premier est une règle de répartition; le second un raccordement incomplet à des coûts d'actions, et les deux ne mesurent pas le même besoin.")
    add("")
    add("Vérification GCB au 2026-10-20: le Data Hub officiel présente le Global Carbon Budget 2025 comme l'édition la plus récente; il met à disposition les émissions fossiles nationales v2025 et les émissions nationales de changement d'usage des terres v2025. Le papier de référence couvre les séries historiques jusqu'en 2024 et projette 2025. Les comparaisons d'émissions de cet inventaire restent au millésime 2023 actuellement utilisé (GCB 2024 via Our World in Data); aucune nouvelle extraction/re-calcul GCB n'a été fait ici. Avant le gel du résultat, contrôler la comparabilité de la série historique 2023 v2025 et recalculer les résultats dépendants si elle est harmonisable. Sources: https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/ ; https://essd.copernicus.org/articles/18/3211/2026/.")
    add("")
    add("1. Périmètre et lecture des chiffres")
    add("GCW forestier = ajouts annuels estimés à la biomasse vivante aérienne et souterraine × GSCC. Les sorties de biomasse vivante ne sont pas soustraites de cet indicateur; la déforestation est un résultat distinct de perte de capacité. Les intervalles P05-P95 monétaires du GCW propagent les tirages GSCC seulement; les taux Gibbs/GFW et les surfaces restent fixes. L’écart-type spatial des pixels est une sensibilité déterministe, pas un intervalle de confiance.")
    add("BCW = flux côtiers et pompe biologique du large tels que comptabilisés dans Hilmi et al., avec seule la superficie mangrove remplacée par GMW 2025. Le taux d'enfouissement Hilmi/Alongi et les autres compartiments marins restent tels quels. NCW = GCW + BCW.")
    add("")
    add("2. Valeurs mondiales par composante")
    gtab = global_ecosystems.copy()
    gtab_out = gtab.copy()
    for index, row in gtab_out.iterrows():
        divisor = 1e12 if row.unit == "US$2015/yr" else 1e9
        for col in ["value_mean", "value_sd", "value_p05", "value_p50", "value_p95"]:
            if col in gtab_out:
                gtab_out.loc[index, col] /= divisor
    add("Tableau suivant: tCO2/yr en GtCO2/yr; US$2015/yr en trillions de dollars par an. P05/P95 sont les quantiles des tirages monétaires lorsque l'incertitude est propagée.")
    add(tsv(gtab_out))
    add("")
    add("3. Quatre biomes forestiers: surfaces et taux")
    add("Les surfaces sont FRA 2025 × parts spatiales GEZ; les taux propres à chaque biome viennent de l'agrégation pondérée par aire des pixels Gibbs/GFW 2001-2023 après exclusion du code source mangrove. La surface A_b dans le fichier des taux est la surface valide des pixels source servant au dénominateur des taux, et n'est pas la surface nationale utilisée dans le calcul de GCW.")
    rates_and_biomes = biome.rename(columns={
        "area_ha": "area_fra_gez_ha", "rate_tc_ha_yr_mean": "rate_mean_tC_ha_yr",
        "rate_tc_ha_yr_spatial_sd": "pixel_spatial_SD_tC_ha_yr", "addition_gtco2_yr": "gross_addition_GtCO2_yr",
    })
    add(tsv(rates_and_biomes))
    add(f"Total central: {biome.addition_gtco2_yr.sum():.6f} GtCO2/an. Part tropicale+subtropicale: {biome.loc[biome.biome.isin(['tropical','subtropical']), 'share_of_forest_additions_pct'].sum():.2f}%.")
    add("")
    add("4. Mise à jour GMW et harmonisation FRA")
    add(f"GMW v4.1.12, carte annuelle 2025: facteur officiel de correction d'aire={gmw_factor:.4f}; aire corrigée de source={gmw_area_summary.published_corrected_total_ha.iloc[0]:,.2f} ha. L'intersection et la réattribution produisent {gmw_corrected_assigned:,.2f} ha dans {int(gmw_area_summary.spatial_accounting_units.iloc[0])} unités; {gmw_corrected_unassigned:,.2f} ha restent sans attribution admissible. Le désaccord principal de référentiels concerne 2,745.31 ha codés Guyana par GMW mais tombant dans le polygone Venezuela de la couche de frontières; ce n'est pas une conclusion de souveraineté.")
    add(f"Le remplacement effectif donne {gmw_main.area_ha_assigned:,.0f} ha et une valeur de mangrove de {gmw_main.mean_mangrove_value_billion_usd2015_yr:.3f} milliards US$2015/an. Le cas Hilmi d'origine donne {hilmi_base.area_ha_assigned:,.0f} ha et 57.512 milliards/an. La valeur moyenne de BCW passe de {hilmi_base.mean_total_bcw_billion_usd2015_yr:,.3f} à {gmw_main.mean_total_bcw_billion_usd2015_yr:,.3f} milliards/an; seul le poste mangrove est remplacé, les taux côtiers et océaniques publiés restent inchangés.")
    add("Unités FRA avec une superficie mangrove positive mais sans polygone GMW dans la table spatiale actuelle: " + ", ".join(f"{r.iso3} ({r.mangroves:.0f} ha FRA)" for r in no_vector.itertuples()) + ". Le résultat main utilise zéro hectare cartographié pour ces codes; cette différence de couverture/source est à signaler, en particulier pour SHN.")
    add("Décision de recouvrement FRA: soustraction seulement quand un rapport national donne la même superficie de classe que la catégorie FRA 2025 et ventile 100% de cette classe en Forest. Retirés: " + ", ".join(known_forest_codes) + f"; total {overlap.documented_forest_mangrove_area_ha.sum():,.0f} ha.")
    add("Les rapports ne documentent pas une ventilation Forest/OWL exploitable pour 3 cas ambigus (PAK, SHN, TCA) et 103 autres unités. Leur superficie brute totale retenue comme non résolue est " + f"{unresolved_codes.fra_mangroves_2025_ha.sum():,.0f} ha. LCA documente 220 ha en Other wooded land, qui n'est pas soustrait du total strict de forêt. Les 9 et LCA sont des constats tirés des crosswalks nationaux; KIR porte un indicateur FRA source 'Desk study', donc cette preuve est de qualité plus faible.")
    add("Ventilation de l'audit par statut:")
    add(tsv(status))
    add("")
    add("5. Répartition géographique et groupes économiques")
    add("Continent: sommes des valeurs par tirage, résumées ensuite. Unclassified indique des unités sans groupe/continent reconnu; les composantes manquantes ne sont pas imputées.")
    add("Continent - milliards US$2015/an (moyennes et part mondiale)")
    cont = continents.copy()
    for component in ["gcw", "bcw", "ncw"]:
        cont[f"{component}_mean_bn"] = cont[f"{component}_usd2015_yr_mean"] / 1e9
        cont[f"{component}_share_pct"] = 100 * cont[f"{component}_usd2015_yr_share_of_world"]
    keep_cont = ["continent", "gcw_mean_bn", "gcw_share_pct", "bcw_mean_bn", "bcw_share_pct", "ncw_mean_bn", "ncw_share_pct"]
    add(tsv(cont, keep_cont))
    add("Groupe économique - milliards US$2015/an (moyennes et part mondiale)")
    grp = groups.copy()
    for component in ["gcw", "bcw", "ncw"]:
        grp[f"{component}_mean_bn"] = grp[f"{component}_usd2015_yr_mean"] / 1e9
        grp[f"{component}_share_pct"] = 100 * grp[f"{component}_usd2015_yr_share_of_world"]
    add(tsv(grp, ["groups", "gcw_mean_bn", "gcw_share_pct", "bcw_mean_bn", "bcw_share_pct", "ncw_mean_bn", "ncw_share_pct"]))
    add("Profils et soldes comptables, selon les méthodes actuelles (compte GCW seul / GCW+BCW moins émissions CO2 nationales 2023, hors usage des terres dans la source d'émissions):")
    add(tsv(group_profiles))
    add("")
    add("6. Résultats nationaux complets")
    add("Une ligne par unité comptable du tableau NCW (267 lignes). Valeurs monétaires en milliards US$2015/an, flux et pertes en MtCO2/an; le champ GCW/PIB est en pourcentage. NA = donnée manquante, pas zéro.")
    country_cols = ["iso3", "name", "continent", "groups", "gcw_bn_usd2015_yr", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95", "bcw_bn_usd2015_yr", "ncw_bn_usd2015_yr", "forest_share_of_ncw", "gcw_gdp_pct", "ncw_per_capita_usd2015", "lost_capacity_mtco2_yr", "lost_value_bn_usd2015_yr", "erosion_pct_of_gcw", "reported_deforestation"]
    national_out = national.copy()
    national_out["gcw_usd2015_yr_p05"] /= 1e9
    national_out["gcw_usd2015_yr_p95"] /= 1e9
    national_out["forest_share_of_ncw"] *= 100
    add(tsv(national_out, country_cols))
    add("")
    add("7. Concentration, correlations et tests entre groupes")
    add(f"Gini non pondéré des valeurs par unité, cohortes disponibles: GCW={gini_gcw:.4f} (n={gcw.gcw_usd2015_yr_mean.notna().sum()}); BCW={gini_bcw:.4f} (n={ncw.bcw_usd2015_yr_mean.notna().sum()}); NCW={gini_ncw:.4f} (unités avec GCW et BCW, n={len(paired_ncw)}). Gini de la capacité annuelle perdue déclarée={loss_gini:.4f} (n={len(covered)}).")
    add(f"Part des dix premières unités dans leur total couvert: GCW={100*top10_gcw:.2f}%; BCW={100*top10_bcw:.2f}%; NCW={100*top10_ncw:.2f}%. Ces indicateurs de concentration sont non pondérés par population.")
    add(f"Spearman GCW-PIB: rho={rho_gdp:.4f}, p={p_gdp:.4g}, n={len(r1)}. C'est une association descriptive entre grandeurs toutes deux dépendantes de la taille du pays, pas un effet causal.")
    add(f"Kruskal-Wallis de GCW/PIB entre groupes économiques: H={kw_h:.4f}, p={kw_p:.4g}, groupes={', '.join(ratio_by_group)}. Comparaisons Mann-Whitney bilatérales avec correction de Holm:")
    add(tsv(mw) if len(mw) else "Aucune comparaison disponible.")
    add(f"Spearman GCW et intensité d'érosion (part du GCW annualisée correspondant à la capacité perdue; seules observations strictement positives): rho={rho_erosion:.4f}, p={p_erosion:.4g}. Le total de la perte représente {100*loss_value_coverage:.3f}% du GCW mondial, mais la déforestation n'est déclarée que par 139 unités.")
    add("Top 10 valeurs GCW:")
    add(tsv(gcw.nlargest(10, "gcw_usd2015_yr_mean")[["iso3", "name", "groups", "gcw_usd2015_yr_mean", "gcw_share_of_gdp"]]))
    add("Top 10 valeurs BCW:")
    add(tsv(bcw_valid.nlargest(10, "bcw_usd2015_yr_mean")[["iso3", "name", "groups", "bcw_usd2015_yr_mean"]]))
    add("Top 10 valeurs NCW:")
    add(tsv(top_ncw))
    add("")
    add("8. Déforestation et perte de capacité annuelle")
    add(f"La moyenne FRA des taux rapportés sur 2010-2015 et 2015-2020 représente {defor['2010_2020_kha_yr'].sum()/1000:.3f} Mha/an dans le total des données rapportées. Couverture de l'analyse de capacité: {len(covered)} unités sur {gcw.gcw_usd2015_yr_mean.notna().sum()} unités à GCW disponible; ces absences sont manquantes, pas zéro.")
    add(f"Les 139 déclarants cumulent {covered.loss_tco2_mean.sum()/1e6:.6f} MtCO2/an de capacité d'ajout à la biomasse vivante qui ne serait plus fournie par les hectares convertis sous l'hypothèse de taux et de biome utilisés; valeur GSCC moyenne={covered.loss_usd_mean.sum()/1e9:.6f} milliards US$2015/an. Cette valeur ne mesure pas les émissions du carbone des arbres abattus.")
    add(f"Intensité agrégée parmi les seuls déclarants: {100*covered.loss_usd_mean.sum()/covered.gcw_usd2015_yr_mean.sum():.4f}% du GCW de ces unités. Les montants de perte par groupe, avec 2 unités potentiellement sans groupe classé, sont:")
    loss_group = erosion.groupby("groups", dropna=False).agg(
        units_reporting=("loss_tco2_mean", lambda s: int(s.notna().sum())),
        loss_mtco2_yr=("loss_tco2_mean", lambda s: s.sum()/1e6),
        loss_value_bn_usd2015_yr=("loss_usd_mean", lambda s: s.sum()/1e9),
        median_erosion_pct=("erosion_pct_of_gcw", "median"),
    ).reset_index()
    loss_group["groups"] = loss_group["groups"].fillna("Unclassified")
    add(tsv(loss_group))
    add("Plus grands pays en capacité perdue et en intensité de perte:")
    add("Perte de capacité, top 10:")
    add(tsv(covered.nlargest(10, "loss_tco2_mean")[["iso3", "name", "groups", "loss_tco2_mean", "loss_usd_mean", "erosion_pct_of_gcw"]]))
    add("Intensité, top 10, parmi les déclarants ayant GCW positif:")
    add(tsv(covered.loc[covered.gcw_usd2015_yr_mean.gt(0)].nlargest(10, "erosion_pct_of_gcw")[["iso3", "name", "groups", "erosion_pct_of_gcw", "loss_tco2_mean"]]))
    add("Tendance mondiale des taux FRA déclarés par intervalle (somme des valeurs disponibles; périodes de durée différente, donc les points représentent des taux annuels dans chaque intervalle):")
    add(tsv(world_defor.rename_axis("period").reset_index(name="sum_reported_kha_yr")))
    add(f"Theil-Sen={sen_slope/1000:.3f} Mha/an² (IC non paramétrique approx. 95% {sen_low/1000:.3f} à {sen_high/1000:.3f} Mha/an²); Mann-Kendall S={mk_s:.0f}, p={mk_p:.4f}. Cinq intervalles seulement; résultat descriptif, et l'échantillon déclaré peut varier d'un intervalle à l'autre.")
    add("Dix plus grandes surfaces annuelles de déforestation rapportées pour la moyenne 2010-2020:")
    add(tsv(top_deforestation))
    add("")
    add("9. Valorisation conditionnelle et coûts d'abattement")
    add("Sensibilité de valorisation: appliquer une fraction f au GCW calculé; ce test ne mesure pas la part du carbone réellement retenue pendant une durée observée. Montants en billions US$2015/an:")
    add(tsv(valuation_fraction))
    add("Prix illustratifs de compensation actuellement présents dans le tableau historique (50/150/400 US$ par tCO2): ils donnent un coût de 1.741/5.224/13.930 Md US$2015/an pour la capacité perdue recalculée. Ils restent des scénarios de prix communs, pas des coûts observés d'actions locales. Une comparaison distincte avec les courbes publiées de Busch et al. (2024) est résumée ci-dessous.")
    add(f"Scénario principal d'Ibrahim recalculé sur toutes les unités GCW (n={ibrahim.gcw_usd2015_yr_mean.notna().sum()}): F_i=0.02×G_i donne {ibrahim_global_annual/1e9:.3f} milliards US$2015/an, distribués en proportion du GCW national. Les 10 premières unités couvrent {100*ibrahim_top10_share:.2f}% du GCW; les 50 premières {100*ibrahim_top50_share:.2f}%. Les montants pour les 139 déclarants de déforestation ne représentent qu'une sous-cohorte et ne doivent pas remplacer le total de l'allocation.")
    add("Rickels M4, scénario distinct sans échange de permis: la réplication reproduit exactement le coût de référence pour 146 régions. Avec la perte forestière recalculée, la table inclut 92 pays en base lorsque q=0; la contrainte de faisabilité laisse 90 déclarants dans les scénarios de forte ambition à q=1. Pour les six projections macroéconomiques d'ambition haute, la perte couverte est 34.002 MtCO2/an et les surcoûts q=1 vont de ")
    high_full = abatement.loc[abatement.ndc_ambition.eq("high") & abatement.replacement_fraction.eq(1.0)]
    add(", ".join(f"{row.macro_scenario}: {row.incremental_cost_billion_source_usd:.3f}" for row in high_full.itertuples()) + " milliards dans l'unité monétaire du classeur source. Ce n'est ni un coût de remplacement physique d'une forêt ni un financement effectivement dû. Le cours/année monétaire du classeur n'est pas encore harmonisé aux US$2015.")
    add("Climate finance d'Ibrahim - reconstruction fidèle de son document: (1) le texte prend un GCW central d'environ 8.1 T$/an et applique 2%, soit 162 Md$/an; le taux de 2% n'est pas dérivé de coûts d'actions. (2) Il classe les pays par G_i et rapporte des parts des dix et cinquante premiers. Le texte dit aussi que les 224 autres pays représentent 44.3%, ce qui ne concorde pas: 44.3% est le complément des dix premiers à 55.7%, alors que le complément des cinquante premiers à 90.4% est 9.6%. (3) Il pose M=P×T; avec P=100 Md$/an et T=30 ans, M=3 T$ cumulés. Il attribue A_i=(G_i/G)×M et calcule Gap_i=G_i−A_i. Si G_i est le GCW annuel du présent papier, soustraire l'allocation cumulée sur trente ans mélange un montant annuel (USD/an) et un montant cumulé (USD), sauf si les deux sont convertis sur une même période avec une règle explicite. Cette différence dépend aussi d'une allocation proportionnelle hypothétique, pas d'un budget national d'actions. (4) Le modèle d'inaction pose L_t=G(1+r)^t; le modèle d'action soustrait le paiement annuel P après croissance, et celui de l'action retardée laisse croître G pendant d années avant les versements. Les paramètres r, P et d ne sont pas renseignés dans le texte extrait; le passage de 8 T$ à environ 36 T$ en cinquante ans impliquerait r≈3.05%/an si cette croissance est composée. La formule d'extra-cost G[(1+r)^d−1] est une hausse composée d'une valeur supposée, pas une mesure observée des dommages évités. Le document annonce N=237 pour les données, N=234 pour les valeurs nationales, puis 224 pays restants; ces périmètres doivent être réconciliés. Le 1.9 T$ CPI est un flux mondial annuel multi-secteurs en 2023, pas une mesure comparable à un besoin forestier estimé avec 2% du GCW. Ces calculs ne donnent donc ni un besoin de financement observé, ni un déficit de financement mesuré, ni un droit national à paiement. Référence comparative: Austin et al. (2025) modélisent des coûts d'actions forestières permettant d'atteindre des cibles NDC régionales et estiment 20-72 Md$/an en 2030; l'estimand est un coût d'action, distinct du GCW. Références publiques: https://www.nature.com/articles/s41467-025-61657-6; https://www.climatepolicyinitiative.org/wp-content/uploads/2000/06/compressed_Global-Landscape-of-Climate-Finance-2025.pdf; https://unfccc.int/news/cop29-un-climate-conference-agrees-to-triple-finance-to-developing-countries-protecting-lives-and.")
    add("Comparaison complémentaire avec les courbes d'actions forestières de Busch et al. (2024): Busch estime des coûts de régénération naturelle et de plantations dans des zones admissibles de pays à revenu faible/intermédiaire, avec courbes cumulées sur 30 ans, actualisation de 5%, et US$2020/tCO2. Le rapprochement suppose que la capacité annuelle perdue (34.825 MtCO2/an chez 105 déclarants positifs) persiste trente ans; le facteur de valeur actualisée est 15.372451. Une courbe est disponible pour 60/105 déclarants positifs. Pour 46 unités, la cible cumulée entre dans l'offre publiée (17.045 MtCO2/an, 48.9% de la perte déclarée); 14 dépassent l'offre à 100 US$2020/tCO2, 45 n'ont pas de courbe, 18 entrent dans une zone de prix non positif et 16 sont à ou sous -20. Seuls 12 cas donnent une tranche positive; la médiane des bornes de prix est 2.5-7.5 US$2020/tCO2. Le proxy de transfert uniforme pour ces 12 cas est 0.73-7.59 M US$2015/an; il ne représente ni coût intégré des projets ni besoin mondial de financement. Le flux carbone et le périmètre des actions de restauration ne sont pas équivalents à la capacité annuelle de la forêt existante. Sources: https://www.nature.com/articles/s41558-024-02068-1; https://zenodo.org/records/11372275.")
    add("")
    add("10. Analyse spatiale exploratoire: séquence en quatre étapes")
    add("Les trois résultats sont: perte annuelle absolue de capacité (MtCO2/an), perte relative au GCW (%), et GCW/PIB (%). Les modèles utilisent log1p(y), log PIB/habitant, log surface forestière et part des biomes tropicaux+subtropicaux. Les échantillons sont les mêmes dans toutes les spécifications d'un résultat. La matrice Queen teste les frontières terrestres; le kNN symétrisé k=5 relie aussi les îles à leurs voisins géographiques les plus proches.")
    add("Les tests de la branche Panel dessinée sous les étapes spatiales (effets aléatoires, effets fixes, Hausman) ne s'appliquent pas: les fichiers ont une observation transversale par pays/territoire, sans dimension unité-année.")
    add("Étape 1 - Moran global est calculé à la fois sur y transformé et sur les résidus OLS. Les pertes de capacité ne montrent pas de regroupement qui survive à Holm sous les deux matrices; l'intensité relative et GCW/PIB présentent un Moran positif corrigé sous Queen et kNN. Pour GCW/PIB, le Moran positif des résidus OLS reste significatif sous les deux matrices. Les valeurs complètes figurent dans la table Step 1 ci-dessous.")
    robust_lm_sig = spatial_lm.loc[spatial_lm.test.isin(["robust_LM_lag", "robust_LM_error"]) & spatial_lm.p_holm_across_six_cases.lt(0.05)]
    if len(robust_lm_sig):
        add("Étape 2 - Les seuls tests LM robustes restant significatifs après correction de Holm sont: " + "; ".join(f"{r.outcome}, {r.weight}, {r.test}: stat={r.statistic:.3f}, p ajusté={r.p_holm_across_six_cases:.4g}" for r in robust_lm_sig.itertuples()) + ".")
    else:
        add("Étape 2 - Aucun des tests LM robustes ne reste significatif après correction de Holm.")
    add("Les LM simples et les tests joints SARMA/SDM sont également rapportés. Les LM sont des diagnostics après OLS, et ne constituent pas à eux seuls une sélection finale du modèle.")
    add("Étape 3 - Les tests du rapport de vraisemblance comparent SDM à SAR (H0: tous les coefficients WX=0), SDEM à SEM (H0: tous les WX=0), et GNS à SDM (H0: lambda=0). L'ajout de WX est soutenu sous les deux matrices uniquement pour GCW/PIB après Holm; l'ajout du terme d'erreur GNS à SDM l'est sous Queen, mais pas sous kNN. Aucune comparaison de l'arbre ne survit à Holm pour les deux résultats de déforestation.")
    add("Étape 4 - Le classement AIC/BIC est calculé pour chaque résultat et matrice. AIC et BIC ne désignent pas toujours le même candidat, et les classements diffèrent entre Queen et kNN. Le tableau présente leurs minima mécaniques sans en faire une sélection scientifique définitive.")
    add("Les coefficients et tests sont descriptifs. Les diagnostics LM et les vraisemblances gaussiennes reposent sur des hypothèses d'innovations homoskédastiques; les erreurs-types HC3 de l'OLS ne changent pas les hypothèses des tests LM. Les coefficients ne démontrent pas de causalité. La Queen laisse 21 isolats dans les échantillons de déforestation et 53 pour GCW/PIB; le kNN relie les îles en leur attribuant parfois des voisins distants ou séparés par la mer.")
    add("")
    add("11. Tables spatiales exhaustives")
    add("11.1 Step 1 - Moran de y transformé et des résidus OLS; p-values brutes et Holm par mesure")
    add(tsv(spatial_sequence_moran))
    add("11.2 Step 2 - Tests LM après OLS: lag, error, formes robustes, SARMA joint et SDM joint; p-values brutes et Holm")
    add(tsv(spatial_lm))
    add("11.3 Step 3 - Tests LR entre spécifications emboîtées; p-values brutes et Holm")
    add(tsv(spatial_nested))
    add("11.4 Step 4 - Log-vraisemblance, AIC/BIC, paramètres spatiaux, convergence et rangs par critère")
    add(tsv(spatial_fit))
    add("11.5 Coefficients et erreurs-types ML pour OLS, SAR, SEM, SDM, SDEM et GNS")
    add(tsv(spatial_coefficients))
    add("11.6 Tables historiques OLS-HC3/SAR/SEM, Moran séparés des résidus OLS et échantillons")
    add(tsv(spatial_models))
    add(tsv(spatial_residuals))
    add(tsv(spatial_samples))
    add("Diagnostic des frontières: " + f"{spatial_diagnostics['units_with_geometry']} unités avec géométrie; unité sans polygone={','.join(spatial_diagnostics['units_without_geometry'])}; Queen complet: {spatial_diagnostics['queen']['n_islands']} isolats et {spatial_diagnostics['queen']['n_components']} composantes; kNN symétrisé k={spatial_diagnostics['knn']['k']} en {spatial_diagnostics['knn']['distance_crs']}; permutations={spatial_diagnostics['permutations']}, seed={spatial_diagnostics['seed']}. Les matrices des échantillons sont induites par les données disponibles.")
    add("Minima mécaniques AIC par résultat et matrice:")
    add(tsv(spatial_fit.loc[spatial_fit.groupby(["outcome", "weight"]).aic.idxmin(), ["outcome", "weight", "model", "aic", "bic"]].sort_values(["outcome", "weight"])))
    add("Minima mécaniques BIC par résultat et matrice:")
    add(tsv(spatial_fit.loc[spatial_fit.groupby(["outcome", "weight"]).bic.idxmin(), ["outcome", "weight", "model", "aic", "bic"]].sort_values(["outcome", "weight"])))
    add("")
    add("11.4 Allocation Ibrahim par toutes les unités GCW (allocation annuelle et part du pledge cumulé séparées)")
    add("F_i=2%×G_i pour toutes les unités ayant une valeur GCW. La colonne `share_of_30yr_100bn_pledge_usd_cumulative` répartit séparément 100 milliards US$/an sur 30 ans, soit 3 000 milliards cumulés; elle n'est pas soustraite de G_i annuel.")
    add(tsv(ibrahim))
    add("11.5 Courbes d'action Busch par déclarant de perte positive et statut global")
    add("Une ligne par unité parmi les 105 déclarants où la perte de capacité estimée est strictement positive. Les quantités cumulées cibles supposent 30 ans de persistance et le facteur d'actualisation de 5%; le classement reste dans le domaine publié, sans extrapolation.")
    add(tsv(busch_status))
    add(tsv(busch))
    add("11.6 Remplacement GMW et comparaison des six conventions d'aire")
    add("Le cas principal est `gmw_official_corrected_spatial_reassigned`; les autres lignes sont des variantes de comparaison, pas des résultats principaux.")
    add(tsv(gmw_bcw_world))
    add("Aires GMW corrigées par unité de compte:")
    add(tsv(gmw))
    add("Audit des aires corrigées au code pays source (incluant les facteurs, sommes raster et résidus):")
    add(tsv(gmw_area_audit))
    add("Aires BCW GMW corrigées par unité et différences monétaires versus l'aire Hilmi:")
    add(tsv(gmw_bcw_units))
    add("Audit complet du chevauchement FRA mangrove/Forest/Other wooded land:")
    add(tsv(overlap))
    add("11.7 Autres résultats nationaux complets et sensibilités")
    add("Taux estimés hors pixels de mangrove, comparaison avec les taux incluant ces pixels, et caractéristiques de la grille source:")
    rate_pair = rates.merge(rates_with_mangroves[["biome", "rate_tc_ha_yr_mean"]].rename(columns={"rate_tc_ha_yr_mean": "rate_including_mangroves_tC_ha_yr"}), on="biome", validate="one_to_one")
    add(tsv(rate_pair))
    add("Sensibilité par unité reposant sur l'écart-type spatial des pixels; ce n'est pas un intervalle de confiance:")
    add(tsv(uptake_spatial_sensitivity))
    add("Route A FAOSTAT, estimations nationales complémentaires:")
    add(tsv(uptake_faostat))
    add("Sensibilité de valorisation par unité aux fractions 25%, 33%, 50%, 75% et 100% du GSCC:")
    add(tsv(valuation_fraction_units))
    add("Scénarios Rickels M4 complets, conservés comme analyse distincte et non comme scénario principal décidé pour le récit actuel:")
    add(tsv(pd.read_csv(OUT / "validation" / "forest_abatement_no_trade_country_scenarios.csv")))
    add("")
    add("12. Sorties de référence dans le dépôt")
    add("Principales sorties actualisées: results/tables/table1_global_by_ecosystem.csv; table2_by_continent.csv; table3_by_group.csv; table4_top_territories.csv; results/country_level_gcw.csv; results/country_level_ncw.csv; data/derived/forest_area_by_biome.csv; data/derived/gfw_gibbs_biome_rates.csv; data/derived/fra_mangrove_forest_overlap_2025.csv; data/derived/gmw_2025_mangrove_area_by_unit.csv; results/tables/manuscript/Supplementary_country_level_erosion.csv; results/validation/forest_abatement_no_trade_summary.csv.")
    add("Le pipeline, les scripts complémentaires et les notebooks 03-06 ont été réexécutés. Les images des notebooks ont été régénérées dans leurs dossiers de sortie, mais aucune des quatre figures intégrées à PAPER.docx n'a été remplacée. La mise à jour du DOCX principal reste une étape séparée.")
    add("")
    add("Sources de méthodes: FAO FRA definitions (https://fra-data.fao.org/definitions/fra/2020/en/tad); FRA 2025 country reports (https://www.fao.org/forest-resources-assessment/fra-2025-country-reports/); GMW v4.1.12 (https://zenodo.org/records/21346457); Gibbs et al. 2025 (https://essd.copernicus.org/articles/17/1217/2025/); Rickels et al. 2024 (https://doi.org/10.1038/s43247-024-01674-3), data repository (https://github.com/wilmwilmsen/OceanValue); Austin et al. 2025 (https://www.nature.com/articles/s41467-025-61657-6); UNFCCC NCQG (https://unfccc.int/news/cop29-un-climate-conference-agrees-to-triple-finance-to-developing-countries-protecting-lives-and).")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {DEST}")


if __name__ == "__main__":
    main()
