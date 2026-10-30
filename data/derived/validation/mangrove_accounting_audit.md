# Audit des superficies de mangroves, mise à jour du 28 octobre 2026

## Sources et périmètres vérifiés

| Série | Source et année | Définition et traitement dans le dépôt |
|---|---|---|
| BCW de Hilmi et al. | World Atlas of Mangroves UNEP-WCMC, version 3.1 publiée en mars 2021 ; observations principalement 1999-2003, avec des années plus anciennes selon les pays | Polygones intersectés avec `EEZ_land_union_v4_202410`, puis superficies par unité `UNION`. Il s'agit d'une carte de mangroves, pas d'une statistique FRA 2025. Source exacte : supplément de Hilmi, tableau 1. |
| FRA 2025 | `1a_forestArea` et `1c_mangroves`, valeurs 2025, milliers d'hectares multipliés par 1 000 dans `forest_areas.py` | La forêt FRA inclut les mangroves répondant aux critères forestiers, mais la rubrique `mangroves` inclut **forêt et autres terres boisées**. La part commune aux deux rubriques n'est pas fournie par le total national. |
| GMW 2025 | Global Mangrove Watch v4.1.12, carte annuelle 2025 et polygones codés par pays | Couverture télédétectée des mangroves. La mise à jour BCW intersecte directement les polygones avec les géométries EEZ `UNION` en Mollweide, conserve `cntry_iso3` pour la provenance, puis applique le facteur global GMW 0,9775 à l'aire de chaque intersection avant l'agrégation comptable. |

Le taux de Hilmi pour les mangroves, **183,6 ± 14,7 tC/km²/an**, vient d'Alongi (2022), section « Carbon Burial Rates » : il mesure l'enfouissement du carbone organique dans les sols/sédiments. Il ne comprend pas un taux d'augmentation de la biomasse vivante. Gibbs et al. (2025), en revanche, estiment des absorptions brutes vers la biomasse aérienne et souterraine. Les flux portent donc sur des réservoirs distincts, même lorsqu'ils existent sur les mêmes hectares.

## Résultats reproduits localement

| Série | Superficie de mangroves, Mha | Enfouissement illustratif avec 183,6 tC/km²/an, MtC/an | Valeur indicative à 559,6 US$/tCO₂, Md US$/an |
|---|---:|---:|---:|
| Hilmi, tableau côtier publié sans correction du dépôt | 11,187925 | 20,5410 | 42,15 |
| Hilmi + les sept compléments FRA déjà présents dans ce dépôt | 15,205505 | 27,9173 | 57,28 |
| GMW 2025, intersection EEZ brute (somme sur unités comptables) | 15,156239 | 27,8269 | 57,10 |
| GMW 2025, intersection EEZ corrigée par 0,9775 (candidate prioritaire) | 14,815224 | 27,2008 | 55,81 |
| GMW 2025, statistique nationale corrigée GMW (comparaison distincte) | 14,728364 | 27,0413 | 55,49 |
| FRA 2025, catégorie mangroves | 15,866870 | 29,1316 | 59,77 |

Les deux dernières colonnes sont des **comparaisons de surfaces à taux et prix fixes**, pas une nouvelle estimation BCW validée ni des intervalles de confiance. La valeur se calcule par `surface_ha × 1,836 tC/ha/an × 44/12 × 559,6 US$/tCO₂`. Le calcul BCW de Hilmi est à l'échelle EEZ/territoires et utilise des tirages de taux. Pour la candidate GMW 2025, l'intersection EEZ localise l'aire et le facteur officiel 0,9775 corrige ensuite sa superficie. La surface finalement utilisée dépend de la hiérarchie par unité décrite ci-dessous. Les sommes sur les unités comptables peuvent inclure des recouvrements entre géométries EEZ; elles ne sont donc pas des aires mondiales uniques sans chevauchement. La ligne de statistique nationale corrigée GMW reste une comparaison distincte car elle utilise une autre partition géographique. Les totaux ne sont pas strictement comparables à cause des périmètres et des définitions.

Le tableur GMW fournit pour le total mondial 2025 **13,7371 à 16,1422 Mha** comme bornes de précision globales à 95 %, autour de 14,7284 Mha. Ces bornes proviennent de l'évaluation globale du produit ; elles ne sont pas une incertitude locale fiable pour chaque pays.

Après application de la table de correspondance territoriale déjà décidée dans le dépôt (`territory_crosswalk.csv`), **116 unités possèdent les trois séries**. Leurs sommes sont respectivement 11,8486 Mha (FRA), 11,1865 Mha (Hilmi brut) et 11,3583 Mha (GMW direct). Les divergences restent fortes au niveau national. Exemples : Guyana, 275 880 ha FRA contre 26 735 ha Hilmi et 28 178 ha GMW direct ; Malaisie, 284 960 ha FRA contre 522 709 ha Hilmi et 576 294 ha GMW direct ; Pakistan, 164 530 ha FRA contre 77 745 ha Hilmi et 85 116 ha GMW direct. Ces chiffres ne doivent pas être interprétés comme une évolution temporelle, car les méthodes, périmètres et dates diffèrent.

## Sélection de la surface BCW par unité

La surface mangrove utilisée dans le calcul BCW suit maintenant l'ordre défini par le chercheur : GMW 2025 direct si une aire positive est détectée; sinon FRA 2025 si une valeur est déclarée, y compris zéro; sinon statistiques nationales GMW 2024, puis 2023 si une aire positive existe; enfin, l'ancienne aire BCW si elle est renseignée. La table annuelle GMW disponible est un tableau de superficies corrigées, pas une couche de polygones 2024/2023.

| Source finalement retenue | Unités | Somme des surfaces retenues (ha) |
|---|---:|---:|
| GMW 2025 direct corrigé | 126 | 14 815 223,695 |
| FRA 2025 | 113 | 2 660,000 |
| Statistiques nationales GMW 2024 | 0 | 0 |
| Statistiques nationales GMW 2023 | 0 | 0 |
| Ancienne aire BCW | 1 | 62,360 |
| Aucune source disponible | 26 | 0 |

Les 26 unités sans source disponible ne reçoivent pas de nouvelle composante mangrove. L'aire sélectionnée totale est 14 817 946,055 ha. L'audit par unité, y compris les valeurs candidates et la source retenue, est `data/derived/bcw_mangrove_gmw_area_replacement.csv`. Pour le Brésil, la priorité GMW 2025 retient 1 083 926,377 ha au lieu des 1 137 555,043 ha BCW antérieurs.

Par rapport à l'ancienne surface BCW, une source plus récente est retenue pour 239 unités : GMW 2025 pour 126 et FRA 2025 pour 113. Les deux surfaces sont disponibles pour 119 unités; la surface retenue est différente de l'ancienne pour 118 et identique pour une. Pour les 121 autres unités mises à jour, aucune ancienne surface BCW n'était renseignée. Une unité conserve l'ancienne surface BCW et 26 n'ont aucune surface disponible. Les séries GMW 2024 et 2023 ne sont pas utilisées dans cette exécution.

## Contrôle de la soustraction forestière actuelle

Cette section remplace la description historique du traitement qui soustrayait la
catégorie mangrove entière. Depuis la mise à jour du 23 octobre 2026,
`forest_uptake_gfw.py` répartit la forêt FRA 2025 selon les parts de biomes FRA
rapportées en priorité, avec le GEZ/JRC en secours, puis soustrait seulement la part
documentée comme Forest dans la catégorie mangrove.

La table `fra_mangrove_forest_overlap_2025.csv` distingue désormais :

- 2 082 920 ha dans 12 correspondances exactes classées 100% Forest ;
- 1 809 830 ha dans 11 unités où la classification Forest du rapport est appliquée
  à la série 2025 copiée, prévisionnelle ou extrapolée sous une hypothèse explicite
  de stabilité ;
- 287 848 ha au Mozambique, correspondant à 80% de sa catégorie FRA 2025 de
  359 810 ha ;
- 312 ha à Mayotte, correspondant à 48% de sa catégorie FRA 2025 de 650 ha ;
- 72 477,75 ha documentés comme Other wooded land et 42,25 ha comme Remaining
  land ;
- 11 613 440 ha sans ventilation quantitative Forest/Other wooded land vérifiée.

Le chevauchement Forest documenté retiré de la forêt tropicale est donc de
4 180 910 ha. Les applications de stabilité, ainsi que les fractions mozambicaine
et mahoraise, reposent sur les classifications des rapports nationaux et non sur une
intersection spatiale directe des cartes 2025.

Trois cas dépassent encore leur allocation tropicale avant retrait ; ils restent des
alertes de diagnostic et ne déclenchent aucune soustraction non documentée :

| ISO3 | Forêt FRA, ha | Mangroves FRA, ha | Allocation tropicale avant retrait, ha | GMW 2025, ha |
|---|---:|---:|---:|---:|
| PAK | 3 192 460 | 164 530 | 128 359 | 82 853 |
| SHN | 2 020 | 2 000 | 762 | Aucune emprise GMW cartographiée |
| TCA | 10 520 | 23 600 | 10 520 | 9 005 |

La ligne TCA prouve directement que la rubrique FRA « mangroves » n'est pas un sous-ensemble automatique de `forest` : 23 600 > 10 520 ha. Le cas SHN appelle un contrôle du rapport national FRA : aucune mangrove 2025 n'est visible dans le produit GMW, et une ancienne fiche FRA indiquait une valeur reprise faute d'informations plus récentes. Il serait incorrect d'en déduire que GMW est infaillible ou que FRA est certainement erroné.

Un diagnostic spatial de la carte vectorielle GMW 2025 avec les domaines GEZ 2010 donne, **en hectares vectoriels bruts avant correction globale GMW**, environ 75 383 ha dans un domaine tropical et 9 754 ha hors des polygones GEZ pour PAK ; 616 ha tropicaux et 8 642 ha hors GEZ pour TCA ; aucune emprise GMW pour SHN. Les mangroves intertidales peuvent tomber hors des polygones terrestres GEZ. Cette attribution par point représentatif sert à diagnostiquer la géographie, **pas** à quantifier exactement la part des mangroves reconnue « forêt » par FRA.

Le recalcul principal donne 14,76383 GtCO₂/an avec la sélection FRA-first et la
correction documentée ci-dessus. La différence avec l'ancienne version provient de
l'audit élargi, qui documente davantage de catégories Forest dans les rapports
nationaux. Les variantes map-first et sans correction fractionnelle restent des
sensibilités à régénérer explicitement si elles sont présentées dans le papier ; le
pipeline principal utilise FRA-first et les fractions documentées. La variante avec
mangroves utilise un taux moyen tropical, pas un taux propre aux mangroves ; elle ne
constitue donc pas une nouvelle estimation spécialisée de leur biomasse.

## Conséquence comptable et décision scientifique

1. **Deux superficies qui se recoupent ne sont pas nécessairement un double comptage du carbone.** Chez Hilmi/Alongi, le flux est l'enfouissement dans les sols ; chez Gibbs, c'est l'entrée dans la biomasse vivante. Le risque de double valorisation porte sur le *même carbone au fil du temps* lorsqu'il passe de la biomasse vers le sol, et sur la durée réelle de stockage, non sur la seule intersection des hectares.
2. La part exacte des mangroves FRA qui appartient à `forest` ne peut pas être extraite des deux colonnes nationales `forest` et `mangroves`. Une carte GMW croisée avec une carte forestière donnerait l'intersection de **ces deux cartes**, pas l'intersection « FRA mangroves ∩ FRA forest » dans les déclarations nationales. Les catégories et millésimes resteraient distincts.
3. Si l'étude souhaite une **attribution exclusive des mangroves à BCW**, il faut fixer une règle d'allocation observable, par exemple un masque mangrove et forêt commun à résolution comparable, puis recalibrer les superficies forestières nationales au total FRA. Le choix du masque et le traitement des mangroves hors forêt doivent être explicites. Le calcul actuel `FRA mangroves retirées du tropical` n'est pas une telle règle.
4. Si l'étude souhaite compter **deux flux vers deux réservoirs**, elle peut conserver les mangroves forestières dans GCW et l'enfouissement sédimentaire dans BCW, en documentant la possibilité de transfert ultérieur entre réservoirs et en évitant de présenter la somme comme des tonnes indépendantes retirées durablement de l'atmosphère. Un taux de biomasse spécifique aux mangroves serait préférable à l'application du taux moyen tropical.
5. La candidate GMW 2025 est calculée par intersection directe avec `EEZ_land_union_v4_202410`, reprojection en Mollweide, puis application du facteur GMW 0,9775 à chaque aire intersection avant l'agrégation par `UNION` et le rapprochement avec les unités de l'étude. Le code GMW `cntry_iso3` est conservé pour auditer la provenance, sans déplacer l'aire hors de l'unité EEZ intersectée. La priorité par unité sélectionne ensuite la surface mangrove; le pipeline actualise cette composante et génère les comptes, tableaux et figures. Les sorties principales sont `results/validation/gmw_2025_direct_overlay_by_eez_unit_and_source.csv` (intersection brute), `results/validation/gmw_2025_direct_area_eez_crosswalk.csv` (aires brutes et corrigées par EEZ) et `data/derived/gmw_2025_mangrove_area_by_unit.csv` (aires brutes et corrigées par unité d'étude).

Le nom du service est une question distincte de cette harmonisation spatiale. Le GIEC reconnaît la biomasse comme réservoir de carbone et définit la séquestration comme augmentation du contenu d'un réservoir ; il définit un puits par un flux net entrant supérieur au flux sortant pendant la période. Le SEEA EA (§6.114) retient, pour le service comptable de séquestration, du carbone attendu en stockage long et cite le bilan net de l'écosystème comme mesure appropriée. L'ajout brut Gibbs/GFW peut décrire un **flux entrant dans la biomasse**, mais ne prouve pas seul une augmentation nette du stock vivant ni du puits de l'écosystème complet.

Le script `scripts/audit_mangrove_accounting.py` reproduit la table nationale de comparaison et `mangrove_area_fixed_rate_scenarios.csv`. `scripts/audit_mangrove_biomes.py` reproduit le diagnostic ciblé avec les vecteurs GMW publics. Aucun des deux ne modifie le pipeline GCW/BCW principal ni le manuscrit.

## Sources primaires

- Hilmi et al. (2026), article et supplément, tableau 1 (World Atlas v3.1) et tableau 3 (taux) : https://www.nature.com/articles/s44458-026-00117-8 ; supplément : https://static-content.springer.com/esm/art%3A10.1038%2Fs44458-026-00117-8/MediaObjects/44458_2026_117_MOESM2_ESM.pdf
- UNEP-WCMC, World Atlas of Mangroves, métadonnées de temporalité principalement 1999-2003 : https://www.cbd.int/doc/meetings/mar/ebsaws-2017-01/other/ebsaws-2017-01-wcmc-submission-03-en.pdf
- FAO, FRA 2025, données : https://fra-data.fao.org/api/export/bulk-download/ ; définitions FAO des forêts et mangroves : https://fra-data.fao.org/definitions/fra/2020/en/tad
- GMW v4.1.12 et README, publication juillet 2026 : https://zenodo.org/records/21346457
- Ancien rapport FRA sur Sainte-Hélène (reprise de la donnée 1980 dans cette ancienne édition, sans preuve sur la provenance de l'édition 2025) : https://www.fao.org/4/al611E/al611E.pdf
- Alongi (2022), sections 2.1-2.3 sur biomasse et enfouissement : https://www.mdpi.com/1999-4907/13/2/149
- Gibbs et al. (2025), flux de biomasse et émissions séparées : https://essd.copernicus.org/articles/17/1217/2025/
- GIEC, rapport LULUCF, glossaire « carbon pool », « sequestration », « sink » : https://www.ipcc.ch/site/assets/uploads/2018/03/srl-en-1.pdf
- SEEA EA (2024), §6.114 : https://seea.un.org/sites/seea.un.org/files/documents/EA/seea_ea_f124_web_9dec24.pdf
