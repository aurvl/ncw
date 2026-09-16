# GCW and NCW calculation methods

Choices and their alternatives are documented in `MYCHOICES.md` (C#).

## Accounting object

For territory `i`, GCW values an annual forest CO2 uptake flow:

$$
GCW_i = U_i \times GSCC, \qquad U_i \; [\text{tCO}_2/\text{yr}] = \frac{44}{12} \, F_i^C \; [\text{tC}/\text{yr}].
$$

GSCC is taken draw by draw from the BCW release (mean 559.6 constant 2015 US$/tCO2).

## Route B — main: Pan area × rate (C1)

1. **Areas.** FRA 2025 forest, naturally regenerating forest (NRF), planted forest and mangroves, year 2025 (`forest_areas.py`). Mangroves are removed from NRF because BCW counts them (C7).
2. **Biome shares.** Each country's forest is split into tropical, subtropical, temperate and boreal shares from FAO GEZ 2010 zones intersected with EEZ_land_union v4 land polygons and restricted to JRC GFC2020 forest pixels (~2.3 km). FRA-reported shares are used where the rasters do not resolve a country (`biome_shares.py`, C2). Within a country, NRF and planted forest are assumed to have the same biome shares.
3. **Rates.** For Pan biomes, rate = Pan et al. (2024) Table 1 flux 2010–2019 / global FRA area of that biome. In the tropics NRF uses the intact-forest flux and planted forest the regrowth flux (C9). The subtropical rate is 0.95 ± 0.13 tC/ha/yr from the coauthors' interpolation (C3). By construction, the pipeline reproduces Pan's biome totals.

$$
F_i^C = \sum_{b,t} A_{i,b,t} \, q_{b,t}
$$

4. **Uncertainty.** Each rate is drawn from a normal distribution truncated at zero, once per draw and shared by all countries (C8). Area uncertainty is not propagated.

## Route A — complementary: FAOSTAT net flux (C1)

FAOSTAT *Emissions from forests*, Item `Forestland`, Element `Net emissions/removals (CO2) (Forest land)`, source `FAO TIER 1`, sign flipped so removals are positive, mean 2015–2024 (C4). This is removals minus losses and includes mangroves. Only the GSCC is uncertain.

## NCW

$$
NCW_i = GCW_i^{\text{excl. mangroves}} + BCW_i
$$

summed draw by draw with BCW draws re-aligned to the published BCW table. The alternative `GCW incl. mangroves + BCW − value of BCW mangrove uptake` is reported for C7.

## Aggregation

Totals by continent, group and world are computed on draws, then summarised (mean, sd, p5, p50, p95). Standard deviations are never added directly.
