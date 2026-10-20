# Methods

The current pipeline uses the GMW 2025 spatial mangrove replacement for BCW and
selectively removes only report-documented FRA forest-mangrove overlap from GCW.
Conditional GSCC valuation and the Rickels-style forest-loss abatement-cost
scenario are documented in `docs/GMW_GCW_VALUATION_AND_ABATEMENT_SCENARIOS.md`.

Subjective choices and their alternatives are documented in `MYCHOICES.md` (kept with the manuscript, outside this repository); `C#` references below point to it.

## 1. Accounting object

For accounting unit `i`, Green Carbon Wealth values annual carbon additions to
the living above- and below-ground biomass of existing forests:

$$
GCW_i = U_i \times GSCC, \qquad U_i = \frac{44}{12}\, C_i
$$

with $C_i$ in tC/yr, $U_i$ in tCO2/yr, GSCC in constant 2015 US$ per tCO2 and $GCW_i$ in constant 2015 US$ per year. Natural Carbon Wealth adds Blue Carbon Wealth: $NCW_i = GCW_i + BCW_i$.

This is an operational measure of the annual addition to living biomass; losses
from that compartment are not subtracted in this forest indicator and are
analysed separately. The measure is not the net carbon balance of every forest
ecosystem pool. GCW and NCW are annual welfare values, not stock values, market
prices, finance needs or additional mitigation.

## 2. Accounting units (C12)

Units are the FRA 2025 countries and territories. BCW rows are mapped onto them with `data/reference/territory_crosswalk.csv`:

- countries split in BCW and sub-territories included in an FRA country are regrouped; BCW values and draws are summed;
- population and GDP are never summed: they come from the country row or from the main part;
- continent and economic group come from the main country;
- Taiwan is regrouped under China, as in FAO statistics (unit renamed "China (incl. Taiwan, Hong Kong SAR and Macao SAR)");
- BCW-only territories and the BCW "Joint Regimes" / "Overlapping Claims" rows are kept as separate units.

## 3. Forest areas

FRA 2025 total forest area $F_i$ and mangrove area $M_i$ for 2025, in hectares. Naturally regenerating forest (NRF), planted forest and primary forest (PR) are kept as descriptive variables only: $F = NRF + Planted$ and $PR \subset NRF$, so PR is never added to NRF or planted forest (C17).

## 4. Biome shares (C2)

FAO Global Ecological Zones 2010 and EEZ_land_union v4 country polygons are rasterised on the grid of the JRC Global Forest Cover 2020 map (~2.3 km). For each country, forest pixel areas $a(\text{lat}) = R^2 \Delta\phi\, \Delta\lambda \cos(\text{lat})$ are summed by biome (first digit of the GEZ code; polar → boreal; water excluded):

$$
s_{i,b} = \frac{S_{i,b}}{\sum_{b'} S_{i,b'}}, \qquad b \in \{\text{tropical, subtropical, temperate, boreal}\}
$$

Countries not resolved by the grid use FRA-reported climatic-domain shares.

## 5. Four forest biomes and mangroves (C17, C7)

Country forest area by biome is FRA 2025 total forest area multiplied by the four FAO Global Ecological Zones (GEZ) shares. A country-report audit identified nine cases where the exact mangrove class area matches FRA's 2025 mangrove total and the national crosswalk assigns 100% of that class to FRA Forest: BHS, KEN, KIR, PNG, VCT, WSM, SGP, TLS and TON. Their combined documented overlap is 495,400 ha. Only this documented amount is removed from the tropical allocation:

$$
A_{i,T}=F_i s_{i,T}-M_i^{documented},\quad A_{i,ST}=F_i s_{i,ST},\quad
A_{i,Te}=F_i s_{i,Te},\quad A_{i,B}=F_i s_{i,B}.
$$

FRA defines its separately reported mangrove category as forest **and** other wooded land, so the whole reported mangrove total cannot be subtracted from the forest total. One audited report assigns its matched mangrove class entirely to other wooded land (LCA; 220 ha), so it is not subtracted. The split remains unresolved for three cases (PAK, SHN, TCA) and was not verified for 103 other positive-reporting units. Those areas are retained in FRA forest totals rather than assumed to be wholly inside or wholly outside forest. This conservative rule avoids unsupported subtraction but may leave some true overlap with the new BCW mangrove layer; that possible residual double attribution is disclosed as a limitation. The original category exceeds the GEZ tropical allocation in three units, which remains an audit warning only; it no longer drives a clipped area subtraction. The evidence table is `data/derived/fra_mangrove_forest_overlap_2025.csv`.

## 6. Gibbs/GFW gross rates to living biomass (C28)

The main rate source is the published Gibbs et al. (2025) / Global Forest Watch gross-removals raster set for 2001-2023. Its pixel values represent cumulative CO2 removals per hectare into above- and below-ground living biomass. For each modeled forest pixel, the pipeline divides the cumulative value by 23 and converts CO2 to carbon:

Gibbs et al. [Table 4](https://essd.copernicus.org/articles/17/1217/2025/) publish **total annual gross removals**, not the four per-hectare rates used below. They report removals with a negative sign in their emissions-positive flux convention. The table shows positive magnitudes and their published ±1 standard deviations for 2001-2023:

| Gibbs climate domain | Gross removal magnitude (Gt CO₂/yr) | Published SD (Gt CO₂/yr) |
|---|---:|---:|
| Tropical | 7.1 | 7.6 |
| Subtropical | 1.7 | 0.56 |
| Temperate | 3.1 | 0.55 |
| Boreal | 2.5 | 0.95 |
| Global | 14.5 | 7.7 |

These are the authors' climate-domain totals and include the model's mangrove pixels. Their boundaries need not match our FAO GEZ assignment exactly; these totals are not divided by FRA 2025 forest area to create our rates.

$$q_p = X_{p,2001:2023}\times\frac{1}{23}\times\frac{12}{44}.$$

The pixel is assigned to one of four FAO GEZ domains. The denominator $A_b$ is the total spherical area, in hectares, of valid Gibbs/GFW pixels assigned to biome $b$. For each EPSG:4326 pixel, its area is computed from the longitude width and the sine difference between its northern and southern latitude edges. The biome rate $q_b$ is the mean of $q_p$ weighted by these pixel areas. The pipeline also retains the spatial standard deviation as a description of variation among modeled pixels, not as a confidence interval or rate-estimation error.

The main non-mangrove rates use the forest-type tiles generated by the same [WRI model release v1.3.2](https://github.com/wri/carbon-budget/blob/v1.3.2/removals/annual_gain_rate_AGC_BGC_all_forest_types.py). Source forest-type code 6 denotes pixels to which the model assigns mangrove removal factors. For each of the 272 removals tiles, the matching forest-type tile has the same grid; pixels with code 6 are excluded from both the weighted numerator and area denominator before the four biome means are calculated. The removed pixel count and area are retained by biome. Four tile/biome cells consist entirely of mangroves and have zero weight in the clean rate. This excludes the model's mangrove-factor pixels; it does not claim to identify every ecological mangrove in the later FRA 2025 area series. The original all-forest rates remain in `gfw_gibbs_biome_rates_with_mangroves.csv` for comparison; the clean rates are the primary cached table after area and pixel reconciliation.

| FAO GEZ biome | Our raster mean incl. mangrove pixels (tC/ha/yr) | Main rate excluding mangrove pixels (tC/ha/yr) | Non-mangrove source-pixel area (ha) |
|---|---:|---:|---:|
| Tropical | 0.960530 | **0.934399** | 1,997,984,310 |
| Subtropical | 1.376466 | **1.370738** | 338,000,593 |
| Temperate | 1.430112 | **1.430069** | 604,093,056 |
| Boreal | 0.618633 | **0.618633** | 1,101,382,760 |

Both per-hectare columns are **our estimates from the published rasters**. They are not rates that Gibbs et al. report directly. Only the non-mangrove column is used in the main national estimates. The country-report area adjustment above and the pixel-level source mask are separate harmonisation steps: the former corrects FRA area only when Forest classification is documented; the latter excludes source-model pixels assigned mangrove factors from the four rate calculations.

The selected sensitivity analysis recomputes country estimates with $q_b- SD_b$ (floored at zero) and $q_b+SD_b$. These are deterministic spatial-dispersion scenarios, separate from the main estimate and from the GSCC Monte Carlo draws. Gibbs/GFW rates summarize 2001-2023, while the country areas are FRA 2025; this temporal pairing is an explicit approximation. The source's spatial model uses a hierarchy of factors, including IPCC defaults and region- or forest-type-specific factors; the IPCC comparison is therefore not fully independent.

## 7. Country uptake (C1, C28)

$$
C_i = A_{i,T}q_T + A_{i,ST}q_{ST} + A_{i,Te}q_{Te} + A_{i,B}q_B,
\qquad U_i = \frac{44}{12} C_i.
$$

Here $C_i$ is the annual addition to living above- and below-ground biomass under the chosen indicator. The deforestation-related loss is assessed separately; it is not subtracted from this gross-addition measure.

## 8. Net flux - Route A, complementary (C1, C4)

FAOSTAT *Emissions from forests*, Item `Forestland`, Element `Net emissions/removals (CO2) (Forest land)`, source `FAO TIER 1`; sign flipped so removals are positive; mean 2015-2024. This is removals minus losses (it can be negative) and it includes mangroves.

## 9. Uncertainty and spatial sensitivity (C8, C15, C28)

Monte Carlo with $B = 20\,000$ draws.

- Main Gibbs/GFW biome rates are fixed at their area-weighted means in every draw. Gibbs et al. report global gross removals of 14.5 ± 7.7 Gt CO₂/yr for 2001-2023; ±7.7 is one standard deviation from error propagation across model inputs whose variances were available and considered potentially substantial. They report uncertainties for the global and climate-domain totals, not per-hectare uncertainty for four FAO GEZ biome rates. They also state that the framework cannot provide pixel-level uncertainty maps and that propagation to biomes or countries requires uncertainty information for each input at the requested scale. We retain the published uncertainty at its reported scale and do not convert it into country or biome intervals (Gibbs et al., 2025, Sections 2.2 and 4.3; Table 4).
- Spatial sensitivity is reported separately using each biome's mean rate minus/plus one spatial standard deviation. This spread describes pixel heterogeneity and is not sampled as probabilistic uncertainty.
- GSCC: the 20 000 draws of the BCW release (mean 559.6, median 506.7 US$2015/tCO2), identical for GCW and BCW.
- Forest areas and the mapped GMW 2025 mangrove areas are fixed in the main calculation; no statistical area interval is propagated.
- Route A: only the GSCC is uncertain.

$$
GCW_i^{(k)} = U_i^{(k)}\, G_k, \qquad NCW_i^{(k)} = GCW_i^{(k)} + BCW_i^{(k)}
$$

BCW draw rows are re-aligned to the published BCW table (matching mean and Monte Carlo standard error).

**BCW mangrove area replacement.** The BCW mangrove component uses the GMW v4.1.12 mapped 2025 extent. GMW's README states that its country area statistics apply a global accuracy correction factor of 0.9775 to mapped extent. We intersect the country-coded vector geometry with the same EEZ/land boundaries as the BCW account, then multiply each source-code intersection and its residual transfers by the corresponding corrected-area / raw-vector-area ratio from GMW's country-statistics workbook. The ratios reconcile to the stated 0.9775 factor; this retains the mapped spatial allocation while matching corrected GMW source-code totals. The corrected hectares are then assigned to the accounting unit of the intersected EEZ. Residual area not assigned to an admissible territory remains unassigned and is reported separately. This is a global product correction, not a country-specific classification-error model. We treat the corrected areas as fixed; the lower and upper workbook statistics and map-classification uncertainty are not propagated in the main Monte Carlo interval. The spatial audit records the remaining unassigned hectares and any country-code/boundary disagreements. The operation replaces only BCW's mangrove area and retains the existing Hilmi/Alongi mangrove-burial-rate draws; salt marshes, seagrasses and open-ocean BCP remain unchanged. The FRA-to-GMW area comparison and report-level overlap audit remain separate: GMW supplies the BCW mangrove area, while FRA report evidence governs only the documented mangrove subtraction from GCW.

## 10. Aggregation and reporting

Every total (continent, group, world) is summed draw by draw, then summarised by the mean, standard deviation and 5th, 50th and 95th percentiles. Standard deviations are never added. The reported standard deviation is the spread of the value, not the Monte Carlo standard error of the mean (C14).
