# Test spatial GMW–JRC : chevauchement mangrove–forêt

Date du test : 23 octobre 2026.

## Objectif

Tester, uniquement en analyse de sensibilité, si une carte forestière spatiale peut aider à estimer la part des mangroves FRA dont la classification Forest/OWL reste inconnue.

## Données et méthode

- mangroves : polygones GMW 2025 v4.1.12 ;
- forêt : masque JRC GFC2020, version overview x256 ;
- calcul : surface des polygones GMW dont le point représentatif tombe dans un pixel JRC classé forêt ;
- surfaces calculées en projection équivalente, puis comparées aux surfaces GMW corrigées déjà utilisées dans le pipeline.

Ce calcul est un proxy spatial grossier. Il ne reproduit pas la classification nationale FRA Forest/OWL et ne doit donc pas remplacer les déclarations nationales.

## Résultats

- 116 unités mangrove ont été testées ;
- 90 unités ont une classification FRA Forest/OWL non résolue dans l’audit ;
- pour ces unités, le proxy spatial donne **7 469 202 ha** de mangrove située dans un pixel JRC forestier ;
- ce chiffre représente **64,3 %** des 11 613 440 ha FRA non résolus, mais ce ratio ne constitue pas une mesure officielle de la part forestière ;
- rapporté à toute la surface GMW corrigée utilisée dans le pipeline, le proxy forestier représente **68,2 %** ;
- trois unités non résolues n’ont pas de proxy GMW exploitable : BES, MSR et SHN.

## Contrôle sur les unités déjà documentées

Le proxy spatial ne reproduit pas les classifications FRA connues : sur les unités documentées, il donne une fraction forestière pondérée d’environ **67,0 %**, alors que plusieurs déclarations nationales indiquent 100 % Forest. Par exemple, le proxy donne environ 41 % pour le Kenya, 6,5 % pour le Sri Lanka et 15 % pour les Philippines.

Cela montre que la carte JRC et la classification FRA ne mesurent pas exactement la même chose. Les causes probables sont la résolution grossière de la couche JRC, la méthode par point représentatif, les différences de définition et les différences entre les surfaces GMW et FRA.

## Interprétation pour le papier

Le résultat spatial est utile comme **analyse de sensibilité** et comme indication des pays où une part forestière est plausible. Il ne justifie pas de modifier le résultat principal ni de retirer automatiquement 7,47 Mha de la forêt FRA.

La règle recommandée reste donc :

1. résultat principal : classification FRA documentée ;
2. cas non résolus : conserver l’incertitude ;
3. analyse de sensibilité : utiliser le chevauchement GMW–JRC comme scénario spatial, clairement présenté comme proxy.

Si l’on transformait artificiellement les 7,47 Mha en surface forestière tropicale et qu’on appliquait le taux tropical du modèle, cela produirait environ **25,6 MtCO₂/an**, soit **14,3 milliards US$2015/an** au GSCC utilisé. Ce chiffre est uniquement un stress test et ne doit pas entrer dans le résultat principal.
