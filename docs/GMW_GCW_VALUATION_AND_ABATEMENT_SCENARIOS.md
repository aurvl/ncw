# Méthodes harmonisation et scénarios économiques

Mise à jour au 19 octobre 2026. Le calcul principal utilise désormais les superficies GMW 2025 pour les mangroves de BCW et ne retire de FRA que les chevauchements mangrove-forêt documentés dans les rapports nationaux. Les passages marqués comme anciens tests ci-dessous restent utiles pour la traçabilité; ils ne décrivent plus le statut du calcul principal. Les figures du manuscrit sont gardées pour une mise à jour ultérieure.

## 1. Ce que donnent réellement FRA et GEZ

FRA 2025 donne pour chaque unité `i` une **surface forestière totale** `F_i` et une catégorie séparément rapportée « mangroves » `M_i`. Cette dernière comprend *forêt et autres terres boisées* : `M_i` n'est donc pas automatiquement la part de mangrove comprise dans `F_i`. Les quatre surfaces tropicale, subtropicale, tempérée et boréale du dépôt ne sont pas quatre variables FRA directement observées. Elles sont construites par `F_i × s_{i,b}`, où `s_{i,b}` vient du croisement entre les zones écologiques FAO GEZ 2010 et le masque forestier JRC 2020. La période, le masque, la définition de forêt et la résolution spatiale diffèrent de FRA 2025.

La décomposition exclusive désirée serait `F_i = A_{i,T} + A_{i,ST} + A_{i,Te} + A_{i,B} + A_{i,mangrove forestière}`. Elle n'est établie que si la part des mangroves **effectivement incluse dans la forêt FRA** est connue. Une déclaration du total `M_i` ne suffit pas. Certains rapports nationaux détaillent les classes d'origine : le Brésil affecte explicitement la classe *Manguezal* de son point national 2020 à la forêt. Il faut vérifier pays, année et correspondance avec la série 2025 avant chaque retrait. En l'absence de ventilation prouvée, conserver la surface forestière telle quelle et signaler le chevauchement résiduel.

Le calcul principal applique maintenant la règle sélective choisie: il soustrait uniquement les mangroves explicitement classées comme « Forest » dans les rapports nationaux et dont la superficie de classe correspond au total mangrove FRA 2025. Neuf unités satisfont ce critère, pour 495 400 ha. LCA documente 220 ha comme « Other wooded land » et n'est pas soustrait. Les ventilations de PAK, SHN, TCA et de 103 autres unités restent inconnues ou non vérifiées; leurs superficies ne sont pas soustraites. Les anciennes alertes de dépassement de surface tropicale sont conservées comme diagnostics de source, pas comme surfaces plafonnées dans le calcul principal. Cette convention évite une soustraction non étayée et laisse un risque de chevauchement résiduel entre GCW et BCW.

## 2. Remplacement effectif de la composante mangrove de BCW par GMW 2025

- Hilmi et al. utilisent une couche de mangroves UNEP-WCMC/World Atlas version 3.1 et la croisent avec les frontières `EEZ_land_union_v4_202410`. Le taux de BCW vise l'enfouissement dans le sol/sédiment. Les marais salés et herbiers restent inchangés dans tous les tests ici.
- GMW v4.1.12 fournit une couche de présence de mangroves pour 2025 à 30 m. La statistique nationale *corrigée pour la précision globale* couvre 123 des 126 unités positives actuelles et 99,9864 % de leur superficie. Ce tableau n'est pas une carte permettant de refaire directement l'intersection EEZ.
- `code/scripts/overlay_gmw_2025_eez.py` parcourt les 1 551 714 polygones du vecteur GMW 2025 et intersecte chaque polygone avec les frontières EEZ/terre du dépôt. Les sous-territoires sans code territorial propre mais rattachés à un souverain (notamment Andaman et Nicobar, Galápagos) sont regroupés avec le pays comme dans le rapprochement BCW du dépôt. L'aire est calculée en projection équivalente EPSG:6933. L'intersection avec le territoire portant le même code GMW laisse 4 011,63 ha à attribuer.
- `code/scripts/reassign_gmw_2025_eez_residuals.py` croise ces résidus avec les autres polygones « Union EEZ and country » du même fichier de frontières. Il attribue 3 983,24 ha et laisse 28,39 ha sans territoire admissible. Le transfert principal concerne 2 745,31 ha codés Guyana dans GMW mais situés dans le polygone Venezuela du fichier EEZ. C'est une divergence entre deux référentiels territoriaux, **pas** une preuve de souveraineté ni une correction de GMW. Les valeurs mondiales sont presque insensibles à la réattribution ; les résultats nationaux de GUY et VEN en dépendent et doivent conserver ce signalement.
- Les polygones bruts GMW représentent 15,06748 Mha ; l'intersection avec l'EEZ correspondant donne 15,06347 Mha. La table GMW nationale corrigée donne 14,72836 Mha. Ces trois nombres mesurent des traitements différents. Le test spatial suit la logique cartographique de Hilmi ; le test avec la table corrigée mesure l'effet de la correction de précision.

| Cas | Mangroves Mha | Enfouissement moyen MtC/an | Valeur mangroves Md US$2015/an | BCW total Md US$2015/an |
|---|---:|---:|---:|---:|
| Ancienne composante mangrove publiée par Hilmi | 15,206 | 28,171 | 57,512 | 2 330,776 |
| **Calcul principal: GMW 2025 avec réattribution spatiale** | **15,067** | **27,915** | **56,990** | **2 330,254** |
| GMW 2025, intersection avec l'EEZ portant le même code | 15,063 | 27,908 | 56,975 | 2 330,239 |
| GMW 2025, superficie nationale corrigée | 14,728 | 27,287 | 55,707 | 2 328,971 |

Les tirages du taux de mangroves et du GSCC ont été réutilisés sans modifier les autres composantes. Ces intervalles **n'incorporent pas l'incertitude de cartographie GMW**. Le cas EEZ réattribué est maintenant le calcul principal, car il conserve la règle territoriale appliquée au reste de BCW. La statistique nationale corrigée reste une sensibilité distincte. Le croisement attribue 2 745 ha codés Guyana par GMW à la géométrie Venezuela de la couche EEZ; ce désaccord entre référentiels n'est pas un arbitrage de souveraineté.

**Convention appliquée.** Les polygones GMW 2025 intersectés avec les mêmes frontières territoriales que le reste de BCW remplacent la superficie mangrove publiée auparavant. La statistique nationale GMW corrigée est conservée comme sensibilité. Les marais salés, herbiers et composantes océaniques restent inchangés. Du côté GCW, les pixels mangroves identifiés par le masque natif du modèle sont exclus des quatre taux Gibbs/GFW; les superficies FRA ne sont réduites que dans les neuf cas où le classement « Forest » est documenté.

Sorties : `results/validation/gmw_2025_eez_overlay_by_source_unit.csv`, `gmw_2025_eez_residual_reassignment.csv`, `gmw_2025_eez_final_area_by_unit.csv`, `gmw_2025_spatial_bcw_by_unit.csv`, `gmw_2025_spatial_bcw_world.csv`, `gmw_2025_mangrove_replacement_test_world.csv`.

Pour reproduire l'intersection, récupérer le fichier public `gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg.gz` dans le [dépôt Zenodo GMW](https://zenodo.org/records/21346457), vérifier son MD5 `ad1dda154bd21ad14b3cdf6baf3143ed`, le décompresser sous `data/raw/environmental/marine/gmw/`, puis lancer `python code/scripts/overlay_gmw_2025_eez.py`, `python code/scripts/reassign_gmw_2025_eez_residuals.py` et `python code/scripts/test_gmw_2025_spatial_bcw.py` dans cet ordre. Le vecteur décompressé (~957 Mo) et l'archive compressée (~190 Mo) sont exclus de Git. Une installation `pip install -e ".[dev]"` fournit les dépendances des scripts, dont `openpyxl` pour le classeur Rickels.

## 3. Recalcul des taux Gibbs sans pixels de mangroves

Le choix actualisé du chercheur est de **recalculer les quatre taux moyens Gibbs/GFW en retirant les pixels que le modèle source classe comme mangroves**. Dans la version `v1.3.2` du modèle WRI/GFW, le raster `removal_forest_type` affecte le code 6 aux mangroves. Pour chacun des 272 carreaux de retraits bruts 2001-2023, le script lit le carreau correspondant de ce masque, vérifie que leurs grilles sont identiques, puis exclut les pixels de code 6 avant de calculer les moyennes pondérées par l'aire dans les quatre biomes GEZ. Les 272 tuiles de retraits (36,89 Go) et les 272 masques (9,04 Go) ont été vérifiés avant agrégation. Le tableau de comparaison conserve les anciens taux et mesure l'aire effectivement exclue.

| Biome GEZ | Taux avec mangroves (tC/ha/an) | Taux sans mangroves (tC/ha/an) | Variation | Aire exclue (ha) |
|---|---:|---:|---:|---:|
| Tropical | 0,960530 | 0,934399 | −2,721 % | 10 377 597 |
| Subtropical | 1,376466 | 1,370738 | −0,416 % | 134 678 |
| Tempéré | 1,430112 | 1,430069 | −0,003 % | 1 787 |
| Boréal | 0,618633 | 0,618633 | 0 % | 0 |

Les 544 empreintes de sources figurent dans les manifestes `data/raw/environmental/forest/gfw_gibbs_2025/`. Les quatre taux proviennent des 272 tuiles pondérées par l'aire de pixel ; l'écart-type spatial n'est pas un intervalle d'incertitude du taux. Quatre couples tuile-biome ne contenaient **que** des pixels de mangroves. Le calcul des taux les avait correctement écartés, mais la première sortie d'audit omettait leurs 6 484 ha. `code/scripts/complete_gfw_mangrove_audit.py` a rétabli ces lignes à partir du tableau original vérifié ; `code/scripts/compare_gfw_mangrove_exclusion.py` confirme ensuite, pour chaque biome, `A_ancien = A_sans_mangrove + A_exclue` et l'identité correspondante des nombres de pixels. L'archive originale des sorties distantes reste dans `results/validation/gfw_non_mangrove_results.tar.gz`.

Cette opération harmonise **la définition des taux source** avec le choix de ranger les mangroves dans BCW. Elle ne détermine pas, à elle seule, combien d'hectares de mangroves sont contenus dans les totaux nationaux FRA : la difficulté décrite en section 1 reste distincte. Le masque décrit les classes du modèle Gibbs/GFW pour sa période de référence ; il ne constitue pas une carte exhaustive des mangroves FRA 2025.

## 4. Sensibilité de la valorisation GCW au GSCC

Le calcul principal valorise les ajouts annuels à la biomasse vivante au GSCC entier. `code/scripts/test_gcw_retention_valuation.py` applique à chacun des 20 000 tirages de GCW une fraction hypothétique `f` et conserve ainsi l'incertitude déjà portée par les tirages GSCC. **`f` n'est ni une fraction de carbone observée après un nombre d'années, ni une conversion prouvée entre stockage temporaire et permanent.** Aucune durée unique n'est fournie par Gibbs pour les tonnes ajoutées.

| Fraction `f` | GCW moyenne, billions US$2015/an | P05-P95, billions US$2015/an |
|---:|---:|---:|
| 0,25 | 2,061 | 0,805-3,742 |
| 0,33 | 2,721 | 1,063-4,940 |
| 0,50 | 4,122 | 1,610-7,484 |
| 0,75 | 6,183 | 2,415-11,226 |
| 1,00 | 8,244 | 3,220-14,968 |

Un test lié à une durée requerrait une distribution de survie du carbone par tissu et une fonction économique de valeur du report d'émission. La règle de Groom et Venmans concernant 50 ans est une illustration issue de leur modèle ; elle ne fournit pas une durée moyenne mesurée pour GCW.

Sorties : `results/validation/gcw_valuation_fraction_sensitivity_world.csv` et `_by_unit.csv`.

Reproduction : `python code/scripts/test_gcw_retention_valuation.py` après le calcul principal des 20 000 tirages GCW.

## 5. Scénario de coûts d'abattement suivant Rickels et al.

### Question et formule

Le scénario demande : **si une part choisie de la capacité forestière annuelle perdue avec une surface convertie était compensée par des réductions supplémentaires d'émissions hors secteur forestier en 2030, quel serait le coût additionnel de cette politique ?** La surface forestière diminue dans ce scénario ; le taux d'ajout des hectares forestiers qui restent ne baisse pas par hypothèse. « Affaiblissement du puits » désigne ici exclusivement la capacité annuelle non fournie par les hectares convertis. Le scénario ne mesure ni la dépense réelle des gouvernements ni le coût physique de reconstruire une forêt.

Avec la surface `D_{ib}` en hectares qui disparaît **pendant une année représentative** dans le biome `b`, et le taux forestier `φ_b` en tC/ha/an, la capacité annuelle perdue de cette cohorte est `L_i = (44/12) Σ_b D_{ib} φ_b`, en tCO2/an. La moyenne FRA de déforestation exprimée en ha/an fournit la taille de cette cohorte représentative ; une fois fixée pour le scénario, `D_{ib}` est une surface en hectares. Sans cette précision, multiplier directement les unités « ha/an × tC/ha/an » donnerait une variation de capacité par an, en tC/an², et non la capacité annuelle perdue d'une cohorte. Pour le modèle de Rickels, `L_i` est converti en MtCO2/an. Le périmètre conceptuel visé est celui des quatre biomes de GCW hors mangroves connues. **La série de perte actuellement disponible dans le dépôt ventile la déforestation FRA selon les parts de biomes et ne peut pas identifier exactement les pertes propres aux mangroves** ; le scénario calculé est donc un prototype sur cette approximation, à corriger avant usage dans le papier.

Pour une fraction de compensation hypothétique `q ∈ [0,1]`, le plafond devient `A_i(q)=A_i-qL_i`. Le modèle publié donne, pour les émissions restantes `E_i`, les émissions sans politique `E_i^BAU`, le PIB projeté `Y_i^BAU` et le coefficient de coût calibré `α_i` :

`AC_i(E_i) = α_i Y_i^BAU E_i^BAU (1-E_i/E_i^BAU)^3`.

Le coût supplémentaire sans commerce de permis est `ΔC_i(q)=AC_i(min(E_i^BAU,A_i-qL_i))-AC_i(min(E_i^BAU,A_i))`. Si `A_i-qL_i < 0`, le scénario est marqué non réalisable et exclu de la somme ; il n'est pas ramené silencieusement à zéro. Il s'agit d'une hypothèse de compensation **extérieure aux NDC modélisées par Rickels**, qui excluent LULUCF.

### Données et accessibilité

Rickels et al. mettent publiquement à disposition [leur dépôt OceanValue](https://github.com/wilmwilmsen/OceanValue), notamment `Supplementary_Data_M3.xlsx` (calibrage des `α_i`) et `Supplementary_Data_M4.xlsx` (146 régions, dont EU29 agrégée ; six projections macroéconomiques ; cibles basses/hautes et coûts). Les fichiers sont consultables et téléchargeables sans abonnement ou clé. Le dépôt public ne porte pas de licence explicite identifiable : notre script lit M4 à la demande sans republier le classeur brut. L'article et la version exacte du dépôt sont cités dans le script.

`code/scripts/test_forest_abatement_costs.py` lit M4, vérifie sa structure, puis reproduit **chaque coût national de référence sans commerce** avec une erreur maximale de `2,84 × 10⁻¹⁴` milliard d'USD dans les unités du classeur. En incluant la ligne EU29, la moyenne des six scénarios à ambition haute est `262,339832` milliards, conforme aux `262,34` milliards publiés. Cette réplication valide l'extraction de la courbe et des colonnes ; elle ne valide pas l'hypothèse de compensation forestière.

La table forestière contient 139 unités rapportant une déforestation ; 92 correspondent directement à une ligne pays de M4. À `q=1`, deux lignes ayant une cible de zéro deviennent irréalisables, laissant 90 pays et `34,836` des `35,663` MtCO2/an de capacité perdue couverte dans la table actuelle. Pour cette sous-population, la **moyenne non pondérée des six projections** du surcoût modélisé est `3,478` milliards dans la base monétaire du classeur, avec ambition haute. À `q=0,5`, elle est `1,557` milliard. Ces chiffres sont exploratoires et ne sont pas comparables directement aux US$2015 du GCW sans harmonisation de l'année monétaire. EU29 apparaît comme un bloc dans M4 ; les pertes connues de ses membres ne sont pas injectées artificiellement dans cette ligne, faute de couverture complète et de décision sur la consolidation.

Avant insertion dans le manuscrit : fixer la période de perte utilisée comme hypothèse pour 2030 ; réconcilier la perte GCW hors mangroves ; harmoniser les pays et le bloc EU29 ; confirmer l'année monétaire et la conversion vers US$2015 ; choisir les fractions `q` et vérifier si le scénario sans commerce suffit ou si la variante avec marché international est nécessaire. Le scénario `q=1` est une convention d'effort supplémentaire, pas une affirmation d'équivalence climatique permanente.

Sorties : `results/validation/forest_abatement_no_trade_country_scenarios.csv` et `forest_abatement_no_trade_summary.csv`.

Reproduction : `python code/scripts/test_forest_abatement_costs.py`. Le script télécharge M4 en mémoire depuis la révision GitHub `61e17605919e19c1da83e282cafc8940d6edf3b8` et accepte aussi `--workbook` pour utiliser une copie locale. Il ne loue pas de calcul distant et ne télécharge pas M3 ; M3 reste disponible si un recalibrage des courbes est nécessaire.

## Sources primaires

- FAO FRA, [définitions des forêts et des mangroves](https://fra-data.fao.org/definitions/fra/2020/en/tad) ; [classification brésilienne](https://fra-data.fao.org/assessments/fra/2025/BRA/originalDataPoints/2020/extentOfForest/).
- [GMW v4.1.12 et fichiers vecteurs](https://zenodo.org/records/21346457), [fiche JAXA](https://www.eorc.jaxa.jp/ALOS/en/dataset/gmw_e.htm).
- [Gibbs et al. (2025)](https://essd.copernicus.org/articles/17/1217/2025/).
- [Hilmi et al. (2026)](https://www.nature.com/articles/s44458-026-00117-8), [Alongi (2022)](https://www.mdpi.com/1999-4907/13/2/149).
- [Rickels et al. (2024)](https://doi.org/10.1038/s43247-024-01674-3), [données des auteurs](https://github.com/wilmwilmsen/OceanValue).
- [Groom et Venmans (2023)](https://www.nature.com/articles/s41586-023-06153-x), [Matthews et al. (2023)](https://www.nature.com/articles/s41467-023-41242-5).
