# Audit des superficies de mangroves, 15 octobre 2026

## Sources et périmètres vérifiés

| Série | Source et année | Définition et traitement dans le dépôt |
|---|---|---|
| BCW de Hilmi et al. | World Atlas of Mangroves UNEP-WCMC, version 3.1 publiée en mars 2021 ; observations principalement 1999-2003, avec des années plus anciennes selon les pays | Polygones intersectés avec `EEZ_land_union_v4_202410`, puis superficies par unité `UNION`. Il s'agit d'une carte de mangroves, pas d'une statistique FRA 2025. Source exacte : supplément de Hilmi, tableau 1. |
| FRA 2025 | `1a_forestArea` et `1c_mangroves`, valeurs 2025, milliers d'hectares multipliés par 1 000 dans `forest_areas.py` | La forêt FRA inclut les mangroves répondant aux critères forestiers, mais la rubrique `mangroves` inclut **forêt et autres terres boisées**. La part commune aux deux rubriques n'est pas fournie par le total national. |
| GMW 2025 | Global Mangrove Watch v4.1.12, carte annuelle 2025 ; tableau par pays corrigé pour la précision globale | Couverture télédétectée des mangroves. Les frontières nationales et la correction d'aire de GMW ne sont pas celles de l'intersection EEZ de Hilmi. Le fichier `Extent` contient un total mondial et des valeurs par pays en hectares ; le total n'est pas additionné deux fois dans le script. |

Le taux de Hilmi pour les mangroves, **183,6 ± 14,7 tC/km²/an**, vient d'Alongi (2022), section « Carbon Burial Rates » : il mesure l'enfouissement du carbone organique dans les sols/sédiments. Il ne comprend pas un taux d'augmentation de la biomasse vivante. Gibbs et al. (2025), en revanche, estiment des absorptions brutes vers la biomasse aérienne et souterraine. Les flux portent donc sur des réservoirs distincts, même lorsqu'ils existent sur les mêmes hectares.

## Résultats reproduits localement

| Série | Superficie de mangroves, Mha | Enfouissement illustratif avec 183,6 tC/km²/an, MtC/an | Valeur indicative à 559,6 US$/tCO₂, Md US$/an |
|---|---:|---:|---:|
| Hilmi, tableau côtier publié sans correction du dépôt | 11,187925 | 20,5410 | 42,15 |
| Hilmi + les sept compléments FRA déjà présents dans ce dépôt | 15,205505 | 27,9173 | 57,28 |
| GMW 2025, tableau corrigé par pays | 14,728364 | 27,0413 | 55,49 |
| FRA 2025, catégorie mangroves | 15,866870 | 29,1316 | 59,77 |

Les deux dernières colonnes sont des **comparaisons de surfaces à taux et prix fixes**, pas une nouvelle estimation BCW validée ni des intervalles de confiance. La valeur se calcule par `surface_ha × 1,836 tC/ha/an × 44/12 × 559,6 US$/tCO₂`. Le calcul de Hilmi est à l'échelle EEZ/territoires et utilise des tirages de taux ; GMW est attribué aux pays selon son propre découpage. L'écart brut de 4,68 Mha entre Hilmi et FRA tombe à 0,66 Mha lorsque les sept compléments déjà appliqués par le dépôt sont inclus. Les totaux restent non strictement comparables à cause des unités et définitions.

Le tableur GMW fournit pour le total mondial 2025 **13,7371 à 16,1422 Mha** comme bornes de précision globales à 95 %, autour de 14,7284 Mha. Ces bornes proviennent de l'évaluation globale du produit ; elles ne sont pas une incertitude locale fiable pour chaque pays.

Après application de la table de correspondance territoriale déjà décidée dans le dépôt (`territory_crosswalk.csv`), **116 unités possèdent les trois séries**. Leurs sommes sont respectivement 11,8491 Mha (FRA), 11,1870 Mha (Hilmi brut) et 11,0390 Mha (GMW). Les divergences restent fortes au niveau national. Exemples : Guyana, 275 880 ha FRA contre 26 735 ha Hilmi et 30 049 ha GMW ; Malaisie, 284 960 ha FRA contre 522 709 ha Hilmi et 559 735 ha GMW ; Pakistan, 164 530 ha FRA contre 77 745 ha Hilmi et 82 853 ha GMW. Ces chiffres ne doivent pas être interprétés comme une évolution temporelle, car les méthodes, périmètres et dates diffèrent.

## Contrôle de la soustraction forestière actuelle

`forest_uptake_gfw.py` répartit la superficie de forêt FRA 2025 par domaine GEZ, puis soustrait **toute** la rubrique nationale FRA « mangroves » de la seule partie tropicale, avec un plancher à zéro. Cette opération retire effectivement 15 767 770 ha contre 15 866 870 ha de mangroves FRA ; le résidu est **99 100 ha**. Trois cas dépassent leur allocation tropicale :

| ISO3 | Forêt FRA, ha | Mangroves FRA, ha | Allocation tropicale avant retrait, ha | GMW 2025, ha |
|---|---:|---:|---:|---:|
| PAK | 3 192 460 | 164 530 | 128 359 | 82 853 |
| SHN | 2 020 | 2 000 | 762 | Aucune emprise GMW cartographiée |
| TCA | 10 520 | 23 600 | 10 520 | 9 005 |

La ligne TCA prouve directement que la rubrique FRA « mangroves » n'est pas un sous-ensemble automatique de `forest` : 23 600 > 10 520 ha. Le cas SHN appelle un contrôle du rapport national FRA : aucune mangrove 2025 n'est visible dans le produit GMW, et une ancienne fiche FRA indiquait une valeur reprise faute d'informations plus récentes. Il serait incorrect d'en déduire que GMW est infaillible ou que FRA est certainement erroné.

Un diagnostic spatial de la carte vectorielle GMW 2025 avec les domaines GEZ 2010 donne, **en hectares vectoriels bruts avant correction globale GMW**, environ 75 383 ha dans un domaine tropical et 9 754 ha hors des polygones GEZ pour PAK ; 616 ha tropicaux et 8 642 ha hors GEZ pour TCA ; aucune emprise GMW pour SHN. Les mangroves intertidales peuvent tomber hors des polygones terrestres GEZ. Cette attribution par point représentatif sert à diagnostiquer la géographie, **pas** à quantifier exactement la part des mangroves reconnue « forêt » par FRA.

Le dépôt conserve déjà les deux sensibilités `incl_mangroves` et `excl_mangroves` : elles produisent respectivement 14,92934 et 14,87381 GtCO₂/an de flux forestier mondial, soit **55,53 MtCO₂/an** d'écart. La variante avec mangroves utilise un **taux moyen tropical**, pas un taux propre aux mangroves ; elle ne constitue donc pas une nouvelle estimation spécialisée de leur biomasse.

## Conséquence comptable et décision scientifique

1. **Deux superficies qui se recoupent ne sont pas nécessairement un double comptage du carbone.** Chez Hilmi/Alongi, le flux est l'enfouissement dans les sols ; chez Gibbs, c'est l'entrée dans la biomasse vivante. Le risque de double valorisation porte sur le *même carbone au fil du temps* lorsqu'il passe de la biomasse vers le sol, et sur la durée réelle de stockage, non sur la seule intersection des hectares.
2. La part exacte des mangroves FRA qui appartient à `forest` ne peut pas être extraite des deux colonnes nationales `forest` et `mangroves`. Une carte GMW croisée avec une carte forestière donnerait l'intersection de **ces deux cartes**, pas l'intersection « FRA mangroves ∩ FRA forest » dans les déclarations nationales. Les catégories et millésimes resteraient distincts.
3. Si l'étude souhaite une **attribution exclusive des mangroves à BCW**, il faut fixer une règle d'allocation observable, par exemple un masque mangrove et forêt commun à résolution comparable, puis recalibrer les superficies forestières nationales au total FRA. Le choix du masque et le traitement des mangroves hors forêt doivent être explicites. Le calcul actuel `FRA mangroves retirées du tropical` n'est pas une telle règle.
4. Si l'étude souhaite compter **deux flux vers deux réservoirs**, elle peut conserver les mangroves forestières dans GCW et l'enfouissement sédimentaire dans BCW, en documentant la possibilité de transfert ultérieur entre réservoirs et en évitant de présenter la somme comme des tonnes indépendantes retirées durablement de l'atmosphère. Un taux de biomasse spécifique aux mangroves serait préférable à l'application du taux moyen tropical.
5. La mise à jour de BCW avec GMW 2025 doit reprendre l'intersection avec `EEZ_land_union_v4_202410`, résoudre les codes de territoires (par exemple `BLZ-1`, `IN-AN` dans Hilmi face aux ISO3 par pays de GMW), appliquer et documenter la correction d'aire GMW et recalculer les tirages de séquestration et de valeur. Remplacer directement les seules colonnes de superficie ferait mélanger des frontières.

Le nom du service est une question distincte de cette harmonisation spatiale. Le GIEC reconnaît la biomasse comme réservoir de carbone et définit la séquestration comme augmentation du contenu d'un réservoir ; il définit un puits par un flux net entrant supérieur au flux sortant pendant la période. Le SEEA EA (§6.114) retient, pour le service comptable de séquestration, du carbone attendu en stockage long et cite le bilan net de l'écosystème comme mesure appropriée. L'ajout brut Gibbs/GFW peut décrire un **flux entrant dans la biomasse**, mais ne prouve pas seul une augmentation nette du stock vivant ni du puits de l'écosystème complet.

Le script `scripts/audit_mangrove_accounting.py` reproduit la table nationale de comparaison et `mangrove_area_fixed_rate_scenarios_2026-10-15.csv`. `scripts/audit_mangrove_biomes.py` reproduit le diagnostic ciblé avec les vecteurs GMW publics. Aucun des deux ne modifie le pipeline GCW/BCW principal ni le manuscrit.

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
