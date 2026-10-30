# Notebooks

The notebooks are independent analytical deep dives into the pipeline. Run `code/scripts/main.py` first to refresh the canonical accounts, analysis outputs and machine-readable tables. Then open or execute the notebooks separately. They may read these generated outputs and source/reference files needed for a specific analysis or map; they do not call `main.py` themselves.

> **Spatial econometrics, published version:** the rendered HTML of notebook 07 can be read without installing anything at
> <https://aurvl.github.io/NotebookSites/gcw-spatial-econometrics/07_spatial_econometrics.html>.

## Analytical deep dives

| Notebook | Focus |
| --- | --- |
| [`01_forest_account.ipynb`](01_forest_account.ipynb) | How forest area and Gibbs/GFW uptake rates combine within each biome to form GCW, how the annual flow is distributed across biomes, and how spatial rate dispersion differs from account uncertainty. |
| [`02_marine_account.ipynb`](02_marine_account.ipynb) | How marine ecosystem areas and rates form the physical coastal account and BCW; how the GMW–EEZ overlay and mangrove-area selection affect coverage and national results. |
| [`03_national_accounts.ipynb`](03_national_accounts.ipynb) | How GCW and BCW combine into NCW; account availability, concentration, national/territorial distributions, and geographic/economic profiles. |
| [`04_socioeconomic_emissions.ipynb`](04_socioeconomic_emissions.ipynb) | Coverage and distributions of emissions, GDP and population; the selected data years; and how the account balances and ratios are assembled. |
| [`05_deforestation_capacity.ipynb`](05_deforestation_capacity.ipynb) | The coverage and recency of FRA loss rates and how reported annual forest-area loss is valued as lost annual addition capacity. |
| [`06_climate_finance.ipynb`](06_climate_finance.ipynb) | The 2% GCW allocation scenario and the separate Busch forest-restoration supply/cost analysis, including coverage and sensitivity results. |
| [`07_spatial_econometrics.qmd`](07_spatial_econometrics.qmd) | Spatial patterns and model diagnostics across the study relationships and weight matrices. [Open the published HTML](https://aurvl.github.io/NotebookSites/gcw-spatial-econometrics/07_spatial_econometrics.html). |

Each deep dive introduces its analytical question and the relevant data, then examines the calculation through distributions, comparisons, plots and consistency checks. Outputs from notebooks 01–07 are displayed in the notebook or rendered document; they are not exported as separate analysis tables or figures. The spatial Quarto document reads model outputs prepared by the Python pipeline. Render it from the repository root with:

```powershell
quarto render code/notebooks/07_spatial_econometrics.qmd --to html --output-dir tmp/quarto-render
```

The Python notebooks can be executed from the repository root, for example:

```powershell
python -m nbconvert --to notebook --execute --inplace code/notebooks/01_forest_account.ipynb
```

## Presentation notebooks

| Notebook | Role and output |
| --- | --- |
| [`08_paper_figures.ipynb`](08_paper_figures.ipynb) | Standalone figure notebook. Its existing figure-export behaviour is unchanged; run it separately when refreshing the approved paper figures. |
| [`09_manuscript_tables.ipynb`](09_manuscript_tables.ipynb) | Previews the prepared manuscript tables and independently writes `results/tables/manuscript/Manuscript_tables.xlsx`. Run it after `main.py`. |

`main.py` produces the inputs to these presentation notebooks but does not execute any notebook, generate the workbook, or require figure exports. Notebook 09 reads the prepared CSVs; it does not rebuild them. The archived notebooks are retained for provenance and are not part of the current workflow.
