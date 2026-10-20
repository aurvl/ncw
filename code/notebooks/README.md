# Notebooks

The notebooks are grouped by their role in the analysis and manuscript workflow. Reusable calculations remain in `../src/gcw/` and `../scripts/` so they can be tested and run without notebook state.

| Notebook | Role |
| --- | --- |
| `03_figures.ipynb` | Earlier paper figure workflow |
| `04_analyses_R1_R4.ipynb` | Exploratory R1-R4 results and supplementary analyses |
| `05_manuscript_tables_figures.ipynb` | Manuscript-specific tables and figure exports |
| `06_paper_figures_v2.ipynb` | Current paper figure workflow |

## Component guides

The notebooks in `components/` are short navigation guides. They check file availability, show a small table preview, and point to the code entry point for each component.

| Guide | Component |
| --- | --- |
| `components/forest_account.ipynb` | Forest-area allocation, Gibbs/GFW rates, and GCW |
| `components/marine_account.ipynb` | BCW inputs and GMW mangrove-area update |
| `components/national_accounts.ipynb` | Country-level GCW and NCW accounts |
| `components/socioeconomic_emissions.ipynb` | 2024 emissions and socioeconomic covariates |
| `components/deforestation_finance.ipynb` | Capacity loss and climate-finance scenarios |
| `components/spatial_models.ipynb` | Spatial diagnostics and model comparisons |

Run notebooks from the repository root so their project-root discovery and relative paths resolve consistently. Rebuild the underlying accounts with `python code/scripts/main.py --reuse-gfw-rates` before refreshing notebook outputs. Add `--rasters` only when you intend to rebuild the biome allocation.
