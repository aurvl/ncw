# Climate-finance complete results inventory

**Status (23 October 2026):** regenerated after the mangrove-area and forest-capacity refresh. The GCW allocation is a stipulated scenario; the Busch correction is an independently derived reconstruction, pending clarification with the source authors. Monetary amounts below are real US$2015 per year unless a 30-year present value in US$2020 is explicitly named. Accounting units may be countries or territories.

## 1. Research questions and analytical scope

1. How is a hypothetical annual allocation equal to 2% of estimated GCW distributed across 236 forest-account units? 2. Among the 105 units with positive reported annual forest-capacity loss, which have published Busch country curves and enough reconstructed 30-year mitigation supply for an equal-tonnage scenario? 3. For the matched units, how do annual-equivalent modeled resource costs and theoretical uniform carbon payments compare with the stipulated allocation? None of these comparisons identifies an actual funding need, an observed transfer, or ecological equivalence.

## 2. Data sources, samples, definitions, and methodology

| Object | Population | Definition | Unit | Status |
|---|---|---|---|---|
| GCW allocation | 236 | GCW from `results/country_level_gcw.csv`; allocation `0.02 × GCW_mean` | US$2015 yr⁻¹ | stipulated / modeled valuation |
| Positive capacity loss | 105 of 139 deforestation reporters | `lost_capacity_tco2_yr > 0`; area loss × four biome rates | tCO₂ yr⁻¹ | modeled from reported forest loss |
| Busch source country curves | 138 source curves (115 Core, 23 Other); 71 match positive-loss units | 25 grid prices from −20 to 100, step 5 | source workbook labels quantities tCO₂; audit finds tC-like numerics | published / audited |
| Derived cost comparison | 59 target-within-supply units | Cell outputs; tC→tCO₂ ×3.67; natural soil term counted once | 30-year discounted tCO₂, US$2020 PV | derived / provisional |

Source horizon: `Q_i = L_i × D`, `D = Σ(t=0,…,29) 0.95^t = 15.707224721`. This treats each observed annual capacity loss as persisting for 30 years and follows the source program's factor. The conventional years-1–30 5% factor is 15.372451027; it is a separate sensitivity, not silently substituted. In the 236-row CSV, `lost_capacity_discounted_30yr_tco2` is the older conventional-horizon column, whereas `scenario_target_30yr_tco2_all_positive_loss` uses the source factor for this inventory. Positive-loss units lacking a Busch curve have a scenario `Q_i` in the new country inventory but no source modeled supply/cost. The other 131 of 236 units fall outside the positive-loss sample; their blank Busch fields do not mean a zero mitigation price.

Corrected cell quantity is in tCO₂ after ×3.67; natural regeneration uses `aboveground + belowground + soil/2` instead of the source output's `aboveground + belowground + soil`. Plantation carbon is unchanged. Method choice is recalculated with the source rule. Eligible cell net 30-year project cost divided by corrected screened/buffered/additional tCO₂ is the derived effective marginal price. The supply curve ranks cells by this price; a fraction of the final cell reaches `Q_i`. Net economic cost is the signed cost sum; positive project cost sums only positive cell costs; theoretical uniform payment is `max(0, marginal price at Q_i) × Q_i`. The annual-equivalent comparison applies CPI `237.017/258.811 = 0.915791833` and divides the 30-year US$2020 PV by `D`.

**Scope distinction.** The current `finance_figure4_summary.json` is the published workbook-grid comparison and remains separate from this cell-level reconstruction. The regenerated `gcw_valuation_fraction_sensitivity_world.csv` 100% row is US$8,261.443009 billion/year and matches current Table 1 GCW of US$8,261.443009 billion/year. The 2% allocation interval is US$64.530–299.984 billion/year when only existing GCW draw uncertainty is propagated.

## 3. Exhaustive allocation results

| Measure | Exact result | Unit | Formula / denominator |
|---|---|---|---|
| GCW mean | 8,261.443009 | billion US$2015/yr | Table 1, Green carbon wealth |
| 2% allocation mean / national sum | 165.228860 | billion US$2015/yr | 0.02 × current GCW; n=236 |
| Allocation P05 | 64.530120 | billion US$2015/yr | 0.02 × global GCW draw P05 |
| Allocation P50 | 149.623171 | billion US$2015/yr | 0.02 × global GCW draw P50 |
| Allocation P95 | 299.983976 | billion US$2015/yr | 0.02 × global GCW draw P95 |
| Zero allocated value | 8 | units | observed zeros in modeled GCW table; no imputation |
| Unclassified GCW units | 0 | units | all 236 have a project group |
| Gini | 0.865217 | 0–1 | equal to GCW Gini by positive scaling |
| HHI | 0.061119 | 0–1 | sum of squared national allocation shares |

The P05–P95 interval conditions on fixed forest inputs and varying monetary draws. It is neither a confidence interval for the 2% policy rule nor full ecological uncertainty. National P05 and P95 values in the attached 236-row CSV are `0.02 ×` each unit's GCW P05/P95; these are **not additive** into the global draw P05/P95.

### Concentration and distribution

| Top N | Annual allocation (billion US$2015) | Share of 236-unit total (%) | Denominator |
|---|---|---|---|
| 1 | 23.909446 | 14.4705 | 236 ranked units |
| 5 | 83.455604 | 50.5091 | 236 ranked units |
| 10 | 105.839121 | 64.0561 | 236 ranked units |
| 20 | 125.448816 | 75.9243 | 236 ranked units |
| 25 | 131.512598 | 79.5942 | 236 ranked units |
| 50 | 149.747485 | 90.6303 | 236 ranked units |
| 100 | 162.239770 | 98.1909 | 236 ranked units |
| 118 | 163.897205 | 99.1941 | 236 ranked units |
| 200 | 165.226333 | 99.9985 | 236 ranked units |
| 236 | 165.228860 | 100.0000 | 236 ranked units |

The bottom 118 units receive 0.8059% of the total. Top-N shares and the Gini are mechanically identical for GCW and a uniform 2% allocation.

The legacy source table also contains a **separate** illustrative US$100 billion per year pledge allocated in proportion to national GCW for 30 years: total 3.000000 trillion US$ cumulative, top 10 1.921682 trillion (64.0561% of 236-unit total). Formula: `national_GCW / global_GCW × 100 billion × 30`. This is an undiscounted policy thought experiment whose currency price year is unspecified in the source script; it is neither the 2% GCW allocation nor a cost estimate and is **not** pooled with US$2015 results. Full national values remain in the 236-row CSV.

| Series / n | Unit | Min | P05 | P25 | P50 | P75 | P95 | Max | Zeros |
|---|---|---|---|---|---|---|---|---|---|
| Allocation, 236 units | million US$2015/yr | 0.0000 | 0.0103 | 1.2349 | 66.5640 | 343.3697 | 2,316.2549 | 23,909.4463 | 8 |
| GCW, 236 units | billion US$2015/yr | 0.0000 | 0.0005 | 0.0617 | 3.3282 | 17.1685 | 115.8127 | 1,195.4723 | 8 |

**Ranked national allocations (top 25).** Full rankings, including zero-valued units, are in the 236-row CSV.

| Rank | Unit | Name | Group | Allocation (billion US$2015/yr) | Cumulative share (%) |
|---|---|---|---|---|---|
| 1 | RUS | Russian Federation | Developed economies | 23.909446 | 14.4705 |
| 2 | BRA | Brazil | Developing economies | 18.767497 | 25.8290 |
| 3 | USA | United States of America | Developed economies | 16.388648 | 35.7477 |
| 4 | CHN | China (incl. Taiwan, Hong Kong SAR and Macao SAR) | Developing economies | 12.202669 | 43.1331 |
| 5 | CAN | Canada | Developed economies | 12.187345 | 50.5091 |
| 6 | AUS | Australia | Developed economies | 7.267759 | 54.9077 |
| 7 | COD | Democratic Republic of the Congo | LDCs | 5.336977 | 58.1377 |
| 8 | IDN | Indonesia | Developing economies | 3.679786 | 60.3648 |
| 9 | IND | India | Developing economies | 3.050323 | 62.2110 |
| 10 | MEX | Mexico | Developing economies | 3.048671 | 64.0561 |
| 11 | PER | Peru | Developing economies | 2.575132 | 65.6146 |
| 12 | AGO | Angola | LDCs | 2.425691 | 67.0827 |
| 13 | COL | Colombia | Developing economies | 2.279776 | 68.4624 |
| 14 | BOL | Bolivia (Plurinational State of) | Developing economies | 2.084739 | 69.7242 |
| 15 | ARG | Argentina | Developing economies | 2.019283 | 70.9463 |
| 16 | VEN | Venezuela (Bolivarian Republic of) | Developing economies | 1.805522 | 72.0390 |
| 17 | CAF | Central African Republic | LDCs | 1.729089 | 73.0855 |
| 18 | ZMB | Zambia | LDCs | 1.720631 | 74.1269 |
| 19 | TZA | United Republic of Tanzania | LDCs | 1.658040 | 75.1304 |
| 20 | JPN | Japan | Developed economies | 1.311791 | 75.9243 |
| 21 | PNG | Papua New Guinea | SIDS | 1.293820 | 76.7073 |
| 22 | TUR | Türkiye | Developing economies | 1.289458 | 77.4877 |
| 23 | MOZ | Mozambique | LDCs | 1.225264 | 78.2293 |
| 24 | ZAF | South Africa | Developing economies | 1.164140 | 78.9338 |
| 25 | ESP | Spain | Developed economies | 1.091100 | 79.5942 |

**Observed zero allocations:** FLK (Falkland Islands (Malvinas)), GIB (Gibraltar), KIR (Kiribati), MCO (Monaco), NRU (Naoero), SJM (Svalbard and Jan Mayen Islands), TKL (Tokelau), VAT (Holy See). Zero here means the input GCW estimate is zero, not a filled missing value.

### Economic-group allocation and loss composition

| Exclusive project group | n | Total (billion) | World share (%) | Median (million) | P25 | P75 | Within-group Gini | Zeros |
|---|---|---|---|---|---|---|---|---|
| Developed economies | 62 | 72.239007 | 43.7206 | 113.7246 | 1.9101 | 397.8624 | 0.8843 | 4 |
| Developing economies | 80 | 68.601312 | 41.5190 | 156.3140 | 16.9669 | 603.8059 | 0.8081 | 2 |
| LDCs | 37 | 21.089087 | 12.7636 | 185.1889 | 54.3000 | 499.8457 | 0.6993 | 0 |
| SIDS | 57 | 3.299455 | 1.9969 | 1.2592 | 0.3823 | 14.2676 | 0.9014 | 2 |

The four project groups are mutually exclusive accounting categories (62 + 80 + 37 + 57 = 236), not independent overlapping UN LDC and SIDS flags. There are zero unclassified **GCW** units after the current territorial fallback, although other marine-only or special units can remain unclassified outside this 236-unit population. Each group allocation statistic is exactly 2% of its GCW counterpart.

## 4. Exhaustive reconstructed reforestation results

| Disjoint status except subtotal rows | Units | Loss (tCO₂/yr) | % of 105-unit loss | 30y target (MtCO₂) | 2% allocation (billion/yr) |
|---|---|---|---|---|---|
| Within supply, non-positive marginal | 44 | 26,040,564.142 | 73.8401 | 409.024993 | 66.222384 |
| Within supply, positive marginal | 15 | 2,978,770.630 | 8.4465 | 46.788220 | 5.383347 |
| Within supply, all | 59 | 29,019,334.772 | 82.2867 | 455.813213 | 71.605731 |
| Insufficient modeled supply | 12 | 3,119,278.992 | 8.8450 | 48.995216 | 2.947917 |
| No published country curve | 34 | 3,127,521.043 | 8.8683 | 49.124676 | 28.687323 |
| All positive-loss reporters | 105 | 35,266,134.807 | 100.0000 | 553.933104 | 103.240971 |

Of the 12 insufficient units, 7 have exactly zero reconstructed supply and 5 have positive but inadequate supply. Of 71 matched source curves, 60 are on `Core results` and 11 on `Other results`; across the full workbook there are 115 and 23, respectively. Seven published zero curves are reproduced exactly.

### Source-curve reproduction and correction stages

| Stage / diagnostic | Value | Meaning / denominator |
|---|---|---|
| Curve validation | 71/71 | Max source-supply-normalized difference 0.437939% of each curve maximum |
| Original grid ceiling −20 to 100 | 25 | US$2020/tCO₂ points, increment 5; source numeric quantity labels are disputed |
| Published numeric, Core only at 100 | 46 | Historical source-number comparison with target |
| Published numeric, Core + Other at 100 | 53 | Adds 11 sample countries with curves from Other |
| ×3.67 carbon conversion at 100 | 59 | Source tC-like numbers converted to tCO₂ |
| ×3.67 and soil counted once at 100 | 59 | Corrected 25-price supply |
| US$50: converted without soil adjustment | 93.769645 | GtCO₂ discounted, 71 countries |
| US$50: conversion + soil adjustment | 88.341544 | GtCO₂ discounted, 71 countries; delta -5.7888% |
| US$100: conversion + soil adjustment | 98.044936 | GtCO₂ discounted, 71 countries, not annual or global |
| Output cells inspected | 46,039,862 | Rows across 71 national source DTAs |
| Eligible priced cells | 4,805,330 | Corrected finance-curve cells (nonzero supply only) |
| Cells switching selected method | 97,440 | Count after soil correction; source algorithm reapplied |

The source workbook is preserved. The `×3.67` and soil-once series are **derived interpretations** of publicly available cell outputs and code, not corrected values endorsed or published by Busch et al. A repeated soil addition in code is an observed code-path issue; its effect is estimated here but remains subject to author clarification. At US$50, the 71 matched workbook curves sum to 25.563917 billion in their labelled quantity, whereas the converted and soil-adjusted reconstruction sums to 88.341544 billion tCO₂. The workbook's 138-country total is 31.400000 billion, matching the 31.4 GtCO₂ that [Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1) report below US$50. Since our adjusted **71-country subset** exceeds that published global result, the carbon-unit interpretation is scientifically unresolved. Do not combine the adjusted volumes with published totals or describe them as Busch's published findings until this discrepancy is resolved with the authors.

**Full 25-price audit for the 71 matched country curves.** All volume columns below are billions of workbook-labelled units or derived tCO₂ over the source 30-year discounted horizon. The workbook column retains its published numeric value without endorsing its physical unit. The companion CSV retains unrounded values and the soil-correction percentage.

| Price (US$2020/tCO₂) | Workbook 138-country total (bn) | Matched 71 numeric (bn) | Reproduced 71 numeric (bn) | ×3.67 (GtCO₂) | ×3.67 and soil once (GtCO₂) | Soil change (%) | Nonzero curves / 71 |
|---|---|---|---|---|---|---|---|
| -20 | 2.50000 | 2.26186 | 2.26500 | 8.31256 | 8.31256 | -0.000 | 39 |
| -15 | 4.66000 | 4.03207 | 4.03176 | 14.79658 | 14.79658 | 0.000 | 46 |
| -10 | 7.25000 | 6.06179 | 6.06411 | 22.25527 | 22.25527 | 0.000 | 49 |
| -5 | 10.30000 | 8.47704 | 8.47775 | 31.11333 | 31.11333 | 0.000 | 50 |
| 0 | 13.00000 | 10.57307 | 10.57433 | 38.80779 | 38.80779 | 0.000 | 52 |
| 5 | 16.50000 | 13.22465 | 13.22044 | 48.51903 | 47.68237 | -1.724 | 57 |
| 10 | 19.30000 | 15.33792 | 15.33648 | 56.28488 | 54.64132 | -2.920 | 60 |
| 15 | 21.90000 | 17.41074 | 17.41131 | 63.89952 | 61.25878 | -4.133 | 62 |
| 20 | 24.20000 | 19.32116 | 19.32344 | 70.91701 | 67.39562 | -4.966 | 63 |
| 25 | 26.20000 | 20.94991 | 20.95266 | 76.89625 | 72.68255 | -5.480 | 63 |
| 30 | 27.70000 | 22.25502 | 22.25073 | 81.66019 | 77.05440 | -5.640 | 64 |
| 35 | 29.00000 | 23.33407 | 23.33550 | 85.64127 | 80.70184 | -5.768 | 64 |
| 40 | 30.00000 | 24.23017 | 24.22462 | 88.90434 | 83.70437 | -5.849 | 64 |
| 45 | 30.80000 | 24.90848 | 24.94718 | 91.55617 | 86.24491 | -5.801 | 64 |
| 50 | 31.40000 | 25.56392 | 25.55031 | 93.76965 | 88.34154 | -5.789 | 64 |
| 55 | 32.00000 | 26.06076 | 26.05576 | 95.62465 | 90.11709 | -5.760 | 64 |
| 60 | 32.50000 | 26.44518 | 26.47182 | 97.15156 | 91.64297 | -5.670 | 64 |
| 65 | 32.80000 | 26.77516 | 26.81975 | 98.42848 | 92.91686 | -5.600 | 64 |
| 70 | 33.20000 | 27.17039 | 27.11940 | 99.52820 | 94.01510 | -5.539 | 64 |
| 75 | 33.40000 | 27.41613 | 27.37291 | 100.45858 | 94.94560 | -5.488 | 64 |
| 80 | 33.70000 | 27.61127 | 27.59201 | 101.26266 | 95.78926 | -5.405 | 64 |
| 85 | 33.90000 | 27.79079 | 27.77607 | 101.93818 | 96.48948 | -5.345 | 64 |
| 90 | 34.00000 | 27.95337 | 27.92656 | 102.49049 | 97.09582 | -5.264 | 64 |
| 95 | 34.20000 | 28.06041 | 28.05448 | 102.95995 | 97.60977 | -5.196 | 64 |
| 100 | 34.30000 | 28.15461 | 28.16461 | 103.36412 | 98.04494 | -5.146 | 64 |
### Prices, costs and payments at the 59 comparable targets

| Series | Unit | Min | P05 | P25 | P50 | P75 | P95 | Max | n |
|---|---|---|---|---|---|---|---|---|---|
| Marginal effective price | US$2020/tCO₂ | -41.6197 | -38.9302 | -28.8133 | -20.0396 | -2.9576 | 19.4027 | 45.1630 | 59 (44 non-positive; 15 positive) |
| Positive project cost | million US$2015/yr | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0003 | 0.2222 | 12.4883 | 59 |
| Uniform payment | million US$2015/yr | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0003 | 0.5081 | 21.7516 | 59 |
| Signed net economic cost | million US$2015/yr | -297.2882 | -44.4580 | -9.7964 | -1.8610 | -0.0418 | 0.1986 | 12.4883 | 59 |
| Corrected available supply | GtCO₂ PV (n=71) | 0.0000 | 0.0000 | 0.0033 | 0.0832 | 0.7276 | 4.7837 | 37.9536 | 71 |
| Target coverage | % of 30y target (n=71) | 0.0000 | 0.0000 | 100.0000 | 100.0000 | 100.0000 | 100.0000 | 100.0000 | 71 |

For the 59 sufficient-supply units, the 30-year present values and annual equivalents reconcile as follows. The 44 units with non-positive marginal price have a **zero modeled uniform payment**, whereas their signed project costs can be negative; neither result proves zero implementation cost.

| Distinct quantity | 30y PV (million US$2020) | Annual equivalent (million US$2015/yr) | Population | Definition |
|---|---|---|---|---|
| Signed net economic cost | -12,596.402362 | -734.418881 | 59 | full signed modeled cost of selected cells |
| Positive project cost | 239.590042 | 13.969024 | 59 | only positive cell net costs |
| Uniform carbon payment | 448.803812 | 26.166995 | 59 (positive in 15) | positive cutoff price × full discounted target |

**Highest positive marginal-payment cases (all 15 listed).** Prices are derived cell effective costs, not interpolated values from the published 25-point curve. Zero-payment countries are retained in the 236-unit CSV.

| Unit | Name | Group | Loss (tCO₂/yr) | Price (US$2020/tCO₂) | Positive cost (M/yr) | Payment (M/yr) | Allocation (M/yr) | Allocation/payment |
|---|---|---|---|---|---|---|---|---|
| SOM | Somalia | LDCs | 525,910.67 | 45.1630 | 12.488265 | 21.751633 | 185.1889 | 8.5138 |
| AGO | Angola | LDCs | 1,748,832.86 | 1.3510 | 0.391483 | 2.163642 | 2,425.6908 | 1,121.1145 |
| BGD | Bangladesh | LDCs | 62,321.27 | 12.0412 | 0.255679 | 0.687229 | 54.3000 | 79.0130 |
| SUR | Suriname | SIDS | 32,102.82 | 16.6061 | 0.218495 | 0.488210 | 562.6582 | 1,152.4912 |
| UZB | Uzbekistan | Developing economies | 13,213.84 | 28.8480 | 0.070469 | 0.349093 | 228.5242 | 654.6220 |
| GMB | Gambia | LDCs | 19,837.28 | 16.3032 | 0.218437 | 0.296177 | 8.0318 | 27.1182 |
| GNQ | Equatorial Guinea | Developing economies | 28,539.65 | 7.1422 | 0.121138 | 0.186672 | 92.2779 | 494.3324 |
| CMR | Cameroon | Developing economies | 408,565.78 | 0.2974 | 0.105020 | 0.111281 | 734.0155 | 6,596.0337 |
| PAK | Pakistan | Developing economies | 93,059.76 | 1.0013 | 0.065185 | 0.085333 | 179.1897 | 2,099.8890 |
| GAB | Gabon | Developing economies | 42,415.47 | 0.5016 | 0.007493 | 0.019484 | 895.8806 | 45,980.0816 |
| LBY | Libya | Developing economies | 1,658.59 | 11.6831 | 0.016870 | 0.017746 | 11.5495 | 650.8316 |
| MUS | Mauritius | SIDS | 376.87 | 14.5428 | 0.005019 | 0.005019 | 1.4682 | 292.5067 |
| VCT | Saint Vincent and the Grenadines | SIDS | 102.78 | 27.1568 | 0.002556 | 0.002556 | 1.0936 | 427.7985 |
| DMA | Dominica | SIDS | 137.05 | 18.5412 | 0.002327 | 0.002327 | 2.1990 | 944.9881 |
| COM | Comoros | SIDS | 1,695.93 | 0.3812 | 0.000587 | 0.000592 | 1.2795 | 2,160.9386 |

**Insufficient modeled supply (all 12):**

| Unit | Name | Loss (tCO₂/yr) | Target (MtCO₂) | Available (MtCO₂) | Coverage (%) |
|---|---|---|---|---|---|
| SDN | Sudan | 919,127.40 | 14.43694 | 0.00000 | 0.000 |
| MLI | Mali | 520,908.53 | 8.18203 | 0.00000 | 0.000 |
| BFA | Burkina Faso | 441,679.31 | 6.93756 | 0.00000 | 0.000 |
| TCD | Chad | 439,281.02 | 6.89989 | 2.29231 | 33.222 |
| BEN | Benin | 376,034.70 | 5.90646 | 3.87422 | 65.593 |
| ZWE | Zimbabwe | 195,289.31 | 3.06745 | 0.90499 | 29.503 |
| SEN | Senegal | 73,490.45 | 1.15433 | 0.36565 | 31.677 |
| NER | Niger | 68,248.47 | 1.07199 | 0.00000 | 0.000 |
| IRQ | Iraq | 39,580.06 | 0.62169 | 0.00000 | 0.000 |
| ERI | Eritrea | 29,019.31 | 0.45581 | 0.00926 | 2.031 |
| NAM | Namibia | 11,049.26 | 0.17355 | 0.00000 | 0.000 |
| SWZ | Eswatini | 5,571.17 | 0.08751 | 0.00000 | 0.000 |

**No source curve (all 34):** AUS (Australia), SWE (Sweden), PRT (Portugal), CAN (Canada), ITA (Italy), FIN (Finland), KOR (Republic of Korea), EST (Estonia), AUT (Austria), DEU (Germany), NZL (New Zealand), BLR (Belarus), NLD (Netherlands (Kingdom of the)), NOR (Norway), ESP (Spain), SVN (Slovenia), HUN (Hungary), BEL (Belgium), CZE (Czechia), CHE (Switzerland), POL (Poland), MDA (Republic of Moldova), IRL (Ireland), GBR (United Kingdom of Great Britain and Northern Ireland), DNK (Denmark), LVA (Latvia), LTU (Lithuania), UKR (Ukraine), NCL (New Caledonia), SGP (Singapore), HRV (Croatia), ROU (Romania), SRB (Serbia), SPM (Saint Pierre and Miquelon). Their `Q_i` is computable from our loss scenario but supply, price and financing remain unavailable.

## 5. Allocation–mitigation comparisons

| Measure | n | Value | Unit | Interpretation |
|---|---|---|---|---|
| 2% allocation, all forest-account units | 236 | 165.228860 | billion US$2015/yr | policy rule, not a budget |
| 2% allocation, positive-loss sample | 105 | 103.240971 | billion US$2015/yr | broader than cost-comparable sample |
| 2% allocation, cost-comparable sample | 59 | 71.605731 | billion US$2015/yr | same 59 as cost/payment rows |
| Modeled positive project cost | 59 | 13.969024 | million US$2015/yr | annual equivalent of selected positive project costs |
| Modeled uniform payment | 59 | 26.166995 | million US$2015/yr | conditional carbon-price mechanism |

The three emphasized figures reconcile exactly: **71.605731 billion**, **13.969024 million**, and **26.166995 million** US$2015/year for the same 59 units. The comparison harmonizes the derived 30-year US$2020 present values to annual-equivalent US$2015 using the source factor and CPI ratio. The allocation is itself an annual hypothetical amount; comparing them assumes a constant real annual allocation for 30 years. Cost, payment and allocation are different economic objects, so subtracting them does **not** measure a financing gap.

| Ratio | n | Minimum | Median | Maximum | Denominator rule |
|---|---|---|---|---|---|
| Allocation / positive project cost | 15 | 14.8290 | 944.9881 | 119,557.9756 | defined only where positive project cost > 0 |
| Allocation / uniform payment | 15 | 8.5138 | 654.6220 | 45,980.0816 | defined only for 15 positive-price units |

For the 15 positive-payment units, 15/15 allocations exceed the modeled payment under this mechanism; this does not show real programs are affordable or funded. Ratios are undefined (not zero or infinite) for the 44 modeled zero-payment units.

## 6. Country-level and economic-group findings

| Group | GCW n | Loss n | Curve n | No curve n | Short supply n | Supply n | + price n | Loss (Mt/yr) | Group loss covered (%) | Matched allocation (B/yr) | + cost (M/yr) | Payment (M/yr) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Developed economies | 62 | 32 | 0 | 32 | 0 | 0 | 0 | 3.12562 | 0.000 | 0.00000 | 0.00000 | 0.00000 |
| Developing economies | 80 | 37 | 37 | 0 | 4 | 33 | 6 | 20.54862 | 98.776 | 54.36977 | 0.38618 | 0.76961 |
| LDCs | 37 | 22 | 22 | 0 | 8 | 14 | 4 | 11.28313 | 74.583 | 14.43048 | 13.35386 | 24.89868 |
| SIDS | 57 | 14 | 12 | 2 | 0 | 12 | 5 | 0.30876 | 99.384 | 2.80547 | 0.22898 | 0.49871 |

Country-level rows include all 236 allocations and group metadata, all 105 positive-loss targets (including those without source curves), the source-curve sheet, verification errors and cell counts for 71 countries, prices and three cost/payment concepts where supply is sufficient, plus explicitly undefined ratios. This is the complete national inventory for ranking and selection; absence from a source curve is not a zero cost.

## 7. Sensitivity analyses, uncertainties, and methodological limitations

| Sensitivity / version | Change | Observed diagnostic | Limit |
|---|---|---|---|
| Monetary valuation | Current GCW draw P05–P95 → 2% allocation P05–P95 | 64.530–299.984 billion/yr | fixed forest rates/areas and fixed 2% rule |
| Current valuation-fraction sensitivity | 25%, 33%, 50%, 75%, 100% | 100% mean 8,261.443 billion GCW/yr | 100% row reconciles with current Table 1 |
| Carbon-unit correction | source numeric ×3.67 | at 100: 53 → 59 covered | classification effect on same 71 |
| Natural soil counted once | reselect cell method and recalc curves | at 50: -5.789% corrected supply | source interpretation awaiting author clarification |
| Discount timing | source 15.707225 versus conventional 15.372451 | 2.1778% factor difference | alternative target and annualization require full re-evaluation |
| Published workbook price grid | Core-only, unconverted, 25 points | 46 covered at US$100/tCO₂ | separate workbook-grid diagnostic; not the corrected cell-level cost result |

Additional unpropagated uncertainties: four biome-rate uncertainty, FRA/GEZ forest surface error, mangrove overlap, deforestation coverage and time path, persistence of stored carbon, cell carbon and cost parameters, forest suitability and adoption, transaction costs, governance, wood revenues, future exchange rates and CPI choice. The 2% rule is a policy thought experiment. Busch's 30-year reforestation carbon pools and ecological trajectory are not the same physical service as current annual additions to living forest biomass; equal `Q_i` is scenario matching, not replacement or causal mitigation.

## 8. Validation and reproducibility evidence

- Input workbook, source Stata program and current national allocation CSV hashes are recorded in `busch_mangrove_refresh_20261023_summary.json`; the Zenodo source archive MD5 is `af26192c9349150071e4e4f40ba1f456`.
- The 71 national source curves are re-aggregated from published cell outputs at all 25 price points. The largest error normalized by a country's maximum source quantity is 0.437939%; seven all-zero curves match exactly. Brazil, China and Tanzania were individually checked across all 25 source prices.
- This script checks unique keys, n=236/105/1,775, the 2% national identity, the global Table 1 reconciliation, and the current 59/12/34 cell-level status counts. It writes the climate-finance inventory files only.
- The separate workbook-grid summary and this current cell-level reconstruction use different cost definitions and coverage tests. Neither should be substituted for the other.
- The source workbook's carbon units and the natural-soil code require external author clarification. The current cell-level finance comparison is validated internally against the cell outputs and equations, yet remains provisional scientifically.

## 9. Assessment of scientific relevance

| Evidence class | Finding | Use / boundary |
|---|---|---|
| New conditional information | 71 source curves recovered; 59 equal-tonnage targets within corrected modeled supply; 82.29% of the 105-unit annual loss; differentiated project cost and carbon-payment estimates | Useful for a carefully labelled complementary scenario; not a replacement-cost estimate |
| Mechanically implied | All national and group 2% totals, rankings, Gini, top-N shares, P05–P95 scaling | Describes the distribution of GCW under a stipulated rule; no independent finance observation |
| Scientifically informative with caution | 44 non-positive and 15 positive marginal-price cases; 12 supply-insufficient; 34 no curve; allocation/payment ratios | Source corrections, selected coverage and implementation limits must remain visible |
| Provisional interpretation | tC/tCO₂ and natural-soil corrections; workbook-grid versus cell-level coverage | Clarify with Busch authors before presenting the derived curves as definitive |
| Strengthen from existing data | Show group selection into 105/71/59, country price/payment rank distribution, 25-price correction stages, conventional-discount sensitivity | No new global model required; any full sensitivity must rerun the cost selection |
## 10. Proposed Figure 4 designs and supplementary materials

**Option 1 — allocation to comparable payments.** A: cumulative 236-unit allocation (top-10 and top-50 markers); B: group-level country distribution with group totals; C: 15 positive-price units, paired 2% allocation and modeled uniform payment on a log axis, with a separate note that 44 matched cases have modeled zero payment. Question: where does the stipulated allocation sit relative to a clearly specified payment mechanism? Avoid treating the separation as a financing gap.

**Option 2 — coverage before comparison.** A: 236-unit concentration; B: transition 105 → 71 → 59, with disjoint 44/15/12/34 loss shares; C: distribution of marginal effective prices for 59 and paired allocation/payment for positive-price units. Question: for whom can this comparison be made, and what does selection omit?

**Option 3 — within-sample cost structure.** A: group allocation distributions; B: 59-unit signed economic cost versus positive project cost (separate scales/labels); C: allocation–uniform-payment scatter for 15 positive cases, with 44 zero-payment cases marked separately. Question: how do economic resource costs, incentive transfers and hypothetical allocations differ? This is the most technical option.

**Supplementary tables:** full 236-unit country inventory; four-group distribution and sample selection table; all 71 × 25 published/reconstructed/corrected curve points; 25-price aggregate correction table; 100-point effective-cost curve per 64 nonzero-supply units; country-level validation errors and source hashes. **Supplementary figures:** Lorenz and ranked allocation curves; group-specific coverage flow; correction-stage supply curves at all 25 prices; marginal-price and payment distribution with explicit missing and zero cases. These are proposals only; no figure is produced here.

## 11. Complete source and output file references

| Role | File / source | Relevant columns / status |
|---|---|---|
| Current GCW | `results/country_level_gcw.csv` | `gcw_usd2015_yr_mean`, P05/P50/P95; 236 rows |
| National 2%, pledge and loss | `results/validation/our_2pct_gcw_allocation_and_pledge.csv` | `our_2pct_gcw_allocation_usd2015_yr`, `share_of_30yr_100bn_pledge_usd_cumulative`, `lost_capacity_tco2_yr`, group, 236 rows |
| Global valuation draws | `results/tables/manuscript/Table1_global_carbon_wealth.csv` | Green carbon wealth mean/P05/P50/P95 |
| Allocation and legacy Busch script | `code/scripts/compare_finance_and_action_costs.py` | 2% and 105-unit positive-loss sample; old conventional target |
| Latest Busch reconstruction script | `code/scripts/rebuild_busch_sample_finance.py` | source reconstruction, carbon/soil correction, effective-price selection, annualization |
| Latest sample coverage | `results/validation/busch_reconstruction/busch_mangrove_refresh_20261023_coverage_105.csv` | 105 rows; current loss, target and finance status |
| Latest national finance | `results/validation/busch_reconstruction/busch_mangrove_refresh_20261023_country_finance.csv` | 71 source curves, of which 59 have target costs |
| All source-price curves | `results/validation/busch_reconstruction/busch_mangrove_refresh_20261023_25_price_curves.csv` | 1775 price-point records, four versioned series |
| Derived detailed curves | `results/validation/busch_reconstruction/busch_full_effective_cost_curves.csv` | 64 × 100 = 6,400 supply-percentile records; source reconstruction independent of target, re-targeted by current run |
| Validation and input hashes | `results/validation/busch_reconstruction/busch_mangrove_refresh_20261023_summary.json` | current sample, coverage, correction stages, source hashes |
| Published source workbook/code | `data/raw/economic/busch_2024/11_MAC_curves_consolidated.xlsx`; `data/raw/economic/busch_2024/stata_code/10_stata_code/1. Model loop all data.do` | 115 Core + 23 Other country columns; cell model code |
| Public cell outputs | [Busch et al. Zenodo record 19239386](https://zenodo.org/records/19239386) | `09_output_dtas.zip`, MD5 as above |
| Currency conversion | [BLS annual CPI-U](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm) | 2015 = 237.017; 2020 = 258.811 |
| Published article | [Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1) | published study; derived corrections are ours |
| Workbook-grid Figure 4 outputs | `results/validation/finance_figure4_summary.json` | historical published-grid comparison; distinct from current cell-level reconstruction |
| Inventory builder | `code/scripts/build_climate_finance_results_inventory.py` | reads only inputs above; writes four new CLIMATE_FINANCE files |
| Complete national inventory | `results/validation/CLIMATE_FINANCE_country_inventory_236.csv` | all 236 units with matching/undefined finance fields |
| Group inventory | `results/validation/CLIMATE_FINANCE_group_inventory.csv` | group quantiles, totals, sample composition |
| 25-price aggregate | `results/validation/CLIMATE_FINANCE_price_grid_aggregate_71.csv` | price-by-price carbon and soil correction effects |

**Reproduce this inventory:** from the repository root run `python code/scripts/build_climate_finance_results_inventory.py`. This uses the latest existing files and writes only the four inventory artifacts. It does not rerun the 2.94 GB cell reconstruction, modify canonical tables, or export a figure. Source values should be re-audited before any manuscript claim because the Busch interpretations remain provisional.
