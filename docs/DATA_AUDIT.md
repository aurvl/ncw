# Audit des données - versions, statut et millésimes les plus récents

> Objet : pour chaque source du pipeline, dire ce qu'on utilise, si la valeur est **observée, estimée ou projetée**, et quelle est la donnée effective la plus récente disponible aujourd'hui.
> Date de l'audit : actualisé le 2026-10-20. Sources vérifiées en ligne le 2026-10-20.
> Registre des téléchargements : `data/metadata/source_registry.csv`.

## Verdict en une phrase

**Une extension d'analyse 2024 est maintenant construite séparément des résultats et artefacts encore au millésime 2023.** Elle associe les émissions territoriales de CO₂ fossile et industriel du GCB 2025 aux estimations WDI 2024 de population et de PIB réel. Sur les 236 unités du compte, 210 ont une ligne d'émissions GCB directement appariée, 213 une population WDI 2024, 196 un PIB WDI 2024, et 193 les trois variables. La dette externe 2024 est disponible dans IDS pour les pays couverts, mais elle n'entre pas dans cette analyse. « Aligné sur 2024 » désigne donc l'année de référence commune, pas une observation directe homogène ni une couverture exhaustive.

---

## 1. Données physiques

| Source | Version utilisée | Ce qu'on en tire | Statut des valeurs | Plus récent disponible | Recommandation |
|---|---|---|---|---|---|
| **FAO FRA 2025** | bulk WO, accès 2026-09-16 | Surfaces forestières, mangroves, années 1990→2025 | Années de référence déclarées par les pays ; **194 unités sur 236 en donnée officielle (`A`), 42 en donnée imputée par la FAO (`I`)** ; ce ne sont pas des projections | FRA 2025 est le dernier cycle ; le suivant est FRA 2030 | Garder. Robustesse déjà prévue avec les surfaces 2020, plus proches de la décennie de Pan |
| **FRA 2025, `1d_deforestation`** | idem | Surfaces déboisées par intervalle | **Renseigné pour 139 unités sur 236 seulement**, soit 79 % du GCW mondial | idem | ⚠ Annoncer la couverture ; ne jamais lire une absence comme un zéro (Pérou, Bolivie, Myanmar, États-Unis sont absents) |
| **Gibbs et al. (2025) / GFW** | Dataset publié avec l'article, version 2001-2023 | Retraits bruts cumulés de CO2 par hectare dans la biomasse aérienne et souterraine vivante ; base des quatre taux GEZ | Modélisé, publié ; 272 tuiles vérifiées par MD5 et agrégées ; tableaux dérivés conservés localement, tuiles volumineuses non conservées | Version 2025 présentée dans l'article | L'article rapporte ±1 écart-type pour les totaux globaux et par domaine climatique, pas pour les quatre taux GEZ par hectare ; moyenne 2001-2023 appliquée à FRA 2025 |
| **Global Mangrove Watch v4.1.12** | Carte annuelle complète 1985-2025, publiée le 2026-08-03; polygones 2025 et classeur des aires nationales corrigées | Remplacer uniquement l'aire des mangroves dans BCW; intersection du vecteur avec les mêmes frontières EEZ/terre, puis correction d'aire GMW publiée de 0,9775 par code source | Carte télédétectée et estimation d'aire corrigée; contrôle global fondé sur 32 569 points/120 sites, F1 global 0,9276 (IC 95% 0,9220-0,9330); précision variable localement | Dernière carte mondiale annuelle complète disponible à la date de vérification; les alertes de perte ne sont pas une nouvelle carte d'aire annuelle complète | Garder l'aire corrigée, l'allocation spatiale et le résidu non attribué séparés; ne pas traiter le facteur global comme une incertitude nationale indépendante |
| **Pan et al. (2024)** | version of record, Table 1 et Extended Data 1 et 3 | Comparaison méthodologique secondaire avec la méthode précédente | Publié, final | 2010-2019 est la dernière décennie couverte par ces tableaux | Hors du pipeline principal Gibbs/GFW |
| **FAOSTAT, *Emissions from forests*** | bulk 2026-07-06 | Route A, flux net de la forêt restante | **Toutes les valeurs, toutes années confondues, portent le drapeau `E` = estimation FAO Tier 1** ; aucune n'est une déclaration nationale dans ce domaine. Les valeurs 2025 dérivent du cycle FRA 2025 | années 1990→2025 | Garder la fenêtre 2015-2024 (C4) ; ne pas présenter la Route A comme « déclaré par les pays » |
| **FAO GEZ 2010** | 2ᵉ édition | Parts de biome | Carte statique | Pas d'édition plus récente | Garder |
| **JRC GFC2020 V4** | aperçu ×256 (~2,3 km) | Masque forêt pour les parts de biome | Carte 2020 | V4 est la dernière version | Garder. Hansen GFC est annuel mais sa définition de forêt diffère |
| **EEZ land union v4 (2024-10)** | repris du dépôt BCW | Frontières des unités | Version de référence de BCW | Marine Regions publie des mises à jour | Garder, pour rester aligné sur BCW |

## 2. Données socio-économiques: référence 2023 existante et extension analytique 2024

| Variable | Source BCW | Année | Statut | Millésime effectif le plus récent (vérifié le 2026-10-20) | Faut-il changer ? |
|---|---|---|---|---|---|
| **Émissions de CO₂** | Référence 2023: table BCW. Extension: GCB 2025, *National Fossil Carbon Emissions*, onglet territorial; combustibles fossiles et ciment, hors changement d'usage des terres | Référence 2023; extension 2024 | Estimation nationale du GCB; unité source MtC/an convertie selon le facteur 3,664 indiqué dans le classeur | GCB 2025 est l'édition la plus récente vérifiée le 2026-10-20 et fournit les séries nationales jusqu'en 2024 | 210/236 unités ont une ligne directement appariée. Les unités sans ligne restent manquantes; aucune émission nationale n'est recopiée sur un territoire séparé |
| **Population** | Référence 2023: table BCW. Extension: Banque mondiale WDI, `SP.POP.TOTL` | Référence 2023; extension 2024 | Estimation de population en milieu d'année; WDI cite WPP, offices statistiques nationaux et Eurostat. Dans WPP 2024, la période de projection commence en 2024 | Extraction WDI mise à jour le 2026-10-08 | 213/236 unités ont une valeur WDI 2024 directement appariée; les absences ne sont pas imputées |
| **PIB** | Référence 2023: table BCW. Extension: Banque mondiale WDI, `NY.GDP.MKTP.KD`, dollars US constants de 2015 | Référence 2023; extension 2024 | Comptes nationaux, statistiques officielles et estimations de la Banque mondiale; série révisable | Extraction WDI mise à jour le 2026-10-08; valeurs 2024 disponibles pour une partie des unités | 196/236 unités ont une valeur WDI 2024 directement appariée |
| **Dette extérieure totale** | Banque mondiale, IDS, *External Debt Stocks, Total (DOD)* | Référence 2023; 2024 disponible | Déclarée ou estimée dans le cadre IDS pour les économies couvertes | IDS présente des observations 2024 | Vérifiée comme disponible, mais exclue des analyses spatiales demandées |

### Statut de l'alignement 2024

L'année 2024 existe pour les trois variables retenues, mais les valeurs n'ont pas toutes le même statut. Le GCB fournit une estimation récente des émissions nationales; le WDI décrit sa population comme des estimations de milieu d'année provenant de plusieurs producteurs; et le PIB est une série annuelle de comptes nationaux/estimations révisable. Le WPP 2024 distingue explicitement les estimations 1950-2023 des projections 2024-2100. On présente donc le bloc comme des données socio-économiques référées à 2024, et non comme quatre observations directes parfaitement harmonisées.

Le décalage temporel demeure : le flux forestier Gibbs/GFW porte sur **2001-2023** et les surfaces sur **2025**. La mise à jour des variables nationales à 2024 ne transforme pas ces mesures écologiques en mesures contemporaines de 2024.

### Règles d'extraction et portée

Pour l'extension spatiale, le PIB par habitant est calculé comme PIB WDI 2024 / population WDI 2024; `GCW/GDP` utilise le PIB WDI 2024 en dollars constants de 2015. Les modèles emploient seulement les unités complètes pour les variables requises. Les sorties centrales antérieures fondées sur les valeurs BCW 2023 sont conservées pour comparaison et ne sont pas silencieusement écrasées. La dette n'est pas requise.

Un contrôle de millésime compare les émissions 2023 du GCB 2025 à la série 2023 embarquée dans la table BCW: 210 unités appariées, corrélation de Pearson `0,999875`, différence absolue médiane `4,87 %`. Cette comparaison documente la révision de la série et le crosswalk; elle ne remplace pas l'analyse 2024.

Les extractions, crosswalks et résultats se trouvent dans `data/raw/economic/socioeconomics_2024/`, `data/derived/socioeconomic_2024_by_unit.csv` et les fichiers `results/validation/spatial_emissions_2024_*.csv`.

## 3. Points d'attention ouverts

| Point | Détail | Piste |
|---|---|---|
| Couverture de la déforestation | 139 unités sur 236, 79 % du GCW mondial ; absents : USA, Pérou, Bolivie, Zambie, Myanmar, Afrique du Sud, Japon, Thaïlande, Malaisie, Nigéria | a) restreindre l'analyse aux déclarants en annonçant la couverture ; b) approximer par la perte nette de surface forestière FRA, qui sous-estime, car l'expansion compense ; c) source externe de perte de couvert, avec une définition différente |
| Colonne `Area` de FAOSTAT `Net Forest conversion` | Incohérente : Maroc à 3 270 puis 4 kha, Australie au-dessus du Brésil, ligne World différente de la somme des pays | Écartée, ne pas utiliser |
| Seuil de tension de dette | Valeur de la Fig. 5c de BCW non documentée dans l'article | À demander aux coauteurs |
| Prix carbone AR6 | Pas encore récupérés ; le notebook tourne avec des valeurs placeholder | Base de scénarios AR6 (C24) |

## Sources vérifiées en ligne

- [Global Carbon Budget - dernières données 2025](https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/)
- [Global Carbon Budget 2025, ESSD](https://essd.copernicus.org/articles/18/3211/2026/)
- [UN World Population Prospects 2024](https://population.un.org/wpp/)
- [UN WPP 2024: estimates 1950-2023 and projections 2024-2100](https://data.un.org/Data.aspx?d=PopDiv&f=variableID%3A12%3BcrID%3A484)
- [World Bank WDI, population total](https://data.worldbank.org/indicator/SP.POP.TOTL)
- [World Bank, GDP (constant 2015 US$)](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD)
- [World Bank, International Debt Statistics](https://www.worldbank.org/en/programs/debt-statistics/ids)
