# Methods

Subjective choices and their alternatives are documented in `MYCHOICES.md` (kept with the manuscript, outside this repository); `C#` references below point to it.

## 1. Accounting object

For accounting unit `i`, Green Carbon Wealth values the annual forest CO2 uptake:

$$
GCW_i = U_i \times GSCC, \qquad U_i = \frac{44}{12}\, C_i
$$

with $C_i$ in tC/yr, $U_i$ in tCO2/yr, GSCC in constant 2015 US$ per tCO2 and $GCW_i$ in constant 2015 US$ per year. Natural Carbon Wealth adds Blue Carbon Wealth: $NCW_i = GCW_i + BCW_i$.

GCW and NCW are annual welfare contributions of carbon sinks. They are not stock values, market prices, finance needs or additional mitigation.

## 2. Accounting units (C12)

Units are the FRA 2025 countries and territories. BCW rows are mapped onto them with `data_source/reference/territory_crosswalk.csv`:

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

Country forest area by biome is FRA 2025 total forest area multiplied by the four FAO Global Ecological Zones (GEZ) shares. The FRA mangrove area is subtracted from the tropical area, following the existing decision to avoid counting mangroves in both GCW and BCW:

$$
A_{i,T}=F_i s_{i,T}-M_i,\quad A_{i,ST}=F_i s_{i,ST},\quad
A_{i,Te}=F_i s_{i,Te},\quad A_{i,B}=F_i s_{i,B}.
$$

If reported mangroves exceed the GEZ-allocated tropical forest area, the subtraction is floored at zero and flagged for review.

## 6. Gibbs/GFW gross rates to living biomass (C28)

The main rate source is the published Gibbs et al. (2025) / Global Forest Watch gross-removals raster set for 2001-2023. Its pixel values represent cumulative CO2 removals per hectare into above- and below-ground living biomass. For each modeled forest pixel, the pipeline divides the cumulative value by 23 and converts CO2 to carbon:

$$q_p = X_{p,2001:2023}\times\frac{1}{23}\times\frac{12}{44}.$$

The pixel is assigned to one of four FAO GEZ domains. The biome rate $q_b$ is the pixel-area-weighted mean of $q_p$ in that domain. For the geographic raster grid, pixel area varies with latitude; the aggregation therefore weights by $\cos(\text{latitude})$. It retains spatial standard deviation as a description of variation among modeled pixels, not as a confidence interval or rate-estimation error.

The selected sensitivity analysis recomputes country estimates with $q_b- SD_b$ (floored at zero) and $q_b+SD_b$. These are deterministic spatial-dispersion scenarios, separate from the main estimate and from the GSCC Monte Carlo draws. Gibbs/GFW rates summarize 2001-2023, while the country areas are FRA 2025; this temporal pairing is an explicit approximation. The source's spatial model uses a hierarchy of factors, including IPCC defaults and region- or forest-type-specific factors; the IPCC comparison is therefore not fully independent.

## 7. Country uptake (C1, C28)

$$
C_i = A_{i,T}q_T + A_{i,ST}q_{ST} + A_{i,Te}q_{Te} + A_{i,B}q_B,
\qquad U_i = \frac{44}{12} C_i.
$$

Here $C_i$ is the annual addition to living above- and below-ground biomass under the chosen indicator. The deforestation-related loss is assessed separately; it is not subtracted from this gross-addition measure.

## 8. Net flux — Route A, complementary (C1, C4)

FAOSTAT *Emissions from forests*, Item `Forestland`, Element `Net emissions/removals (CO2) (Forest land)`, source `FAO TIER 1`; sign flipped so removals are positive; mean 2015–2024. This is removals minus losses (it can be negative) and it includes mangroves.

## 9. Uncertainty and spatial sensitivity (C8, C15, C28)

Monte Carlo with $B = 20\,000$ draws.

- Main Gibbs/GFW biome rates are fixed at their area-weighted means in every draw; the source rasters do not provide a pixel-level standard error for these biome means.
- Spatial sensitivity is reported separately using each biome's mean rate minus/plus one spatial standard deviation. This spread describes pixel heterogeneity and is not sampled as probabilistic uncertainty.
- GSCC: the 20 000 draws of the BCW release (mean 559.6, median 506.7 US$2015/tCO2), identical for GCW and BCW.
- Areas are not uncertain.
- Route A: only the GSCC is uncertain.

$$
GCW_i^{(k)} = U_i^{(k)}\, G_k, \qquad NCW_i^{(k)} = GCW_i^{(k)} + BCW_i^{(k)}
$$

BCW draw rows are re-aligned to the published BCW table (matching mean and Monte Carlo standard error).

**Mangrove gap-fill (C18).** Units with FRA mangroves but no mangroves in BCW (Indonesia, Cuba, Senegal and four very small units) receive a BCW mangrove component estimated with the BCW framework and the same draws: $BCW^{\text{mang}}_{i,(k)} = M_i^{\text{km}^2} \times r_{(k)} \times \frac{44}{12} \times G_k$, where $r_{(k)}$ are the BCW mangrove rate draws (lognormal, tC/km²/yr) and $M_i$ the FRA 2025 mangrove area. Without it, these mangroves would be removed from GCW and counted nowhere. An alternative NCW keeps mangroves in the forest area and subtracts the value of BCW mangrove uptake (C7).

## 10. Aggregation and reporting

Every total (continent, group, world) is summed draw by draw, then summarised by the mean, standard deviation and 5th, 50th and 95th percentiles. Standard deviations are never added. The reported standard deviation is the spread of the value, not the Monte Carlo standard error of the mean (C14).
