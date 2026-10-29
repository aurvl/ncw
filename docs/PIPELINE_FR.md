# Pipeline du NCW : chemin des données et équations

Ce document présente la logique des calculs, à partir des données biophysiques et jusqu'aux indicateurs nationaux. Il définit les variables, leurs unités et les transformations successives. Les dates décrivent les observations disponibles; les flux annuels sont calculés à partir de ces sources et ne correspondent pas à des mesures réalisées simultanément.

## 1. Notation et unités

| Symbole                                      | Définition                                                                              | Unité                           |
| -------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------- |
| $i$                                          | Identifiant d’une entité du compte (pays ou territoire)                                 | —                               |
| $b$                                          | Biome tropical, subtropical, tempéré ou boréal                                          | Catégorie                       |
| $e$                                          | Mangrove, herbier marin ou marais salé                                                  | Écosystème côtier               |
| $d$                                          | Tirage commun du coût social mondial du carbone                                         | $d=1,\ldots,20\,000$            |
| $j$                                          | Identifiant de la ligne géographique du compte marin publié                             | —                               |
| $A$                                          | Surface                                                                                 | ha ou km$^2$, selon le contexte |
| $A_{i,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}$ | Aire de mangrove rapportée par Hilmi et al. (2026), utilisée seulement en dernier recours  | ha                              |
| $A_{i,e}$                                    | Aire de l'écosystème côtier $e$ attribuée à l'entité $i$                                | km$^2$                          |
| $w_p$                                        | Aire réelle du pixel $p$, utilisée comme poids dans la moyenne spatiale                 | ha                              |
| $r_b$                                        | Addition brute moyenne à la biomasse forestière vivante du biome $b$                    | tC ha$^{-1}$ an$^{-1}$          |
| $R_{e,d}$                                    | Taux marin du milieu $e$ dans le tirage $d$                                             | tC km$^{-2}$ an$^{-1}$          |
| $S_{i,d}^{\mathrm{coast}}$                   | Flux annuel de carbone des mangroves, herbiers et marais salés                          | tC an$^{-1}$                    |
| $S_i^{BCP}$                                  | Flux annuel de carbone de la pompe biologique océanique                                 | tC an$^{-1}$                    |
| $S_{i,d}^{\mathrm{blue}}$                    | Flux annuel total après conversion en CO$_2$, BCP incluse                               | tCO$_2$ an$^{-1}$               |
| $GSCC_d$                                     | Tirage $d$ du coût social mondial du carbone                                            | USD 2015 tCO$_2^{-1}$           |
| $P_p^X$                                      | Percentile d’ordre $p$ de la grandeur simulée $X$                                       | Même unité que $X$              |
| $U_i$                                        | Addition forestière brute annuelle estimée                                              | tCO$_2$ an$^{-1}$               |
| $A_{ib}$, $A_i^{total}$                      | Surface forestière utilisée dans le GCW pour le biome $b$, puis total des quatre biomes | ha                              |
| $\bar u_i^{GCW}$                             | Taux annuel moyen d'addition forestière de l'entité, $U_i/A_i^{total}$                  | tCO$_2$ ha$^{-1}$ an$^{-1}$     |
| $GDP_i^*$, $Pop_i^*$                         | Dernière valeur renseignée pour le PIB ou la population parmi 2024, 2023 et 2022        | USD 2015/an; personnes          |
| $T_i$, $D_{i,t}^{FRA}$                       | Périodes FRA disponibles et taux annuel moyen déclaré pour la période $t$               | Période; milliers d'ha/an       |
| $t_i^{sel}$                                  | Période FRA renseignée la plus récente retenue pour l'entité $i$                        | Période                         |
| $D_i$                                        | Taux annuel moyen de déforestation rapporté par FRA pour $t_i^{sel}$                    | ha/an                           |
| $\Delta t$, $A_i^{loss}$                     | Durée considérée et surface déboisée pendant cette durée, $A_i^{loss}=D_i\Delta t$      | an; ha                          |
| $\widehat L_i$                               | Capacité annuelle d'addition forestière associée à la surface déboisée pendant un an    | tCO$_2$ an$^{-1}$               |
| $\widehat V_{i,d}$                           | Valeur monétaire de cette capacité au tirage $d$ du GSCC                                | USD 2015 an$^{-1}$              |
| $E_i$                                        | Émissions territoriales fossiles et industrielles                                       | tCO$_2$/an                      |
| $GCW_{i,d}, BCW_{i,d}, N_{i,d}$              | Valeurs monétaires des comptes GCW, BCW et NCW                                          | USD 2015 an$^{-1}$              |

Les conversions utilisées sont les suivantes : $1\ \mathrm{km}^2=100\ \mathrm{ha}$ et $1\ \mathrm{tC}=44/12\ \mathrm{tCO_2}$. Une surface devient un flux lorsqu'on la multiplie par un taux annuel rapporté à cette surface. Le flux devient une valeur monétaire lorsqu'il est multiplié par le tirage du GSCC, noté $GSCC_d$. Le symbole $P_p^X$ désigne un percentile et ne représente pas un tirage du GSCC.

Les variables du compte ne proviennent pas toutes de la même année. Le tableau résume leurs périodes et les règles de sélection appliquées :

| Donnée | Source et période | Règle retenue |
|---|---|---|
| Surface forestière | FRA 2025 | Surface rapportée pour 2025 |
| Surface de mangrove | GMW 2025, FRA 2025, Hilmi et al. (2026) | Priorité : GMW 2025, puis FRA 2025, puis Hilmi et al. (2026) |
| Taux forestier Gibbs/GFW | 2001–2023 | Taux calculé sur cette période |
| Émissions territoriales comparées | 2024 | Valeur de 2024 |
| PIB et population | 2024, 2023 ou 2022 | Première valeur renseignée dans cet ordre, séparément pour chaque variable et chaque entité |
| Perte annuelle de surface forestière | FRA, périodes 2010–2015, 2015–2020 et 2020–2025 | Pour chaque entité, taux renseigné de la période la plus récente : 2020–2025, puis 2015–2020, puis 2010–2015 |
| Taux marins et tirages GSCC | Version BCW utilisée comme référence | Valeurs reprises de cette version |

Le compte combine donc des données observées ou calculées sur des périodes différentes; chaque variable conserve la période propre à sa source.

## 2. Taux annuel par biome (Gibbs/GFW) 

Le calcul commence avec deux jeux spatiaux couvrant la période 2001-2023 : les retraits bruts de carbone forestier et un masque distinguant les types de couvert. Ils sont téléchargés puis traités ensemble. Les pixels de mangrove sont retirés du calcul du taux forestier terrestre afin de ne pas attribuer le taux forestier terrestre aux mangroves, dont le flux marin est traité séparément.

Pour chaque pixel valide $p$, $x_p$ est une estimation modélisée des retraits bruts cumulés entre 2001 et 2023, en MgCO$_2$/ha. Les données d’observation de la Terre ne mesurent pas directement ce flux de carbone : elles fournissent au modèle les données d’activité forestière associées à chaque pixel d'environ 30 m. Dans l'approche « gain-perte » de Gibbs et al. (2025), l'activité est combinée à un facteur de retrait (schématiquement : activité forestière × facteur de retrait); les facteurs mobilisés comprennent des valeurs par défaut du GIEC et des facteurs localisés issus notamment d'inventaires et d'observations de terrain. Le raster des retraits contient le résultat modélisé de cette opération pour chaque cellule. Les retraits estimés concernent la biomasse forestière aérienne et souterraine. Ainsi, la valeur numérique $x_p$ est produite par le modèle; elle n'est pas calculée à partir d'une mesure directe du carbone par satellite. Comme un Mg équivaut à une tonne, le taux annuel en carbone est :

$$
r_p=x_p\frac{12}{44}\frac{1}{23}
\qquad [\mathrm{tC\ ha^{-1}\ an^{-1}}].
$$

Chaque pixel est associé à l'un des quatre domaines bioclimatiques de la FAO GEZ. Le masque définit l'indicateur $m_p$ : $m_p=1$ si le pixel est classé mangrove (code 6 dans ce masque), et $m_p=0$ sinon. La somme ci-dessous ne retient donc que les pixels hors mangrove.

Le poids $w_p$ est l'aire réelle du pixel, exprimée en hectares. La grille géographique a un pas d'environ $0,00025^\circ$, soit près de l'équateur environ 28 m nord-sud par 28 m est-ouest, donc environ 0,077 ha. Ce n'est pas une aire fixe de $30\times30$ m : la largeur est-ouest et l'aire diminuent avec la latitude. Pour les limites latitudinales $\varphi_N$ et $\varphi_S$ du pixel, l'aire sphérique est :

$$
w_p=\frac{R_\oplus^2\,\Delta\lambda\,[\sin(\varphi_N)-\sin(\varphi_S)]}{10\,000}\quad[\mathrm{ha}],
$$

où $R_\oplus=6\,371\,008.8$ m et $\Delta\lambda$ est la largeur du pixel en longitude, en radians. Le taux moyen d'un biome est calculé comme la moyenne des taux des pixels, pondérée par leur aire $w_p$; les pixels manquants sont omis et les valeurs négatives présentes dans la source restent dans le calcul :

$$
\bar r_b=\frac{\sum_{p\in b,\,m_p=0}w_pr_p}{\sum_{p\in b,\,m_p=0}w_p},
\qquad
\sigma_{b,\mathrm{spatial}}=\sqrt{\frac{\sum_{p\in b,\,m_p=0}w_p(r_p-\bar r_b)^2}{\sum_{p\in b,\,m_p=0}w_p}}.
$$

$\sigma_{b,\mathrm{spatial}}$ est l’écart-type spatial pondéré par l’aire des pixels à l’intérieur du biome. Il décrit à quel point les taux modélisés $r_p$ varient d’un pixel à l’autre. Il ne mesure ni l’erreur-type de la moyenne $\bar r_b$, ni la variation annuelle des retraits, ni l’incertitude complète du modèle Gibbs/GFW. Les scénarios $\bar r_b\pm\sigma_{b,\mathrm{spatial}}$ utilisés plus loin sont donc des sensibilités à la dispersion spatiale, pas des intervalles de confiance.

Ainsi, les données sources et leur masque sont réunis pixel par pixel, convertis en taux annuels, classés par biome et agrégés par aire. Le traitement complet part des 272 tuiles de retraits Gibbs/GFW et de leurs 272 tuiles de types forestiers WRI correspondantes (environ 37 Go pour les retraits). Il calcule pour chaque tuile les sommes pondérées par biome, puis combine les résumés de tuiles en un tableau CSV de quatre lignes, une par biome, avec le taux moyen, $\sigma_{b,\mathrm{spatial}}$, la surface et les champs de contrôle. Le résultat est le fichier `gfw_gibbs_biome_rates_non_mangrove.csv`, utilisé ensuite dans le calcul national. Pour l'exécution décrite ici, les taux déjà validés dans ce CSV ont été réutilisés; les tuiles brutes n'ont donc pas été retéléchargées ni réagrégées.

| Biome $b$ | Taux annuel moyen $\bar r_b$ (tC ha$^{-1}$ an$^{-1}$) | $\sigma_{b,\mathrm{spatial}}$ (tC ha$^{-1}$ an$^{-1}$) |
|---|---:|---:|
| Tropical | 0,9343985914 | 0,9269693002 |
| Subtropical | 1,3707381135 | 1,3227353783 |
| Tempéré | 1,4300688032 | 0,8013244813 |
| Boréal | 0,6186330269 | 0,2612148756 |

Le terme $\sigma_{b,\mathrm{spatial}}$ décrit la dispersion spatiale des pixels; il n'est pas l'erreur-type d'une estimation mondiale.

## 3. De la surface FRA au compte forestier GCW

Pour chaque entité $i$, $F_i^{\mathrm{declared}}$ est la surface FRA déclarée comme Forest, en hectares. Pour alléger les équations, on note ensuite $F_i=F_i^{\mathrm{declared}}$. $M_i^{FRA}$ est la surface FRA déclarée en mangroves. Selon le classement national, la catégorie des mangroves peut relever de Forest ou de Other wooded land (OWL); leur superficie totale n'est donc pas nécessairement incluse dans $F_i$.

Les rapports ne donnent pas tous une ventilation chiffrée de la superficie des mangroves entre les catégories Forest, OWL et les autres classes. Cela signifie parfois que la classe détaillée n'est pas connue, pas que la superficie totale de mangroves manque. L'audit porte sur 116 entités ayant une valeur FRA positive; une ventilation Forest est appliquée dans 26 cas. Le Brésil rapporte une superficie dans la catégorie Forest, le Mozambique répartit sa surface entre Forest (80 %) et OWL (20 %), et Sainte-Lucie la classe en OWL. Au total, 4 180 910 ha sont documentés dans la catégorie Forest; la ventilation entre Forest et OWL n'est pas vérifiée pour 11 613 440 ha.

On note $O_i^F$, $O_i^{OWL}$ et $O_i^R$ les surfaces documentées respectivement comme Forest, OWL et Remaining land, et $O_i^?$ la part sans ventilation établie. La décomposition de travail est :

$$
M_i^{FRA}=O_i^F+O_i^{OWL}+O_i^R+O_i^?.
$$

Les parts de biome $s_{ib}$ totalisent 1 et proviennent d'abord de la ventilation climatique FRA (FRA 2025); lorsque celle-ci n'est pas exploitable, elles sont estimées par croisement des domaines GEZ (FAO GEZ 2010) avec la couverture forestière JRC (JRC Global Forest Cover 2020), puis par la surface terrestre GEZ (FAO GEZ 2010) si aucune couverture forestière exploitable n'est observée. La surface déclarée $F_i$ est d'abord répartie entre les biomes. La superficie de mangrove dont l'inclusion dans la catégorie Forest est attestée, $O_i^F$, est ensuite retranchée une seule fois de la part tropicale (les mangroves sont considérées comme tropicales dans cette allocation de FRA) :

$$
A_{ib}=F_i s_{ib}-{\bf1}_{b=\mathrm{tropical}}O_i^F,
\qquad \sum_b A_{ib}=F_i-O_i^F.
$$

Le total des surfaces forestières allouées après correction peut donc être noté $A_i^{\mathrm{total}}=\sum_b A_{ib}=F_i-O_i^F$; il s'agit du résultat de cette correction, et non d'une seconde surface à soustraire dans la formule.

Les cartes GMW localisent les mangroves, mais ne révèlent pas à elles seules la classe FRA déclarée dans un rapport national. Pour les $11\,613\,440$ ha dont la ventilation entre Forest et OWL n'est pas établie, le compte principal ne retire donc rien. Pour mesurer l'effet maximal possible, une borne séparée suppose que toute cette surface inconnue $O_i^?$ est en réalité incluse dans Forest; elle est alors retirée de la part tropicale en plus de la surface documentée $O_i^F$. Dans cette hypothèse uniquement, la réduction supplémentaire des additions forestières atteint $38{,}69$ MtCO$_2$ an$^{-1}$, soit $0{,}262\,\%$ des additions forestières mondiales du compte. Si l'on combine cette hypothèse avec le retrait déjà appliqué aux $4\,180\,910$ ha documentés comme Forest, la réduction totale par rapport au scénario sans aucun retrait de chevauchement atteint environ $53{,}02$ MtCO$_2$ an$^{-1}$, soit $0{,}359\,\%$ du flux forestier sans correction. Cette hypothèse complète est une sensibilité de cas limite, pas une réattribution observée.

Pour chaque entité, les additions forestières physiques se calculent en multipliant les hectares par les taux annuels par biome, puis en convertissant le carbone en CO$_2$ :

$$
U_i^C=\sum_b A_{ib}\bar r_b\quad[\mathrm{tC/an}],
\qquad U_i=\frac{44}{12}U_i^C\quad[\mathrm{tCO_2/an}].
$$

La valeur GCW au tirage $d$ est :

$$
GCW_{i,d}=U_i\,GSCC_d\quad[\mathrm{USD\ 2015/an}].
$$

Les surfaces et les quatre taux restent fixes d'un tirage à l'autre; la variation de valeur vient principalement du tirage commun $GSCC_d$. Les variantes $r_b^- = \max(0,\bar r_b-\sigma_{b,\mathrm{spatial}})$ et $r_b^+=\bar r_b+\sigma_{b,\mathrm{spatial}}$ montrent l'effet d'une variation spatiale d'un écart-type. Ce sont des scénarios déterministes, pas des bornes de confiance.

**Exemple pour le Brésil.** 
>La surface Forest est $F_{BRA}=486\,086\,640$ ha. 
>Les parts tropicale et subtropicale valent 0,979 et 0,021; $O_{BRA}^F=1\,394\,680$ ha. 
>Après retrait de la mangrove classée Forest, $A_{trop}=474\,484\,140.56$ ha et $A_{subtrop}=10\,207\,819.44$ ha. 
>Les taux par biome donnent d'abord le flux de carbone ajouté à la biomasse vivante :
$$
U_{BRA}^{C}\simeq474\,484\,140.56\times0.9343985914+
10\,207\,819.44\times1.3707381135
=457\,349\,559.74\ \mathrm{tC/an}.
$$

On convertit ensuite ce flux en tonnes de CO$_2$ :

$$
U_{BRA}=\frac{44}{12}U_{BRA}^{C}
=1\,676\,948\,385.69\ \mathrm{tCO_2/an}.
$$

Enfin, pour chaque tirage du coût social du carbone, la valeur monétaire est calculée séparément :

$$
GCW_{BRA,d}=U_{BRA}\,GSCC_d
$$

$$
GCW_{BRA}=938\,374\,837\,901.72
\pm450\,418\,996\,844.68\ \mathrm{USD\ 2015/an}
\simeq(938.375\pm450.419)\ \text{milliards USD 2015/an}.
$$

## 4. Mise à jour du compte BCW : aires des écosystèmes marins

L’aire de mangrove rapportée par Hilmi et al. (2026) est actualisée avant le calcul du BCW. Dans les formules ci-dessous, $A_{i,\mathrm{mang}}^{\mathrm{sel}}$ désigne l’aire retenue pour l’entité $i$ après cette mise à jour; « sel » signifie « sélectionnée ». La procédure de sélection, ses sources et le traitement des valeurs absentes sont précisés dans la sous-section « Choix de l’aire de mangrove ».
Le compte BCW de Hilmi et al. (2026) associe les flux côtiers des mangroves, herbiers marins et marais salés au flux océanique de la pompe biologique (BCP). Pour une entité $i$ et un tirage commun $d$, le flux côtier de carbone est :

$$
S_{i,d}^{\mathrm{coast}}=
\frac{A_{i,\mathrm{mang}}^{\mathrm{sel}}}{100}R_{\mathrm{mang},d}
+A_{i,\mathrm{seag}}^{\mathrm{Hilmi\,2026}}R_{\mathrm{seag},d}
+A_{i,\mathrm{salt}}^{\mathrm{Hilmi\,2026}}R_{\mathrm{salt},d}
\quad[\mathrm{tC/an}].
$$

Les taux $R_{e,d}$ sont en tC/km$^2$/an. Les aires d’herbiers et de marais salés rapportées par Hilmi et al. (2026) sont en km$^2$. L’aire de mangrove retenue est en hectares; sa division par 100 dans la formule la convertit en km$^2$. Le flux $S_i^{BCP}$ de la pompe biologique est celui rapporté par Hilmi et al. (2026), en tC/an. Le flux bleu total valorisé est donc :

$$
S_{i,d}^{\mathrm{blue}}=\frac{44}{12}\left(S_{i,d}^{\mathrm{coast}}+S_i^{BCP}\right)
\quad[\mathrm{tCO_2/an}],
\qquad
BCW_{i,d}=S_{i,d}^{\mathrm{blue}}\,GSCC_d
\quad[\mathrm{USD\ 2015/an}].
$$

Ici, $S_{i,d}^{\mathrm{blue}}$ inclut les flux des trois écosystèmes côtiers et la BCP rapportée par Hilmi et al. (2026); $GSCC_d$ est le tirage du coût social mondial du carbone, en USD 2015/tCO$_2$.

### Aire des mangroves attribuée par intersection spatiale

L'aire de mangrove GMW pour 2025 est obtenue en croisant la couche de mangroves de 2025 avec les polygones EEZ de 2024 associés aux entités étudiées. Tous les polygones de mangrove présents dans la couche 2025 sont utilisés. On note $E_u$ l'union géométrique des polygones EEZ associés à l'entité $u$ et $G_k$ le polygone GMW $k$. Après reprojection en Mollweide (ESRI:54009), l'aire brute en hectares est :

$$
A_u^{GMW,raw}=\frac{1}{10\,000}\operatorname{Aire}_{54009}\!\left(E_u\cap\bigcup_{k\in\mathcal K_{2025}}G_k\right)\quad[\mathrm{ha}].
$$

GMW applique le facteur global de correction $0{,}9775$ à ses estimations d'aire. On l'applique à l'aire de chaque intersection :

$$
A_u^{GMW,corr}=0{,}9775\,A_u^{GMW,raw}.
$$

Pour chaque entité $i$, $\mathcal U_i$ est l'ensemble des géométries EEZ de type « Union EEZ and country » qui lui sont associées. L'aire brute et l'aire corrigée attribuées à l'entité sont :

$$
A_i^{GMW,raw}=\sum_{u\in\mathcal U_i}A_u^{GMW,raw},\qquad
A_i^{GMW,corr}=\sum_{u\in\mathcal U_i}A_u^{GMW,corr}=0{,}9775\,A_i^{GMW,raw}.
$$

L'intersection EEZ détermine l'entité à laquelle chaque surface est attribuée; le code pays `cntry_iso3` de GMW sert à décrire la provenance du polygone.

### Choix de l'aire de mangrove

Pour chaque entité $i$, l’aire de mangrove retenue suit cette hiérarchie : aire positive de l’intersection GMW 2025 corrigée; valeur FRA 2025 effectivement déclarée, y compris zéro; puis aire rapportée par Hilmi et al. (2026), si elle est renseignée. Une cellule FRA vide signifie « aucune valeur déclarée » et ne vaut pas zéro. La valeur numérique zéro est retenue uniquement si FRA déclare explicitement zéro. Dans l’extraction FRA 2025 utilisée ici, 110 valeurs sont des zéros déclarés, 116 sont positives et 10 cellules sont vides; la plateforme et les rapports FRA distinguent les données numériques de l’absence de valeur ([plateforme FRA](https://fra-data.fao.org/), [téléchargement des données](https://fra-data.fao.org/api/export/bulk-download/)).

Si GMW 2025 et FRA 2025 ne donnent pas d’aire pour une entité, on reprend l’aire rapportée par Hilmi et al. (2026). Si cette aire est elle-même absente chez Hilmi et al. (2026), alors $A_{i,\mathrm{mang}}^{\mathrm{sel}}=\mathrm{NaN}$ : l’aire est inconnue, elle n’est pas nulle. Ainsi, une valeur manquante chez Hilmi et al. (2026) reste manquante lorsque les deux sources plus récentes n’apportent pas d’aire. Toute aire retenue permet de calculer la composante mangrove; lorsqu’aucun compte BCW n’est publié par Hilmi et al. (2026) pour cette entité, le compte est calculé à partir de l’aire retenue et des composantes marines renseignées. Si aucune aire n’est disponible, un compte BCW publié par Hilmi est conservé sans recalcul.

L'aire de référence rapportée par Hilmi et al. (2026) est notée $A_{i,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}$. Elle n'est retenue qu'en dernier recours. Pour le Brésil, par exemple, la hiérarchie retient directement $A_{BRA,\mathrm{mang}}^{\mathrm{sel}}=1\,083\,926{,}377$ ha dans la couche GMW 2025 corrigée; l'aire rapportée par Hilmi et al. (2026) est $A_{BRA,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}=1\,137\,555{,}043$ ha.

Pour toute entité disposant d’une aire de mangrove retenue, cette aire remplace celle de Hilmi lorsqu’elle existe; les aires d’herbiers et de marais salés, leurs taux, le flux BCP rapporté et le tirage commun $GSCC_d$ complètent le calcul du BCW. Une composante marine manquante ne contribue pas numériquement à la somme (équivalent arithmétique à zéro); sa valeur NaN est conservée dans la ligne source. Lorsqu’on agrège plusieurs lignes BCW pour une même entité, les valeurs renseignées sont additionnées et les colonnes de couverture indiquent combien de lignes sources ont fourni chaque composante; si aucune ligne ne la renseigne, la valeur agrégée reste NaN. Un indicateur distingue les calculs dont toutes les composantes sont disponibles.

Les effectifs et montants ci-dessous décrivent les tables enregistrées le 28 octobre 2026, avant l’ajout du calcul d’un compte BCW lorsqu’une aire de mangrove est disponible mais qu’aucun compte Hilmi n’est publié. Ils ne sont donc pas les résultats de la règle désormais décrite; ils devront être actualisés lors de la régénération finale.

Hilmi et al. (2026) fournissent une aire de mangrove pour 119 des 266 entités; pour les 147 autres, aucune aire n’est indiquée. Après la sélection décrite ci-dessus, une aire est disponible pour 236 entités et reste NaN pour 30. La provenance des 236 aires retenues est :

| Source retenue | Entités | Aire retenue |
|---|---:|---:|
| GMW 2025, intersection corrigée | 126 | 14 815 223,7 ha |
| FRA 2025, valeur effectivement déclarée | 109 | 2 660 ha (3 valeurs positives, 106 zéros déclarés) |
| Aire rapportée par Hilmi et al. (2026), dernier recours | 1 | 62,4 ha |
| Aucune source disponible | 30 | NaN |

Parmi les 119 entités qui avaient déjà une aire rapportée par Hilmi et al. (2026), 118 reçoivent une aire différente; une conserve l’aire rapportée par Hilmi et al. (2026) comme dernier recours. Pour 117 entités, une aire est maintenant disponible alors qu’Hilmi et al. (2026) n'en rapportaient aucune. À périmètre comparable, la somme des aires passe de 11 187 925 ha à 11 104 147 ha, soit −83 778 ha (−0,75 %). Les 3 713 799 ha des 117 nouvelles entités élargissent la couverture; leur ajout explique pourquoi le total des aires disponibles n’est pas une comparaison à périmètre constant.
Hilmi et al. (2026) fournissent un compte BCW pour 180 entités. Parmi celles-ci, 178 ont maintenant une aire retenue et leur flux BCW est recalculé : 118 avec une aire qui remplace une valeur rapportée par Hilmi et al. (2026), 59 avec une aire nouvellement disponible et 1 avec l’aire rapportée par Hilmi et al. (2026) conservée. Les 2 comptes BCW pour lesquels l’aire reste NaN gardent leur valeur publiée sans recalcul. Les 58 entités restantes ont une aire retenue mais ne figurent pas parmi les comptes BCW publiés par Hilmi et al. (2026); elles ne sont donc pas intégrées à cette mise à jour du BCW.
Le total mondial du BCW porte sur les mêmes 180 comptes avant et après la mise à jour. Les statistiques des 20 000 tirages communs sont :

| Statistique BCW mondial | aire rapportée par Hilmi et al. (2026) | Après mise à jour | Variation |
|---|---:|---:|---:|
| Moyenne (milliards USD 2015/an) | 2 315,580 | 2 329,303 | +13,722 (+0,593 %) |
| P05 (milliards USD 2015/an) | 904,682 | 909,096 | +4,414 |
| Médiane (milliards USD 2015/an) | 2 101,732 | 2 113,411 | +11,679 |
| P95 (milliards USD 2015/an) | 4 266,823 | 4 297,953 | +31,131 |

Les variations sont calculées à partir des valeurs non arrondies; les petits écarts éventuels avec la soustraction des nombres affichés proviennent de l'arrondi.

La moyenne du BCW augmente donc de 13,722 milliards USD 2015/an, mais cette hausse n’est pas uniforme : l’Indonésie présente la plus forte hausse moyenne (+11,981 milliards USD 2015/an), tandis que le Mexique présente la plus forte baisse moyenne (−0,749 milliard USD 2015/an). Le résultat mondial augmente malgré une légère baisse de l’aire totale parmi les 119 entités directement comparables, car 117 entités auparavant sans aire reçoivent désormais une valeur et les flux sont redistribués entre entités.

## 5. Des Green et Blue CW au NCW

Pour chaque entité et chaque tirage commun $d$, le compte naturel est la somme des deux valeurs disponibles :

$$
NCW_{i,d}=GCW_{i,d}+BCW_{i,d}.
$$

Si une composante manque, la somme publiée représente la composante disponible et son état manquant reste identifiable; si les deux manquent, le total est manquant. Les lignes source BCW correspondant au même pays sont additionnées tirage par tirage. Le total mondial additionne les valeurs GCW et BCW disponibles pour les pays et territoires, puis ajoute la ligne BCW « Joint Regimes », qui n'est attribuée à aucune entité nationale :

$$
NCW_{monde,d}=\sum_{i\in\mathcal I_{GCW}}GCW_{i,d}
+\sum_{i\in\mathcal I_{BCW}}BCW_{i,d}+BCW_{JR,d}.
$$

Les ensembles $\mathcal I_{GCW}$ et $\mathcal I_{BCW}$ contiennent les pays et territoires pour lesquels le compte correspondant est disponible; $BCW_{JR,d}$ est la valeur de la ligne « Joint Regimes » au tirage $d$. Les 296 lignes brutes du fichier BCW sont toutes rattachées par la table de correspondance, puis réunies en 266 entités du compte final : plusieurs lignes territoriales peuvent contribuer au même pays ou territoire. Ce regroupement aligne les données BCW sur le niveau pays ou territoire utilisé par FRA et GCW. Par exemple, la ligne BCW « Trinidade » (`BR-ES`) est rattachée au Brésil (`BRA`), car la table de correspondance la décrit comme un sous-territoire inclus dans le pays FRA Brésil. Les données d’écosystèmes et de compte BCW de cette ligne sont manquantes : elle reste présente dans le fichier source et la table de correspondance, tandis que le compte final du Brésil regroupe les lignes qui lui sont rattachées. Le compteur de couverture permet de voir que le compte publié est renseigné pour une ligne sur deux; il ne transforme pas la ligne vide en zéro. Traiter Trinidade comme une entité de compte séparée demanderait aussi des données GCW et FRA indépendantes; la ligne BCW seule ne fournit pas ces comptes.

La table NCW utilise l’union des entités GCW, BCW et des aires de mangrove, et non leur intersection; une ligne est conservée même si l’un des deux comptes manque. Dans ce cas, le total correspond au compte disponible et la colonne de la composante manquante reste NaN.

Pour toute grandeur simulée $X$ (GCW, BCW ou NCW), son percentile d’ordre $p$ est calculé sur ses $D$ tirages. $Q_q$ désigne le quantile empirique d’ordre $q$; le percentile $p$ est exprimé sur une échelle de 0 à 100 :

$$
P_p^X=Q_{p/100}\!\left(\{X_d\}_{d=1}^{D}\right),\qquad p\in[0,100].
$$

Pour calculer un percentile mondial d’ordre quelconque $p$, on additionne d’abord les comptes des entités pour chaque tirage commun, puis on prend le quantile d’ordre $p/100$ des totaux ainsi obtenus :

$$
P_p^{NCW,\,monde}=Q_{p/100}\!\left(\{NCW_{monde,d}\}_{d=1}^{D}\right).
$$

Si l’on calcule d’abord le percentile de chaque entité puis qu’on additionne ces percentiles, on obtient une autre quantité :

$$
\sum_i P_{p,i}^{NCW}=\sum_i Q_{p/100}\!\left(\{N_{i,d}\}_{d=1}^{D}\right),
\qquad P_p^{NCW,\,monde}\ne\sum_i P_{p,i}^{NCW}\quad\text{en général}.
$$

Ici, $P_{p,i}^{NCW}$ est le percentile d’ordre $p$ du NCW du pays ou territoire $i$, tandis que $NCW_{monde,d}$ est le total mondial défini juste au-dessus. Les deux opérations ne coïncident généralement pas, car le quantile est calculé après une addition dans le premier cas, mais avant l’addition dans le second. Avec $D=20\,000$, les percentiles d’ordre 5 et 95 délimitent l’intervalle central de 90 %; la même méthode s’applique aux comptes GCW, BCW et NCW. À titre d’exemple, pour $p=5$ (P05), le percentile mondial du NCW vaut 4 163,868 milliards USD 2015/an. La somme des percentiles d’ordre 5 calculés séparément pour les entités vaut 4 128,259 milliards USD 2015/an (242 entités avec un NCW disponible), soit 35,609 milliards de moins. Cet écart inclut aussi le compte « Joint Regimes », présent dans le total mondial mais absent des 242 entités; il ne mesure donc pas uniquement la différence entre le percentile d'une somme et la somme des percentiles. Le même indice $d$ conserve les tirages communs du GSCC et des taux marins.

## 6. Comparaison avec le flux forestier net FAOSTAT

Cette analyse répond à une question de périmètre : comment les additions brutes estimées par le GCW se situent-elles par rapport au flux forestier net de FAOSTAT ? Elle met en regard deux grandeurs différentes. Le GCW estime les ajouts bruts modélisés par Gibbs/GFW; la série FAOSTAT sélectionnée estime le flux net forestier selon la méthode Tier 1 de la FAO, en tenant compte des retraits et des pertes compris dans son compte. Concrètement, la comparaison calcule la moyenne FAOSTAT 2015-2024 par entité, puis présente les plus grands puits et les plus grandes sources nets à côté du flux GCW correspondant. Elle sert à montrer la différence entre additions brutes et bilan net, et à éviter de présenter le GCW comme le bilan net de l'ensemble du secteur forestier.

Cette comparaison reste descriptive : elle ne valide pas l'un des deux comptes par l'autre et ne mesure pas quelle fraction du GCW est « annulée » par la déforestation. Les périmètres, les méthodes, les périodes et les composantes de carbone considérées diffèrent; les résultats ne sont donc pas deux mesures directement réconciliables. Dans la série FAOSTAT, les retraits sont négatifs et les émissions positives. Pour exprimer les retraits nets comme un flux positif, on inverse ce signe pour les années disponibles entre 2015 et 2024 :

$$
U^{FAO}_{i,t}=-1\,000\,Value_{i,t}\quad[\mathrm{tCO_2/an}],
\qquad \bar U^{FAO}_i=\frac{1}{n_i}\sum_{t\ disponible}U^{FAO}_{i,t}.
$$

La moyenne $\bar U^{FAO}_i$ est un indicateur comparatif de flux net selon le périmètre FAOSTAT. Elle ne remplace pas $U_i$ : les deux grandeurs couvrent des processus, des périodes et des périmètres différents.

## 7. Déforestation et capacité annuelle d'addition perdue

FRA définit la déforestation comme la conversion d'une forêt vers une autre utilisation des terres. Pour chaque entité $i$, le tableau FRA rapporte un taux annuel moyen en milliers d'hectares par an pour les périodes 2010-2015, 2015-2020 et 2020-2025. Il s'agit de moyennes annuelles sur chaque période, pas de superficies cumulées sur cinq ans. On retient la période renseignée la plus récente; un zéro déclaré reste zéro et l'absence de toutes les périodes reste NaN :

$$
t_i^{sel}=\begin{cases}
2020\text{-}2025 & \text{si cette période est renseignée},\\
2015\text{-}2020 & \text{sinon, si cette période est renseignée},\\
2010\text{-}2015 & \text{sinon, si cette période est renseignée},\\
\mathrm{NaN} & \text{si aucune période n'est renseignée},
\end{cases}
\qquad
D_i=1\,000\,D_{i,t_i^{sel}}^{FRA}\quad[\mathrm{ha/an}].
$$

Le taux moyen par hectare utilisé pour valoriser cette perte est celui du compte GCW de la même entité. Si $A_{ib}$ est la surface forestière du biome $b$ déjà définie pour la GCW, la surface totale du compte et son taux national moyen sont :

$$
A_i^{total}=\sum_b A_{ib}\quad[\mathrm{ha}],
\qquad
\bar u_i^{GCW}=\frac{U_i}{A_i^{total}}
\quad[\mathrm{tCO_2\ ha^{-1}\ an^{-1}}].
$$

$U_i$ est déjà exprimé en tCO$_2$/an et comprend la conversion $44/12$ appliquée dans le calcul de la GCW. Elle n'est donc pas appliquée une seconde fois ici. $\bar u_i^{GCW}$ correspond au taux des quatre biomes de l'entité, pondéré par leurs surfaces dans le compte forestier. Il varie d'une entité à l'autre.

Le taux FRA $D_i$ est converti en surface déboisée pendant une année, puis valorisé avec ce taux national moyen :

$$
A_i^{loss}=D_i\Delta t\quad[\mathrm{ha}],
\qquad \Delta t=1\ \mathrm{an},
$$

$$
\widehat L_i=A_i^{loss}\bar u_i^{GCW}
=D_i\Delta t\frac{U_i}{A_i^{total}}
\quad[\mathrm{tCO_2/an}].
$$

Cette valeur représente le flux annuel d'addition brute à la biomasse vivante que la surface déboisée pendant une année aurait pu soutenir, si son taux était celui du pays dans le compte GCW. Elle ne mesure ni le stock de carbone présent avant la conversion, ni les émissions libérées par la conversion, ni une perte observée séparément pour chaque biome.

La valeur monétaire de la capacité annuelle perdue utilise les mêmes tirages du coût social du carbone que le compte GCW :

$$
\widehat V_{i,d}=\widehat L_i\,GSCC_d
\quad[\mathrm{USD\ 2015/an}],
\qquad
P_p^{\widehat V_i}=Q_{p/100}\!\left(\{\widehat V_{i,d}\}_{d=1}^{20\,000}\right).
$$

Les percentiles $P_{05}$ et $P_{95}$ donnent l'intervalle central de 90 % des valeurs monétaires produites par les tirages du GSCC. La surface FRA et le taux moyen $U_i/A_i^{total}$ restent fixes dans ces tirages : cet intervalle reflète donc la distribution du GSCC, pas l'incertitude complète sur la déforestation ou le taux forestier. Si aucune période FRA n'est renseignée, la perte physique et sa valeur restent NaN; si FRA rapporte zéro, elles valent zéro. Une perte positive reste NaN si le compte GCW ou sa surface de référence ne permettent pas de calculer $U_i/A_i^{total}$.

Le calcul traite toute la surface de déforestation déclarée par FRA comme une surface forestière convertie et lui applique le taux moyen du pays. Il ne prétend pas connaître le biome effectivement perdu. La surface de référence $A_i^{total}$ suit le périmètre forestier utilisé dans la GCW, qui exclut seulement les mangroves explicitement classées comme forêt dans les rapports FRA. Si une partie de la perte déclarée par FRA concerne des mangroves ou d'autres surfaces hors de ce périmètre, elle est ici valorisée au taux forestier moyen du pays.
Enfin, ce calcul ne mesure pas les émissions du stock déboisé.

Le tableau calcule aussi la part de la surface forestière de référence correspondant à la surface déboisée pendant une année ($100A_i^{loss}/A_i^{total}$); avec le taux moyen national commun, cette part est égale à $100\widehat L_i/U_i$. Pour la sensibilité, on compare ce résultat central à deux scénarios : dans les deux, la surface déboisée est supposée avoir la même répartition entre biomes que la surface forestière comptabilisée dans le pays. Le scénario bas diminue le taux moyen de chaque biome d’un écart-type spatial; le scénario haut l’augmente du même écart-type. Ces scénarios déterministes ne sont pas des intervalles de confiance.

## 8. Émissions, PIB, population et balances comptables

Les émissions territoriales fossiles et industrielles de 2024 sont publiées par le Global Carbon Budget en MtC/an. Le facteur de conversion fourni par sa source est 3.664 tCO$_2$/tC :

$$
E_i=E_i^{MtC}\times3.664\times10^6\quad[\mathrm{tCO_2/an}].
$$

Les émissions territoriales sont comparées directement aux flux physiques déjà définis : $U_i$ pour les additions forestières et $S_{i,d}^{\mathrm{blue}}$ pour les écosystèmes côtiers et la pompe biologique.

Le PIB (en dollars constants 2015) et la population proviennent de la Banque mondiale. Pour chaque variable séparément, on retient la valeur 2024 si elle est renseignée; sinon, on prend 2023, puis 2022. Les années de source sont conservées par entité. Si aucune des trois années n’est renseignée, la valeur reste manquante; elle n’est pas remplacée par zéro ni par une estimation du pays souverain.

Les balances physiques avec les émissions $E_i$ de 2024 sont :

$$
Z^{GCW}_{i,d}=U_i-E_i,
\qquad Z^{NCW}_{i,d}=U_i+S_{i,d}^{\mathrm{blue}}-E_i
\quad[\mathrm{tCO_2/an}].
$$

La formule de $Z^{NCW}_{i,d}$ s'applique lorsque les deux composantes sont disponibles; si l'une manque, le total suit la règle des composantes disponibles définie à la section 5, sans transformer la valeur manquante en observation nulle. Ces balances sont des comparaisons comptables, pas des tests de neutralité climatique : les émissions fossiles et industrielles, les additions forestières brutes et les composantes marines n'ont pas le même périmètre écologique. Le ratio économique descriptif est $100\,\overline{GCW_i}/GDP_i^*$, en pourcentage du PIB, où $GDP_i^*$ est la dernière valeur disponible entre 2024, 2023 et 2022. Le ratio par habitant utilise de la même façon la dernière population disponible; si les années retenues pour le PIB et la population diffèrent, leurs années de source sont indiquées séparément.

## 9. Scénarios de financement et offre de restauration

### 9.1 Allocation hypothétique d'une part du GCW

Le scénario financier attribue hypothétiquement 2 % de la valeur annuelle de la GCW à chaque entité $i$. Le montant dépend du même tirage $d$ du GSCC que la GCW :

$$
\mathrm{Fin}_{i,d}^{2\%}=0.02\,GCW_{i,d}\quad[\mathrm{USD\ 2015/an}].
$$

Le facteur $0.02$ est une hypothèse de scénario, pas une estimation. $\mathrm{Fin}_{i,d}^{2\%}$ désigne une allocation annuelle théorique; elle ne mesure ni une dépense observée, ni le coût de restauration, ni un besoin financier. Cette notation évite de confondre l'allocation avec $F_i$, déjà utilisé pour la surface forestière.

### 9.2 Courbes d’offre de restauration

Cette section décrit comment les données de Busch et al. (2024) servent à estimer, pour chaque entité (pays ou territoire), le CO$_2$ que la restauration forestière pourrait capter et son coût. La courbe d’offre indique la quantité cumulée de CO$_2$ qui pourrait être restaurée à chaque niveau de coût; elle permet de situer ce potentiel par rapport à la capacité forestière annuelle perdue.

![Courbe d’offre de restauration forestière pour une entité fictive λ](courbe_offre_lambda.png)

*Exemple fictif : à un prix plafond de 35,72 USD 2015/tCO$_2$, les trois premières cellules sont retenues et offrent ensemble 4 100 tCO$_2$ pondérées sur 30 ans. Ces valeurs illustrent la lecture de la courbe; elles ne sont pas des résultats.*

La carte mondiale des possibilités de restauration forestière de Busch et al. (2024) comprend des cellules d’environ 1 km dans 138 pays à revenu faible ou intermédiaire. Pour chaque cellule $c$ de cette carte sont fournis une surface admissible à la restauration, des paramètres de croissance, un type de plantation et des coûts. $\mathcal C_i$ désigne l’ensemble des cellules rattachées à l’entité $i$ (pays ou territoire). Le calcul ne retient que les cellules qui ont les paramètres nécessaires et qui passent les critères d’admissibilité; les zones désertiques ou xériques et les mangroves sont exclues ([Busch et al. (2024)](https://www.nature.com/articles/s41558-024-02068-1)).

Un exemple fictif à deux cellules détaille le calcul ([voir ILLUSTRATION_COR.md](ILLUSTRATION_COR.md)).

#### 9.2.1 Du stock d’arbres au carbone par hectare

Le calcul suit la croissance et les coûts pendant les 30 années qui suivent le début de la restauration : c’est la période étudiée. Pour additionner des valeurs produites à des dates différentes, chaque année $t$ reçoit un coefficient de pondération $d_t=0.95^{t-1}$. Ce coefficient vaut 1 en année 1, puis diminue de 5 % par an; il donne ainsi moins de poids aux valeurs éloignées dans le temps. Il ne représente ni le poids des arbres ni une baisse biologique de leur croissance.

Pour la méthode $m\in\{\mathrm{NR}\ (\text{régénération naturelle}),\mathrm{P}\ (\text{plantation})\}$, le stock aérien suit la fonction de croissance de Chapman–Richards.
$A_{c,m}$ désigne le stock théorique maximal (en $\mathrm{tC/ha}$), et $k_{c,m}$ (en $\mathrm{an}^{-1}$, c'est-à-dire par an) règle la vitesse à laquelle ce stock est approché. Le stock à l'âge $a$ et sa variation entre deux âges successifs sont :

$$
S_{c,m}(a)=A_{c,m}(1-e^{-k_{c,m}a})^2,
\qquad
\Delta S_{c,m,t}=S_{c,m}(t)-S_{c,m}(t-1).
$$

$S_{c,m}(a)$ est le stock aérien vivant d’un hectare à l’âge $a$ : il part de zéro à l’âge 0 et tend vers $A_{c,m}$ à mesure que le peuplement grandit. $k_{c,m}$ règle la vitesse de cette croissance. $\Delta S_{c,m,t}$ est la variation du stock entre deux âges successifs, et constitue l’addition aérienne de l’année avant prise en compte du poids $d_t$. Avant ce calcul, toute valeur négative de $A$ ou $k$ est ramenée à zéro.

En régénération naturelle (NR), les additions aériennes sont pondérées puis cumulées sur 30 ans. Le carbone souterrain est estimé en multipliant ce cumul aérien par le rapport racines/parties aériennes $r_c^{NR}$. Ce rapport suit les règles associées à la zone écologique de la FAO, au pays ou au continent et, lorsque la règle le prévoit, au genre d'arbre; en l’absence de règle particulière, la valeur retenue est $0.26$. Le sol contribue au cumul selon le taux annuel de $0.415107735\ \mathrm{tC\,ha^{-1}\,an^{-1}}$ utilisé dans le modèle source :

$$
\begin{aligned}
C_{c,\mathrm{aérien}}^{NR}&=\sum_{t=1}^{30}d_t\Delta S_{c,NR,t},&
C_{c,\mathrm{racines}}^{NR}&=r_c^{NR}C_{c,\mathrm{aérien}}^{NR},\\
C_{c,\mathrm{sol}}^{NR}&=0.415107735\sum_{t=1}^{30}d_t,&
C_{c,NR}^{*}&=C_{c,\mathrm{aérien}}^{NR}
+C_{c,\mathrm{racines}}^{NR}+C_{c,\mathrm{sol}}^{NR}.
\end{aligned}
$$

$C_{c,NR}^{*}$ additionne le carbone aérien, le carbone racinaire estimé et l’apport du sol. C’est un cumul pondéré sur 30 ans, par hectare, et non un taux annuel.

La sensibilité ne modifie que le taux annuel d’apport du sol en régénération naturelle :

| Scénario | Taux NR du sol (tC/ha/an) |
|---|---:|
| Référence Busch et al. | 0,415107735 |
| Aucun changement du carbone du sol | 0 |
| Post et Kwon (2000) | 0,338 |

Le taux de Post et Kwon correspond à la conversion de leur moyenne de $33{,}8\ \mathrm{gC/m^2/an}$ pour l'accumulation du carbone du sol lors de l'établissement forestier sur des terres agricoles. C’est un scénario comparatif, car cette moyenne n’est propre ni aux cellules de Busch ni à la seule régénération naturelle ([Post et Kwon, 2000](https://doi.org/10.1046/j.1365-2486.2000.00308.x)). Le taux du sol en plantation reste fixé à la valeur de Busch ($0{,}092749069\ \mathrm{tC/ha/an}$). Pour chaque scénario, le calcul recalcule le carbone NR, le choix de méthode cellule par cellule, les quantités, les courbes d’offre et les coûts d’atteinte de la cible. Ces scénarios déterministes ne sont pas des intervalles d’incertitude.

#### 9.2.2 Rotation, stock vivant et carbone récolté

Dans le scénario de plantation, une **rotation** est la période entre la plantation des arbres et leur coupe. Après la coupe, le calcul suppose qu’une nouvelle plantation commence. La durée de cette période, notée $H_c$, est exprimée en années et peut varier d’une cellule $c$ à l’autre. La coupe est simulée dans le modèle; elle ne décrit pas une intervention réelle. La régénération naturelle, elle, n’a pas de rotation ni de coupe dans ce calcul.

Le type de plantation détermine $A_{c,P}$ et $k_{c,P}$ à partir des paramètres disponibles pour Pinus, Cunninghamia, Eucalyptus et quatre groupes fonctionnels (feuillus persistants ou caducs, et arbres à aiguilles persistants ou caducs). Pour choisir la rotation, on calcule la croissance relative entre les âges $a-1$ et $a$ :

$$
g_{c,a}=\frac{S_{c,P}(a)-S_{c,P}(a-1)}{S_{c,P}(a-1)}.
$$

$g_{c,a}$ est une hausse relative (multipliée par 100, elle s’exprime en pourcentage). Pour chaque âge $a=2,\ldots,29$, elle est comparée au seuil du critère de rotation défini pour un taux annuel d’actualisation de 5 % :

$$
g_{c,a}>\frac{0.05}{1-(1.05)^{-a}}.
$$

On retient le dernier âge $a^*$ qui satisfait ce critère, puis on fixe la durée de rotation à $H_c=a^*+1$ (durée du cycle de plantation que le modèle utilise pour simuler les coupes et les replantations). Par exemple, si le dernier âge retenu est $a=9$, alors $H_c=10$ ans et la première coupe est simulée en année 10. Si aucun âge ne satisfait le critère, $H_c=31$ sert uniquement à indiquer qu’il n’y a pas de coupe pendant les 30 années étudiées : cela ne signifie pas qu’une coupe a lieu à 31 ans.

À chaque coupe, les arbres de la plantation sont récoltés et la nouvelle plantation repart à l’âge zéro. Le reste ($t\bmod H_c$, *modulo*) donne l’âge des arbres après l’événement de l’année $t$, alors que $[(t-1)\bmod H_c]$ donne leur âge à la fin de l’année précédente. La différence entre les deux stocks mesure donc la variation annuelle du carbone aérien encore vivant :

$$
C_{c,\mathrm{aérien}}^{P}
=\sum_{t=1}^{30}d_t
\left[S_{c,P}(t\bmod H_c)-S_{c,P}((t-1)\bmod H_c)\right].
$$

Pourquoi la variation devient-elle négative l’année de coupe ? Pour une rotation de $H_c=10$ ans, le bilan se lit en trois temps :

1. À la fin de l’année 9, le stock aérien vivant vaut $S_{c,P}(9)$.
2. Pendant l’année 10, les arbres grandissent jusqu’à $S_{c,P}(10)$.
3. La coupe retire ce stock et ramène le stock vivant à $S_{c,P}(0)=0$.

La variation de l’année 10 est donc la croissance de l’année moins tout le stock récolté :

$$
S_{c,P}(0)-S_{c,P}(H_c-1)
=\underbrace{[S_{c,P}(H_c)-S_{c,P}(H_c-1)]}_{\text{croissance pendant l’année}}
-\underbrace{S_{c,P}(H_c)}_{\text{stock récolté}}.
$$

Ainsi, pour $H_c=10$, le terme aérien de l’année 10 est $d_{10}[S_{c,P}(0)-S_{c,P}(9)]$. Dans l’exemple de la cellule, $S_{c,P}(9)=43.613407\ \mathrm{tC/ha}$ et $S_{c,P}(0)=0$. Le stock vivant varie donc de $-43.613407\ \mathrm{tC/ha}$ avant pondération, soit $-27.487324\ \mathrm{tC/ha}$ après multiplication par $d_{10}=0.630249$.

Ce résultat est la baisse du carbone encore vivant; il ne remplace pas le carbone récolté, qui est compté séparément. Aux années de coupe $H_c,2H_c,\ldots$, le stock récolté est $S_{c,P}(t)$; à la première coupe, c’est donc $S_{c,P}(10)$. Seule la fraction $w_i$ qui reste stockée dans les produits bois à longue durée de vie est ajoutée au cumul. $w_i$ décrit cette part de carbone; il est distinct du prix de vente du bois $p_i$, qui intervient plus loin dans le calcul du coût :

$$
\begin{aligned}
C_{c,\mathrm{racines}}^{P}&=r_c^P C_{c,\mathrm{aérien}}^{P},\\
C_{c,\mathrm{sol}}^{P}&=0.092749069\sum_{t=1}^{30}d_t\,\mathbf 1(t<H_c),\\
C_{c,\mathrm{récolté}}^{P}&=\sum_{t=1}^{30}\mathbf 1(t\bmod H_c=0)\,d_tS_{c,P}(t),\\
C_{c,P}^{*}&=C_{c,\mathrm{aérien}}^{P}+C_{c,\mathrm{racines}}^{P}
+C_{c,\mathrm{sol}}^{P}+w_iC_{c,\mathrm{récolté}}^{P}.
\end{aligned}
$$

$r_c^P$ est le rapport racines/parties aériennes propre aux plantations et peut différer de celui de la régénération naturelle. Le sol reçoit le taux annuel de $0.092749069\ \mathrm{tC\,ha^{-1}\,an^{-1}}$, mais seulement jusqu’à la première coupe. $\mathbf 1(t<H_c)$ compte cet apport au sol avant la coupe, tandis que $\mathbf 1(t\bmod H_c=0)$ sélectionne les années de coupe. $C_{c,P}^{*}$ est le cumul pondéré sur 30 ans, par hectare, exprimé en $\mathrm{tC/ha}$.

#### 9.2.3 Coûts et choix de méthode par cellule

La surface de la cellule, notée $A_c^{\mathrm{cell}}$, est exprimée en $\mathrm{m^2}$. Elle est convertie en hectares à l'aide de $a_c=A_c^{\mathrm{cell}}/10\,000$. Les montants monétaires des données Busch sont exprimés en dollars 2020; ils sont convertis en dollars 2015 avec le CPI-U annuel moyen du Bureau of Labor Statistics (2015 : 237.017; 2020 : 258.811) ([source](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm)) :

$$
f_{20\rightarrow15}=\frac{237.017}{258.811}\simeq0.9158.
$$


Les champs $nr\_cost$, $np\_cost$ et $ep\_cost$ sont les coûts de mise en place de la régénération naturelle, d’une plantation native et d’une plantation exotique. Ils couvrent l’installation puis la gestion pendant environ trois à cinq ans; les données Busch les expriment en dollars 2020 par hectare. Le champ $crop\_va$ est le coût annuel d’opportunité du terrain par hectare, soit le revenu net auquel on renonce en affectant le terrain à la restauration. Ces quatre coûts sont convertis en dollars 2015 avec le facteur défini ci-dessus. Les autres paramètres utilisés ici sont :

| Symbole                                     | Définition                                                                                                                                          | Unité                 |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| $nr\_cost^{2015}$                           | Coût de mise en place et de gestion initiale de la régénération naturelle                                                                           | USD 2015/ha           |
| $np\_cost^{2015}$                           | Coût de mise en place et de gestion initiale d’une plantation native                                                                                | USD 2015/ha           |
| $ep\_cost^{2015}$                           | Coût de mise en place et de gestion initiale d’une plantation exotique                                                                              | USD 2015/ha           |
| $crop\_va^{2015}$                           | Coût annuel d’opportunité du terrain                                                                                                                | USD 2015/(ha·an)      |
| $e_i$                                       | Part nationale des plantations constituée d’espèces exotiques, appliquée aux cellules de l’entité $i$; valeur Busch fondée sur FRA 2020, tableau 24 | Fraction entre 0 et 1 |
| $p_i^{2015}$                                | Coefficient national de recette nette des produits bois par tonne de carbone récoltée, après coûts de récolte et de livraison                       | USD 2015/tC           |
| $C_{c,\mathrm{récolté}}^{P}$                | Carbone récolté par hectare pendant la période de 30 ans, pondéré par $d_t$                                                                         | tC/ha                 |
| $E_{c,P}^{(0)}$/ $E_{c,P}^{(t)}$/ $E_{c,P}$ | Coût d’installation initial / cumulé jusqu’à $t$ / puis total sur 30 ans, par hectare                                                               | USD 2015/ha           |
| $K_{c,NR}$, $K_{c,P}$                       | Coût net total de la cellule pour la régénération naturelle ou la plantation                                                                        | USD 2015/cellule      |

Le paramètre $e_i$ représente la part des plantations de l’entité $i$ constituée d’espèces d’arbres exotiques (non indigènes). Il sert à calculer le coût moyen d’une plantation en pondérant les coûts des plantations exotiques et natives. Par exemple, pour un genre sans règle particulière, $e_i=0{,}25$ donne $0{,}25\,ep\_cost+0{,}75\,np\_cost$. Le programme impose deux exceptions : il retient le coût exotique pour Eucalyptus et Cunninghamia hors de Chine, et le coût natif pour Cunninghamia en Chine.

Les coûts totaux de la cellule s’obtiennent ensuite ainsi :

$$
\begin{aligned}
E_{c,P}^{(0)}&=e_i ep\_cost^{2015}+(1-e_i)np\_cost^{2015},\\
E_{c,P}^{(t)}&=E_{c,P}^{(t-1)}
[1+d_t\mathbf 1(t\bmod H_c=0)],\qquad E_{c,P}=E_{c,P}^{(30)},\\
K_{c,NR}&=a_c\left[nr\_cost^{2015}+crop\_va^{2015}\sum_{t=1}^{30}d_t\right],\\
K_{c,P}&=a_c\left[E_{c,P}+crop\_va^{2015}\sum_{t=1}^{30}d_t-p_i^{2015}C_{c,\mathrm{récolté}}^{P}\right].
\end{aligned}
$$

$E_{c,P}^{(0)}$ est le coût initial, $E_{c,P}^{(t)}$ le coût cumulé jusqu’à l’année $t$, et $E_{c,P}$ le total sur les 30 ans. Le coût de plantation $E_{c,P}$ apparaît uniquement dans $K_{c,P}$, car il correspond à la mise en place et au renouvellement des plantations. Il n’apparaît pas dans $K_{c,NR}$, qui décrit le coût de la régénération naturelle.
Lorsqu’il n’y a pas de récolte l’année $t$, $E_{c,P}^{(t)}$ reste égal à $E_{c,P}^{(t-1)}$. Lorsqu’une récolte a lieu, il est multiplié par $1+d_t$, selon la règle du programme ($d_t$ et $H_c$ sont définis plus haut).

$K_{c,NR}$ et $K_{c,P}$ sont les coûts nets totaux de la cellule en dollars 2015 : on additionne le coût d’installation et le coût d’opportunité des terres, puis on retranche, pour une plantation, la recette nette des produits bois associés au carbone récolté. Le terme $p_i^{2015}C_{c,\mathrm{récolté}}^{P}$ est cette recette par hectare; multiplié par $a_c$, il devient la recette totale de la cellule.

Avant de calculer les rapports, on applique le filtre spatial propre à chaque méthode. $B_{c,m}=1$ si la cellule $c$ est à moins de 5 km d’une forêt naturelle existante pour la régénération naturelle ($m=NR$), ou à moins de 40 km d’une plantation existante pour la plantation ($m=P$); sinon, $B_{c,m}=0$. Ces distances servent respectivement de critères de proximité aux sources de graines et aux infrastructures de plantation et de transformation du bois ([Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1)).
La méthode est choisie en comparant le carbone actualisé par dollar net et par hectare :

$$
R_{c,NR}=\frac{C_{c,NR}^{*}B_{c,NR}}{K_{c,NR}/a_c},
\qquad
R_{c,P}=\frac{C_{c,P}^{*}B_{c,P}}{K_{c,P}/a_c}.
$$

Les ratios comparent ainsi le carbone par hectare au coût net par hectare et s’expriment en $\mathrm{tC/USD\ 2015}$. La méthode ayant le ratio le plus élevé est retenue; la règle de Busch retient aussi la plantation lorsque son coût net est négatif. On note $m_c^*$ la méthode choisie.

Après ce choix, le coût $K$ de la méthode retenue sert encore dans les sections 9.2.4 et 9.2.5. Il entre dans le prix $p_{ic}^{\mathrm{courbe}}$, qui détermine à quel seuil de prix la quantité de la cellule apparaît dans la courbe d’offre. Il entre aussi dans le coût effectif par tonne additionnelle $\widetilde p_{ic}$, défini en section 9.2.5, qui sert à classer les cellules pour atteindre la cible. Les coûts des cellules retenues sont enfin additionnés, en tenant compte de la part mobilisée pour la dernière cellule, afin d’obtenir le coût total de cette cible.

#### 9.2.4 Quantité admissible et courbe nationale

Le filtre général $G_c$ vaut 1 si la cellule passe l’écran géographique de potentiel de reboisement utilisé par Busch et al. à partir de [Griscom et al. (2017)](https://doi.org/10.1073/pnas.1710465114), et 0 sinon. Cet écran écarte notamment les déserts, les forêts existantes, les zones de haute altitude, les prairies naturelles et les terres cultivées ([Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1)). Il s’ajoute aux filtres $B_{c,m}$ définis à la section 9.2.3.

Ces deux filtres de faisabilité sont binaires. Une valeur manquante vaut 0. Une cellule ne contribue à l’offre que si $G_c=1$ et si le filtre correspondant à la méthode retenue, $B_{c,m_c^*}$, vaut également 1.

$bau_{2020\text{--}2030,c}$, $bau_{2030\text{--}2040,c}$ et $bau_{2040\text{--}2050,c}$ sont les fractions de reboisement attendues sans projet dans la cellule $c$ pour chacune des trois périodes. Leur moyenne pondérée donne $BAU_c$ (business-as-usual, scénario sans projet), la part de carbone qui aurait été ajoutée même sans projet. La part attribuée au projet est donc $1-BAU_c$. Si les trois entrées ne permettent pas de calculer cette moyenne, la valeur retenue pour $BAU_c$ est $0.0571795$ :

$$
BAU_c=0.510928\,bau_{2020\text{--}2030,c}
+0.305911\,bau_{2030\text{--}2040,c}
+0.183161\,bau_{2040\text{--}2050,c}.
$$

La quantité admissible multiplie le carbone par hectare par la surface, les deux masques et la part additionnelle; $44/12$ convertit le carbone en CO$_2$ :

$$
q_{ic}^{*}=a_cC_{c,m_c^*}^{*}G_cB_{c,m_c^*}(1-BAU_c)\frac{44}{12}
\quad[\mathrm{tCO_2\ actualisées/cellule}].
$$

Comme $C^*$ est déjà pondéré sur 30 ans, $q_{ic}^{*}$ représente la quantité totale de CO$_2$ que la cellule peut offrir sur cette période, après application des masques et de l’additionnalité. C’est un cumul pondéré sur 30 ans, pas une quantité annuelle. La reconstruction utilise le rapport exact $44/12$; le facteur arrondi $3.67$ sert uniquement au contrôle distinct des prix de la courbe publiée.

Le prix de courbe divise le coût total de la méthode choisie par son carbone total avant masques et additionnalité :

$$
p_{ic}^{\mathrm{courbe}}
=\frac{K_{c,m_c^*}}{(44/12)a_cC_{c,m_c^*}^{*}}
\quad[\mathrm{USD\ 2015/tCO_2\ actualisée}].
$$

Les masques et $1-BAU_c$ réduisent donc la quantité offerte, mais pas ce prix de classement dans la courbe. On retient les cellules admissibles dont la quantité est positive et finie et dont le prix est calculable; leur ensemble est noté $\mathcal C_i^{+}$. Au seuil de prix $p$, la courbe nationale additionne la quantité des cellules dont le prix de courbe ne dépasse pas ce seuil :

$$
V_i(p)=\sum_{c\in\mathcal C_i^{+}}q_{ic}^{*}
\mathbf 1(p_{ic}^{\mathrm{courbe}}\le p).
$$

Les seuils de la courbe publiée vont de $-20$ à $100$ USD 2020/tCO$_2$, par pas de 5 USD 2020. Pour classer la reconstruction en dollars 2015, chacun de ces seuils est multiplié par $f_{20\rightarrow15}$. Le contrôle de reproduction du classeur publié conserve, séparément, les seuils d’origine en dollars 2020.

#### 9.2.5 Coût nécessaire pour atteindre la cible

$\widehat L_i$ est la capacité annuelle d’addition perdue définie à la section 7. La cible suppose que cette perte se répète pendant 30 ans, avec les mêmes poids $d_t$ :

$$
D_{30}=\sum_{t=1}^{30}0.95^{t-1}=15.7072247,
\qquad
Q_i^{\mathrm{cible}}=L_iD_{30}
\quad[\mathrm{tCO_2\ actualisées}].
$$

Si $\sum_{c\in\mathcal C_i^{+}}q_{ic}^{*}<Q_i^{\mathrm{cible}}$, les cellules disponibles ne suffisent pas à atteindre la cible et aucun coût d’atteinte n’est calculé. Cette comparaison porte sur les entités avec perte positive et courbe nationale publiée; seules les cellules ayant une quantité positive et un coût calculable participent au classement.

Lorsque l’offre suffit, la cible est atteinte en classant les cellules par coût net rapporté à la quantité additionnelle qu’elles fournissent après les filtres :

$$
\widetilde p_{ic}=\frac{K_{c,m_c^*}}{q_{ic}^{*}}
\quad[\mathrm{USD\ 2015/tCO_2\ actualisée}].
$$

$\widetilde p_{ic}$ est le coût effectif par tonne additionnelle de la cellule; contrairement au prix de courbe $p_{ic}^{\mathrm{courbe}}$, son dénominateur inclut les masques et l’additionnalité. Les cellules sont prises par ordre croissant de $\widetilde p_{ic}$ jusqu’à la cible. $\alpha_{ic}$ est la fraction de la cellule retenue : 1 pour une cellule entièrement mobilisée, entre 0 et 1 pour la dernière cellule si la cible est atteinte en cours de cellule, et 0 pour les cellules suivantes. Si $\widetilde p_{i,\mathrm{marg}}$ est le coût effectif par tonne de cette dernière cellule mobilisée, les trois coûts actualisés en dollars 2015 sont :

$$
\begin{aligned}
K_i^{\mathrm{net}}&=\sum_c\alpha_{ic}K_{c,m_c^*},\\
K_i^{+}&=\sum_c\alpha_{ic}\max(K_{c,m_c^*},0),\\
K_i^{\mathrm{uniform}}&=\max(\widetilde p_{i,\mathrm{marg}},0)Q_i^{\mathrm{cible}}.
\end{aligned}
$$

$K_i^{\mathrm{net}}$ conserve les recettes et les coûts négatifs; $K_i^{+}$ additionne seulement les coûts positifs. $K_i^{\mathrm{uniform}}$ applique le prix de la dernière cellule mobilisée à toutes les tonnes de la cible, sans paiement négatif; c’est un scénario de paiement uniforme, pas une dépense observée. Les coûts étant déjà exprimés en dollars 2015, leur équivalent annuel est obtenu en divisant la valeur actualisée par $D_{30}$ :

$$
K_i^{x,\mathrm{annuel,2015}}
=\frac{K_i^{x,\mathrm{PV,2015}}}{D_{30}},
\qquad x\in\{\mathrm{net},+,\mathrm{uniform}\}.
$$

La division par $D_{30}$ répartit chaque valeur actualisée sur les 30 années pondérées. Le rapport CPI n’est donc pas appliqué une seconde fois à ce stade.

Pour un exemple chiffré détaillé, voir [ILLUSTRATION_COR.md](ILLUSTRATION_COR.md).
## 10. Analyses descriptives et spatiales

Les statistiques descriptives résument les valeurs nationales disponibles. La médiane partage l'échantillon en deux; la part des dix premières entités est leur somme divisée par la somme totale; le coefficient de Gini résume l'inégalité de la distribution (0 correspond à l'égalité parfaite et 1 à la concentration maximale). Le test de Kruskal-Wallis compare les rangs entre plusieurs groupes; les tests de Mann-Whitney comparent les rangs deux groupes à la fois; la correction de Holm ajuste les valeurs $p$ de plusieurs tests pour contrôler le risque de faux positifs dans la famille de comparaisons. La corrélation de rang de Spearman mesure l'association monotone entre les rangs de GCW et d'érosion relative. Ces résumés et tests sont descriptifs; ils ne démontrent pas un lien causal.

Les analyses spatiales examinent trois résultats principaux : la capacité annuelle perdue, exprimée en MtCO$_2$/an; son ratio au GCW, exprimé en pourcentage; et le GCW rapporté au PIB, également en pourcentage. $x_i$ est la valeur numérique observée du résultat dans l'entité indiquée; $y_i=\ln(1+x_i)$ est sa transformation par logarithme naturel, qui conserve les zéros. Une extension ajoute les émissions territoriales de 2024, en MtCO$_2$/an, comme variable explicative et comme résultat. Chaque estimation utilise les entités disposant de toutes les variables requises pour cette relation.

Les variables explicatives de base comprennent le logarithme du PIB par habitant, $\ln(GDP_i^*/Pop_i^*)$; le `log1p` de la surface forestière en millions d'hectares, $\ln(1+A_i^{\mathrm{total}}/10^6)$ lorsque l'aire est en hectares; et la part tropicale et subtropicale $s_{i,\mathrm{tropical}}+s_{i,\mathrm{subtropical}}$. Dans la suite, $X$ désigne la matrice de ces variables explicatives pour les $n$ entités de l'échantillon considéré, avec une constante; l'extension y ajoute les émissions territoriales lorsque celles-ci sont utilisées comme explicative.

Deux définitions du voisinage sont comparées pour chaque échantillon. Soit $a_{ij}=1$ lorsque les entités $i$ et $j$ sont voisines, et 0 sinon; la diagonale $a_{ii}$ vaut 0. 
- Le voisinage Queen relie deux polygones qui partagent une frontière ou un sommet. 
- Le voisinage des cinq plus proches voisins est construit à partir des cinq points géographiques représentatifs les plus proches de chaque entité, puis les liens sont symétrisés : une paire est reliée si $i$ choisit $j$ ou si $j$ choisit $i$. 
Les liens sont d'abord restreints aux entités de l'échantillon complet de l'analyse, puis standardisés par ligne :

$$
w_{ij}=\frac{a_{ij}}{\sum_{\ell=1}^{n}a_{i\ell}}
\quad\text{si } \sum_{\ell=1}^{n}a_{i\ell}>0;
\qquad
w_{ij}=0\quad\text{pour une entité isolée}.
$$

La matrice $W=(w_{ij})$ contient ces poids; $w_{ij}$ est le poids attribué à l'entité $j$ dans le voisinage de $i$. Pour une entité non isolée, les poids de sa ligne totalisent 1.

Pour un résultat transformé $y_i$, $\bar y=n^{-1}\sum_i y_i$ est sa moyenne dans l'échantillon, $z_i=y_i-\bar y$ sa valeur centrée et $z$ le vecteur des valeurs centrées; le symbole $\top$ désigne la transposée d'un vecteur ou d'une matrice. $n$ est le nombre d'entités de cet échantillon. 
L'indice global de Moran s'écrit :

$$
I=\frac{n}{S_0}\frac{z^\top Wz}{z^\top z},
\qquad S_0=\sum_i\sum_jw_{ij}.
$$

$S_0$ est la somme de tous les poids de voisinage. Comme les lignes sont standardisées, $S_0$ correspond au nombre d'entités non isolées; il peut être inférieur à $n$ pour le voisinage Queen, qui conserve les entités isolées sous forme de lignes nulles. La significativité de $I$ est évaluée par 9 999 permutations des valeurs entre entités, en gardant la matrice $W$ fixe; le test est bilatéral. Il est calculé pour les résultats transformés et pour les résidus $\hat u_i=y_i-X_i\hat\beta$ du modèle OLS, où $X_i$ est la ligne de $X$ pour l'entité $i$ et le chapeau indique une valeur estimée.

Les régressions spatiales candidates s'écrivent :

$$
\mathbf y=\rho W\mathbf y+X\boldsymbol\beta+WX\boldsymbol\theta+\mathbf u,
\qquad
\mathbf u=\lambda W\mathbf u+\boldsymbol\varepsilon.
$$

$\mathbf y$ est le vecteur des résultats transformés ($n\times1$); $X$ est la matrice des variables explicatives ($n\times k$), où $k$ est le nombre de colonnes explicatives, constante comprise; $W$ est la matrice de voisinage ($n\times n$) définie ci-dessus. $W\mathbf y$ donne, pour chaque entité, la moyenne pondérée du résultat chez ses voisins; $WX$ donne de la même façon les moyennes pondérées des variables explicatives voisines. $\boldsymbol\beta$ et $\boldsymbol\theta$ sont des vecteurs de coefficients; $\rho$ mesure la présence d'un terme spatial du résultat; $\mathbf u$ est l'erreur du modèle; $\lambda$ mesure sa dépendance spatiale; et $\boldsymbol\varepsilon$ est le terme d'erreur non spatial.

**Enchaînement des diagnostics et des comparaisons.** À partir de l'échantillon et de la matrice de voisinage définis plus haut, l'analyse suit les étapes suivantes :

1. **Estimer le modèle de référence OLS (moindres carrés ordinaires).** Il ne contient pas de terme spatial : $\rho=\lambda=0$ et $\boldsymbol\theta=\mathbf0$.
2. **Vérifier l'autocorrélation spatiale avec l'indice de Moran.** Le test porte d'abord sur le résultat transformé, puis sur les résidus OLS. Si les résidus restent spatialement autocorrélés, cela indique que la structure spatiale n'est pas entièrement prise en compte par OLS; l'autocorrélation du résultat seul ne suffit pas à établir ce point. La significativité est évaluée par 9 999 permutations et les valeurs $p$ sont ajustées par Holm.
3. **Diagnostiquer la forme de la dépendance avec les tests LM (multiplicateurs de Lagrange).** Les tests simples et robustes portent sur les résidus OLS. Ils examinent les termes de retard spatial ($\rho$) et d'erreur spatiale ($\lambda$), ainsi que les tests conjoints SARMA et SDM. Un signal de retard conduit à examiner particulièrement SAR et SDM; un signal d'erreur conduit à examiner SEM et SDEM; si les diagnostics indiquent plusieurs termes, GNS fait aussi partie des modèles à comparer. Les valeurs $p$ sont ajustées par Holm pour chaque type de test.
4. **Estimer les six modèles candidats pour chaque cas, quel que soit le résultat des diagnostics.** SAR (modèle autorégressif spatial) estime $\rho$; SEM (modèle à erreur spatiale) estime $\lambda$; SDM (modèle de Durbin spatial) estime $\rho$ et $\boldsymbol\theta$; SDEM (modèle d'erreur de Durbin spatial) estime $\lambda$ et $\boldsymbol\theta$; GNS (modèle spatial général englobant) estime les trois termes spatiaux. OLS fixe ces trois termes à zéro. Les résultats LM orientent donc la lecture des candidats, mais ne commandent pas leur estimation dans le processus exécuté.
5. **Comparer les modèles emboîtés avec les tests LR (rapports de vraisemblance).** Les comparaisons portent sur SDM contre SAR (restriction $\boldsymbol\theta=\mathbf0$), SDEM contre SEM (restriction $\boldsymbol\theta=\mathbf0$) et GNS contre SDM (restriction $\lambda=0$). Les valeurs $p$ sont ajustées par Holm pour chaque comparaison. Si une restriction est rejetée, le modèle qui lève cette restriction apporte un meilleur ajustement statistique dans cette comparaison; sinon, le test ne met pas en évidence cet apport.
6. **Mettre les éléments de comparaison en regard.** Pour chaque résultat et chaque matrice de voisinage, le critère d'information d'Akaike (AIC) et le critère d'information bayésien (BIC) classent les six candidats. Les tests et ces classements documentent les différences, mais ne désignent pas automatiquement un modèle scientifique final; les associations estimées ne sont pas interprétées comme des effets causaux.

## 11. Cohérence des calculs et résultat final

La cohérence dimensionnelle et les identités de compte reposent notamment sur les égalités suivantes :

| Étape | Relation attendue |
|---|---|
| Parts de biome | $\sum_b s_{ib}=1$ |
| Aire forestière corrigée | $\sum_{i,b}A_{ib}=\sum_i(F_i-O_i^F)$ |
| Addition forestière | $\sum_iU_i=(44/12)\sum_{i,b}A_{ib}\bar r_b$ |
| Surface de mangrove documentée | $O_i^F+O_i^{OWL}+O_i^R+O_i^?=M_i^{FRA}$ |
| Compte NCW | $N_{i,d}=GCW_{i,d}+BCW_{i,d}$ sur les composantes disponibles |
| Valorisation GCW | $GCW_{i,d}=U_i\,GSCC_d$ |

Ces identités vérifient la cohérence dimensionnelle et la fermeture des comptes. Elles ne tranchent pas les choix scientifiques, notamment le classement des mangroves non ventilées ou l’interprétation des paramètres publiés par une autre étude.

Le calcul suit donc cette chaîne : données raster Gibbs/GFW et masque forestier → taux annuels par biome → surfaces forestières FRA corrigées et ventilées → flux physiques et valorisation du GCW; en parallèle, aire de mangrove retenue selon la hiérarchie GMW 2025/FRA 2025/aire rapportée par Hilmi et al. (2026) → calcul direct du flux bleu total avec les aires côtières, leurs taux et le BCP → valorisation BCW; enfin, addition de GCW et BCW → NCW, puis comparaisons de déforestation, d'émissions, de PIB et scénarios de financement. Les tableaux et figures résument ces étapes et leurs périmètres.

Sources primaires : [article méthodologique Gibbs et al. (2025)](https://essd.copernicus.org/articles/17/1217/2025/), [définition FRA de la déforestation](https://fra-data.fao.org/definitions/fra/2020/en/tad), [zones écologiques mondiales FAO 2010](https://www.fao.org/4/ap861e/ap861e00.pdf), [union terre-EEZ de Marine Regions](https://www.marineregions.org/downloads.php), [lignes directrices GIEC 2006, chapitre 4](https://www.ipcc-nggip.iges.or.jp/public/2006gl//pdf/4_Volume4/V4_04_Ch4_Forest_Land.pdf), [estimation FAO des flux forestiers nets (Tubiello et al., 2026)](https://essd.copernicus.org/articles/18/6799/2026/), [jeu Gibbs/GFW](https://doi.org/10.7910/DVN/V2ISRH), [jeu GMW](https://zenodo.org/records/21346457), [CPI-U annuel du BLS](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm), [article Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1) et [données d’entrée par cellule et programme Stata Busch](https://zenodo.org/records/19239386).

