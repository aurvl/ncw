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

## 5. Harmonised biomes (C17)

Pan et al. (2024) include subtropical forests in their tropical set. Country areas are therefore grouped into three Pan biomes; mangroves, counted in BCW, are removed from the tropical area (C7):

$$
A_{i,T} = F_i\,(s_{i,\text{tropical}} + s_{i,\text{subtropical}}) - M_i, \qquad
A_{i,Te} = F_i\, s_{i,\text{temperate}}, \qquad
A_{i,B} = F_i\, s_{i,\text{boreal}}
$$

## 6. Sequestration rates (C17)

One mean rate per Pan biome, from Pan et al. (2024) only:

$$
q_T = \frac{\Phi_{T,\text{intact}} + \Phi_{T,\text{regrowth}}}{A^{Pan}_{T,\text{intact}} + A^{Pan}_{T,\text{regrowth}}}, \qquad
q_{Te} = \frac{\Phi_{Te}}{A^{Pan}_{Te}}, \qquad
q_B = \frac{\Phi_B}{A^{Pan}_B}
$$

- $\Phi$: Table 1 fluxes, 2010–2019 (Pg C/yr): tropical 2.52 ± 0.41 ("All tropical forests"), temperate 0.68 ± 0.05, boreal 0.32 ± 0.04.
- $A^{Pan}$: mean of the 2010 and 2020 biome areas of Extended Data Table 1.
- Resulting rates (tC/ha/yr): tropical 1.32 ± 0.21, temperate 0.87 ± 0.06, boreal 0.28 ± 0.03.

No FAO forest type is matched to Pan's intact or regrowth categories. Before use, the pipeline checks that $q_b \times A^{Pan}_b = \Phi_b$ and that each derived rate matches the stock change per area published in Extended Data Table 3 (`data_source/summary/pan_rate_checks.csv`); it stops if a check fails.

## 7. Country uptake — Route B, main (C1)

$$
C_i = A_{i,T}\, q_T + A_{i,Te}\, q_{Te} + A_{i,B}\, q_B, \qquad U_i = \frac{44}{12}\, C_i
$$

## 8. Net flux — Route A, complementary (C1, C4)

FAOSTAT *Emissions from forests*, Item `Forestland`, Element `Net emissions/removals (CO2) (Forest land)`, source `FAO TIER 1`; sign flipped so removals are positive; mean 2015–2024. This is removals minus losses (it can be negative) and it includes mangroves.

## 9. Uncertainty (C8, C15)

Monte Carlo with $B = 20\,000$ draws.

- Rates: $q_b^{(k)} = \max\left(0, \mathcal{N}(q_b, \sigma_{q_b})\right)$, one draw per biome shared by all countries, with $\sigma_{q_b} = \sigma_{\Phi_b} / A^{Pan}_b$.
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
