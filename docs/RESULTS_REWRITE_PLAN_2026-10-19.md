# Results rebuild and manuscript handoff

**Status date:** 20 October 2026
**Canonical build:** `code/scripts/build_manuscript_artifacts.py`
**Full output inventory:** [`../../NEXT/RESULTS_INVENTORY.txt`](../../NEXT/RESULTS_INVENTORY.txt)

## Canonical analysis inputs

- Forest physical flow: Gibbs/GFW additions to living above- and below-ground biomass for four FAO GEZ domains, with mapped mangrove pixels excluded from the biome-rate estimation. The source-rate period remains 2001–2023; application uses current FRA 2025 forest area.
- Marine mangroves: GMW v4.1.12 map year 2025, spatially assigned using the current BCW unit crosswalk. Other BCW components and published uptake rates remain as specified in the source account.
- Country socioeconomic and emissions inputs: population, GDP and emissions for 2024 where available; debt is not used. Current figures use 2024 GDP and 2024 emissions only.
- Pan et al. (2024) is the only alternative forest-rate comparison retained in current paper-facing tables. Historical versions remain outside canonical artifacts for audit.
- Required samples checked by the builder: 236 GCW units; 175 with both accounts; 162 in the common emissions-balance comparison; 139 FRA deforestation reporters, including 105 with positive estimated capacity loss.

## Proposed Results sequence: five sections, paragraph by paragraph

### 1. Global and national patterns in natural carbon wealth

- **Paragraph 1 — Physical forest additions.** Report the four non-mangrove Gibbs/GFW rates, the four-biome scope, and the resulting 14.733 GtCO₂/year addition to living biomass; anchor it to Table S1 and the detailed biome-accounting supplement.
- **Paragraph 2 — Global wealth accounts.** Present the GCW, BCW and NCW distributions and their shares, using Table 1; keep the physical forest flow distinct from its GSCC-based monetary valuation.
- **Paragraph 3 — Geographic and economic distribution.** Describe where GCW is large in absolute terms and relative to 2024 GDP, then compare economic-group profiles and green/mixed/blue account composition; use Figure 1, Table 2 and the concentration/top-ten supplements.

### 2. Carbon-account balances against 2024 emissions

- **Paragraph 4 — Green/blue account composition and balance transitions.** Explain how adding the marine account changes the sign of the accounting balance relative to 2024 emissions for the 162-unit common sample; use Figure 2 and the unit/group transition supplements. State that this is a country-boundary accounting comparison, not a climate-neutrality test.

### 3. Deforestation and erosion of annual forest-addition capacity

- **Paragraph 5 — Scale and distribution of estimated loss.** Report the 139 FRA reporters, 105 positive estimated losses, total annual capacity loss and its distribution across groups; use Table 3 and Figure 3.
- **Paragraph 6 — Relative erosion and scenario values.** Compare loss with existing GCW and describe projection/capitalisation assumptions separately; use Figure 3 and the deforestation supplement. Distinguish lost annual capacity from emissions released by the carbon already stored in cleared biomass.

### 4. Spatial associations

- **Paragraph 7 — The three primary relationships.** Report standardized associations for the final selected specifications for forest-capacity loss, relative erosion and GCW/GDP; anchor the coefficients in Figure 4 and the spatial supplement. The plot is pending the researcher's final model/weight choices.
- **Paragraph 8 — Six emissions extensions.** Summarize what changes when 2024 emissions are added as X to each existing outcome and when emissions are Y with each outcome added as X; use the nine-relationship dossier and selected diagnostic tables. Keep these cross-sectional results descriptive and distinguish the extended analyses from the three core relationships.

### 5. Climate-finance scenarios

- **Paragraph 9 — Ibrahim allocation scenario.** Report the 2% of annual GCW allocation by country group using Table 4, explicitly identifying it as a stipulated allocation rather than observed finance or estimated need.
- **Paragraph 10 — Busch action-cost comparison.** Present the complementary action-cost evidence only for the countries and targets covered by published curves; report the coverage and category audit from Supplementary Table S6. Do not combine Busch marginal costs with either Ibrahim's 2% allocation or the 2% discount rate used in capitalisation.

## Four main tables

1. `Table1_global_carbon_wealth.csv` — global GCW, BCW and NCW means and monetary distributions.
2. `Table2_geographic_economic_profiles.csv` — economic-group profiles, 2024 GCW/GDP and green/mixed/blue account types.
3. `Table3_forest_capacity_erosion.csv` — estimated annual forest-addition capacity loss and relative erosion by group.
4. `Table4_Ibrahim_2pct_allocation.csv` — Ibrahim's stipulated allocation of 2% of annual GCW. This is not an estimate of observed finance needs.

**Supplementary Table S1:** `TableS1_forest_biome_additions.csv` — paper-ready four-biome area, Gibbs/GFW removal rate, gross annual additions and global shares. `Supplementary_forest_biome_accounting.csv` retains the unrounded values and spatial-dispersion sensitivity.

## Four main figures

1. `Figure1_GCW_relative_to_GDP_2024.png` — national GCW relative to 2024 GDP.
2. `Figure2_marine_composition_and_balance_transitions.png` — green/blue account composition and 2024 emissions-balance transitions.
3. `Figure3_forest_capacity_erosion.png` — geographic erosion intensity and its descriptive association with GCW.
4. `Figure4_spatial_associations.png` — standardized coefficients for the three primary spatial relationships. The code and status output are ready, but this figure remains gated until the researcher records final model and weight choices in `results/validation/spatial_model_decision_template.csv`. Candidate diagnostics do not select a final model automatically.

## Supplementary outputs and boundaries

The notebook exposes biome rates and physical totals, the Pan comparison, current unit-level accounts, FRA/GMW mangrove reconciliation, 2024 balance transitions, deforestation trends and scenarios, Busch coverage and action costs, concentration and group tests, and the full spatial-model evidence. Ibrahim's 2% allocation, the 2% discount-rate capitalization scenario, and Busch marginal action costs are separate analyses.

Spatial analysis covers nine relationships under Queen contiguity and symmetric k-nearest-neighbour-5 weights, with six candidate model families (108 relationship/model/weight records). The selection process includes Moran diagnostics, LM tests, nested likelihood-ratio tests and fit evidence. Final decisions remain the researcher's. Figure 4 is the only main artifact intentionally pending that decision; the diagnostics and coefficient tables are available.

The canonical country table is `Supplementary_country_level_accounts_2024.csv`: one row per study unit with current identifiers, grouping, account values, socioeconomic data, spatial/environmental areas, forest flows and deforestation indicators. Missing observations remain missing rather than being set to zero.

## Rebuild and verification

Run `code/notebooks/05_manuscript_tables_figures.ipynb` for tables and supplementary outputs, then `code/notebooks/06_paper_figures_v2.ipynb` for figures. Both notebooks are executable independently from the repository. Run `python code/scripts/build_results_inventory.py` to refresh the plain-text inventory. Validation is implemented in the artifact builder and tests under `code/tests/`.

Manuscript Results drafting, final model decisions for Figure 4, figure/table insertion and final prose synchronization remain downstream writing tasks.
