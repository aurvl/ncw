# Audit des données — versions, statut et millésimes les plus récents

> Objet : pour chaque source du pipeline, dire ce qu'on utilise, si la valeur est **observée, estimée ou projetée**, et quelle est la donnée effective la plus récente disponible aujourd'hui.
> Date de l'audit : 2026-09-20. Sources vérifiées en ligne le même jour.
> Registre des téléchargements : `data_source/metadata/source_registry.csv`.

## Verdict en une phrase

**2023 est la dernière année où les quatre variables socio-économiques (émissions, population, PIB, dette) sont toutes observées ou estimées, et non projetées.** La convention de BCW est donc déjà le meilleur choix disponible ; il n'y a rien à gagner à passer à 2024 ou 2025.

---

## 1. Données physiques

| Source | Version utilisée | Ce qu'on en tire | Statut des valeurs | Plus récent disponible | Recommandation |
|---|---|---|---|---|---|
| **FAO FRA 2025** | bulk WO, accès 2026-09-16 | Surfaces forestières, mangroves, années 1990→2025 | Années de référence déclarées par les pays ; **194 unités sur 236 en donnée officielle (`A`), 42 en donnée imputée par la FAO (`I`)** ; ce ne sont pas des projections | FRA 2025 est le dernier cycle ; le suivant est FRA 2030 | Garder. Robustesse déjà prévue avec les surfaces 2020, plus proches de la décennie de Pan |
| **FRA 2025, `1d_deforestation`** | idem | Surfaces déboisées par intervalle | **Renseigné pour 139 unités sur 236 seulement**, soit 79 % du GCW mondial | idem | ⚠ Annoncer la couverture ; ne jamais lire une absence comme un zéro (Pérou, Bolivie, Myanmar, États-Unis sont absents) |
| **Pan et al. (2024)** | version of record, Table 1 et Extended Data 1 et 3 | Taux de séquestration par biome, moyennes 2010–2019 | Publié, final | 2010–2019 est la dernière décennie publiée | Garder. Une mise à jour supposerait une nouvelle publication |
| **FAOSTAT, *Emissions from forests*** | bulk 2026-07-06 | Route A, flux net de la forêt restante | **Toutes les valeurs, toutes années confondues, portent le drapeau `E` = estimation FAO Tier 1** ; aucune n'est une déclaration nationale dans ce domaine. Les valeurs 2025 dérivent du cycle FRA 2025 | années 1990→2025 | Garder la fenêtre 2015–2024 (C4) ; ne pas présenter la Route A comme « déclaré par les pays » |
| **FAO GEZ 2010** | 2ᵉ édition | Parts de biome | Carte statique | Pas d'édition plus récente | Garder |
| **JRC GFC2020 V4** | aperçu ×256 (~2,3 km) | Masque forêt pour les parts de biome | Carte 2020 | V4 est la dernière version | Garder. Hansen GFC est annuel mais sa définition de forêt diffère |
| **EEZ land union v4 (2024-10)** | repris du dépôt BCW | Frontières des unités | Version de référence de BCW | Marine Regions publie des mises à jour | Garder, pour rester aligné sur BCW |

## 2. Données socio-économiques (toutes héritées de la table BCW)

| Variable | Source BCW | Année | Statut | Millésime effectif le plus récent (2026-09-20) | Faut-il changer ? |
|---|---|---|---|---|---|
| **Émissions de CO₂** | Global Carbon Budget 2024 via Our World in Data ; fossile et industrie, **hors usage des terres** | 2023 | Estimation à partir des statistiques énergétiques | **GCB 2025** (ESSD, 2026) : 2024 observé ; **2025 est une projection** (38,1 GtCO₂ annoncés) | Possible de passer à 2024, mais seulement si tout le bloc suit |
| **Population** | UN WPP, révision 2024 | 2023 | Estimation (les années ≥ 2024 sont des **projections**) | La révision 2024 reste la dernière ; **aucune révision 2026 publiée** | **Non. 2023 est déjà la dernière année estimée** |
| **PIB** | Banque mondiale, dollars constants de 2015 | 2023, ou l'année antérieure la plus proche | Observé, révisable | WDI mis à jour le 2026-07-27, séries jusqu'à 2025, avec des années récentes incomplètes selon les pays | Facultatif |
| **Dette extérieure totale** | Banque mondiale, *External Debt Stocks, Total (DOD)* | 2023 | Déclaré par les emprunteurs | IDS mis à jour le 2026-07-31 : **fin 2024** | Facultatif |

### Pourquoi rester en 2023

Passer les émissions à 2024 obligerait à porter aussi la population à 2024, or la révision WPP 2024 ne fournit pour 2024 qu'une **projection**. On échangerait donc une estimation cohérente contre un mélange d'observations et de projections, tout en s'écartant des chiffres publiés de BCW, qui servent de référence d'harmonisation (C12).

Le décalage qui compte n'est de toute façon pas là : le flux forestier porte sur **2010–2019** et les surfaces sur **2025**. Changer l'année des émissions ne le corrige pas.

### Si le choix d'actualiser est fait malgré tout

Il faut alors tout bouger ensemble, à 2024 :

1. émissions : Global Carbon Budget 2025, valeurs 2024 ;
2. dette : IDS, encours fin 2024 ;
3. PIB : WDI, 2024 en dollars constants de 2015 ;
4. population : impossible en valeur estimée, la valeur 2024 de WPP 2024 est une projection — à assumer explicitement ;
5. recalculer tous les ratios et signaler l'écart avec les chiffres publiés de BCW.

## 3. Points d'attention ouverts

| Point | Détail | Piste |
|---|---|---|
| Couverture de la déforestation | 139 unités sur 236, 79 % du GCW mondial ; absents : USA, Pérou, Bolivie, Zambie, Myanmar, Afrique du Sud, Japon, Thaïlande, Malaisie, Nigéria | a) restreindre l'analyse aux déclarants en annonçant la couverture ; b) approximer par la perte nette de surface forestière FRA, qui sous-estime, car l'expansion compense ; c) source externe de perte de couvert, avec une définition différente |
| Colonne `Area` de FAOSTAT `Net Forest conversion` | Incohérente : Maroc à 3 270 puis 4 kha, Australie au-dessus du Brésil, ligne World différente de la somme des pays | Écartée, ne pas utiliser |
| Seuil de tension de dette | Valeur de la Fig. 5c de BCW non documentée dans l'article | À demander aux coauteurs |
| Prix carbone AR6 | Pas encore récupérés ; le notebook tourne avec des valeurs placeholder | Base de scénarios AR6 (C24) |

## Sources vérifiées en ligne

- [Global Carbon Budget — dernières données 2025](https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/)
- [Global Carbon Budget 2025, ESSD](https://essd.copernicus.org/articles/18/3211/2026/)
- [UN World Population Prospects 2024](https://population.un.org/wpp/)
- [World Bank, GDP (constant 2015 US$)](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD)
- [World Bank, International Debt Statistics](https://www.worldbank.org/en/programs/debt-statistics/ids)
