# Notebooks

The notebooks are grouped by their role in the analysis and manuscript workflow. Reusable calculations remain in `../src/gcw/` and `../scripts/` so they can be tested and run without notebook state.

| Notebook | Role |
| --- | --- |
| `03_figures.ipynb` | Historical figure exploration; not the canonical manuscript output |
| `04_analyses_R1_R4.ipynb` | Exploratory R1-R4 results and supplementary analyses |
| `05_manuscript_tables_figures.ipynb` | Current four main tables and supplementary table exports |
| `06_paper_figures_v2.ipynb` | Current manuscript figure workflow; generates Figures 1-3 and gates Figure 4 on author model selection |

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

Run notebooks from the repository root. The current manuscript notebooks call `code/scripts/build_manuscript_artifacts.py`, which reads the committed canonical outputs and validates sample counts. Rebuild underlying accounts with `python code/scripts/main.py --reuse-gfw-rates` only when the account inputs have changed. Add `--rasters` only when you intend to rebuild biome allocation.
