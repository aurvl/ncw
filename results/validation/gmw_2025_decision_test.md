# Test de remplacement des superficies de mangroves par GMW 2025

Date : 15 octobre 2026. Statut : sensibilité calculée ; aucun résultat principal de GCW/BCW/NCW ni passage de PAPER.docx n'a été modifié.

## Question et sources

Proposition du chercheur : utiliser la carte mondiale de mangroves la plus récente et la plus couvrante pour actualiser la composante mangrove de Hilmi et al., écarter les compléments de surface FRA dans BCW, et retirer de GCW uniquement la mangrove que l'on peut établir comme incluse dans la forêt.

- Hilmi et al. (2026), supplément tableau 1 : World Atlas of Mangroves UNEP-WCMC v3.1 ; ses observations sous-jacentes sont surtout de 1999-2003. Attribution par intersection avec `EEZ_land_union_v4_202410`.
- GMW v4.1.12 : carte annuelle 2025 à 30 m, publiée en 2026, série 1985-2025. Évaluation globale F1 = 0,9276 ; précision variable localement. La statistique par pays est corrigée pour la précision globale ; ses unités territoriales ne coïncident pas exactement avec celles de Hilmi.
- FRA 2025 `1a_forestArea` et `1c_mangroves` : le téléchargement global ne ventile pas la catégorie mangroves entre forêt et autres terres boisées. Sa définition les inclut toutes deux.

## Couverture observée

| Ensemble dans les données actuelles | Unités positives | Correspondance GMW positive | Part de leur superficie couverte |
|---|---:|---:|---:|
| Hilmi publié après rapprochement territorial | 119 | 116 | 99,9918 % |
| FRA 2025 mangroves | 116 | 113 | 99,9858 % |
| BCW actuel avec sept compléments FRA | 126 | 123 | 99,9864 % |

Les trois unités BCW sans emprise GMW correspondante sont Montserrat (10 ha de complément FRA), Hala'ib Triangle (62,36 ha chez Hilmi) et Sainte-Hélène (2 000 ha de complément FRA). GMW compte quatre petites unités positives absentes de la composante mangrove actuelle : Glorioso Islands (0,43 ha), Saint-Barthélemy (3,50 ha), Cocos Islands (7,95 ha) et Nauru (0,52 ha), sous réserve de la correspondance exacte des territoires. Il couvre l'Indonésie, Cuba et le Sénégal, les trois plus importants compléments FRA actuels. Le total mondial GMW corrigé est 14 728 364,26 ha, contre 15 205 505,13 ha dans BCW actuel avec compléments FRA. Il serait incorrect de lire cet écart comme une évolution temporelle : les cartes, dates et frontières changent.

## Calcul exploratoire avec les tirages existants

Pour chaque unité : `BCW_nouveau(d) = BCW_actuel(d) + [surface_GMW - surface_mangrove_actuelle] / 100 × taux_mangrove(d) × 44/12 × GSCC(d)`. On réutilise les 20 000 tirages appariés de Hilmi/BNC2 ; les autres composantes BCW restent identiques. Ce test n'introduit pas l'incertitude de surface GMW et n'a pas encore refait l'intersection spatiale avec les frontières EEZ de Hilmi. Le taux moyen de ces tirages est 185,266 tC/km²/an.

| Quantité | Actuel | Test GMW 2025 |
|---|---:|---:|
| Surface mangrove | 15,206 Mha | 14,728 Mha |
| Enfouissement moyen | 28,171 MtC/an | 27,287 MtC/an |
| Valeur moyenne mangrove | 57,512 Md US$2015/an | 55,707 Md US$2015/an |
| Valeur moyenne BCW total dans les unités du dépôt | 2 330,776 Md US$2015/an | 2 328,971 Md US$2015/an |

La différence moyenne BCW est -1,805 Md US$2015/an. L'intervalle 5e-95e percentile des **tirages de cette différence** est [-6,002 ; -0,176] Md, lié uniquement au taux et au GSCC utilisés ici. Conserver par prudence l'ancienne surface pour les trois unités sans GMW change le total GMW moyen de +0,008 Md. Les deux sorties mondiales figurent dans `gmw_2025_mangrove_replacement_test_world.csv` ; la composante mangrove seule est dans `gmw_2025_mangrove_component_test_world.csv` ; les unités dans `gmw_2025_mangrove_replacement_test_by_unit.csv`.

## Test de la soustraction forestière

Remplacer simplement la quantité FRA soustraite par la quantité GMW ferait disparaître les dépassements PAK et TCA observés avec FRA. Il resterait au moins Curaçao (110,59 ha GMW contre 70 ha de forêt FRA) et Nauru (0,52 ha GMW contre 0 ha de forêt FRA). Cette vérification de taille n'est pas un test d'inclusion : pour TCA, 8 642 des 9 258 ha de polygones GMW bruts analysés tombent hors des polygones GEZ terrestres, malgré `surface_GMW < forêt_FRA`. Ni la série FRA nationale ni le masque forestier JRC à environ 2,4 km utilisé pour répartir les biomes ne révèlent quels pixels GMW appartiennent à la catégorie `forest` de FRA. Ce masque est trop grossier pour conclure sur les mangroves côtières de 30 m.

Il faut donc distinguer deux tâches : (1) mettre à jour la surface des mangroves dans BCW à l'aide de GMW 2025, ce que la couverture permet largement ; (2) chiffrer le retrait forestier correspondant. Le second ne peut pas être prouvé par une soustraction des deux totaux nationaux. Une règle spatiale forestière commune à résolution comparable ou une ventilation nationale FRA documentée serait nécessaire. L'incertitude résiduelle doit être explicitée.

## Vérifications et limites restantes

- Somme des unités GMW après rapprochement de codes égale au total du tableur source.
- Différence de valeur mangrove égale à la différence de BCW total, tirage par tirage au niveau global, car les autres composantes sont inchangées.
- Le scénario ne remplace pas l'ancienne table produite avec EEZ/territoires par une intersection GMW × EEZ. C'est l'étape nécessaire pour un résultat BCW spatialement harmonisé.
- Les taux de Gibbs/GFW utilisés pour construire les quatre moyennes de biome incluent une catégorie de pixels mangroves avec facteur propre. Les taux par biome devront être réévalués sans ces pixels si GCW doit exclure entièrement les mangroves.
- La proximité du total GMW avec FRA ne prouve pas qu'ils définissent les mêmes hectares, ni que toute mangrove GMW appartient à la forêt FRA.

## Références primaires

- Hilmi et al. (2026), article : https://www.nature.com/articles/s44458-026-00117-8 ; supplément : https://static-content.springer.com/esm/art%3A10.1038%2Fs44458-026-00117-8/MediaObjects/44458_2026_117_MOESM2_ESM.pdf
- GMW v4.1.12 : https://zenodo.org/records/21346457 ; fiche JAXA : https://www.eorc.jaxa.jp/ALOS/en/dataset/gmw_e.htm
- FAO FRA, définitions : https://fra-data.fao.org/definitions/fra/2020/en/tad
- Gibbs et al. (2025) : https://essd.copernicus.org/articles/17/1217/2025/
