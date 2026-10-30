# Forest and ocean carbon sinks underpin national wealth

<p align="center">
  <img src="https://img.shields.io/badge/Forest_carbon-166534?style=for-the-badge" alt="Forest carbon">
  <img src="https://img.shields.io/badge/Marine_carbon-0E7490?style=for-the-badge" alt="Marine carbon">
  <img src="https://img.shields.io/badge/Natural_wealth-4F46E5?style=for-the-badge" alt="Natural wealth">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11 or newer">
  <a href="LICENSE"><img src="https://img.shields.io/badge/Code-MIT-111827?style=for-the-badge" alt="MIT licensed code"></a>
  <a href="LICENSE-CCBY40.md"><img src="https://img.shields.io/badge/Data_and_docs-CC_BY_4.0-7C3AED?style=for-the-badge" alt="CC BY 4.0 data and documentation"></a>
</p>

**Research code, source data, derived accounts, and analysis outputs for the national natural carbon wealth study.**

Associated manuscript: *Forest and ocean carbon sinks underpin national wealth as deforestation may concentrate burdens in poorer countries*.

Authors: Nathalie Hilmi, Maria-Sophia Chondrou, Loua Aurel De Vince Vehi, Ibrahim Issifu, and Fabio Berzaghi.

This repository rebuilds country-level forest and marine carbon accounts and combines them into **Natural Carbon Wealth** (NCW). It also contains analyses of forest capacity loss, climate-finance scenarios, and spatial relationships.

## Current mangrove-method refresh

On 23 October 2026, the FRA 2025 mangrove Forest/OWL audit was propagated through the complete computational chain. The main accounts, validation tables, manuscript tables and supplementary outputs were regenerated from the FRA-first rule: only mangrove area documented as Forest is removed from the FRA forest allocation; documented Other wooded land and Remaining land are kept separate; unresolved Forest/OWL shares remain explicit rather than being imputed. The GMW--JRC spatial overlap is retained as a separate sensitivity test and is not used in the main accounts. The manuscript DOCX itself was not edited automatically; its tables and supporting outputs were refreshed for author review.

On 27 October 2026, the primary BCW mangrove-area candidate was changed to a direct GIS intersection of GMW 2025 polygons with EEZ `UNION` geometries. The intersection area is measured in Mollweide, mapped to study units through the EEZ crosswalk, and corrected by GMW's published global factor 0.9775. The selected area follows this order: positive corrected GMW 2025 area, reported FRA 2025 area (including a declared zero), the area reported in the prior account, then missing when no area is available. GMW 2024 and 2023 national statistics are not used because they cannot be spatially assigned to study units with the same EEZ overlay.

<p align="center">
  <img src="docs/figures/ncw-workflow.svg" alt="Workflow from source data to national carbon wealth and paper outputs" width="70%" style="border-radius: 4px;"><br>
  <em>Repository workflow. Source-specific physical measures and assumptions remain documented separately.</em>
</p>

## Study accounts

- **Forest account.** Annual carbon additions to above- and below-ground living forest biomass are estimated using Gibbs/GFW gross-removal pixels for 2001-2023. Four non-mangrove mean rates are calculated for the tropical, subtropical, temperate, and boreal FAO GEZ domains and applied to FRA 2025 forest area allocated by biome. This measure does not include forest soils, deadwood, or the net ecosystem carbon balance.
- **Marine account.** Published Blue Carbon Wealth (BCW) components are combined with a spatial update of mangrove area from Global Mangrove Watch 2025. The update changes mangrove area; the other BCW components and source-specific rates are retained.
- **National account.** Green Carbon Wealth (GCW) and Blue Carbon Wealth (BCW) are combined as Natural Carbon Wealth (NCW). The primary uncertainty draws propagate the GSCC draws. Spatial variation in Gibbs/GFW pixels is reported as a separate sensitivity, not as a confidence interval for the biome rates.
- **Complementary analyses.** FAOSTAT forest flux, deforestation-related capacity loss, a 2% GCW allocation scenario, Busch-based forest-restoration costs, and spatial model sequences are retained as separately documented analyses.

See [`docs/METHODS.md`](docs/METHODS.md), [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md), and [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) for definitions, sources, and checks.

> [!NOTE]
> GCW, BCW, and NCW share a monetary valuation framework, but their physical inputs use source-specific definitions. Read the boundary for each account in the Methods before comparing carbon quantities; a common currency does not make the underlying fluxes physically identical.

<details>
<summary><strong>Repository map</strong></summary>


```text
.
├── data/
│   ├── raw/
│   │   ├── environmental/forest/  FRA, GEZ, Gibbs/GFW, JRC, FAOSTAT, Pan
│   │   ├── environmental/marine/  BCW and Global Mangrove Watch
│   │   ├── economic/              emissions, population, GDP, action-cost data
│   │   └── geospatial/            country and EEZ boundaries
│   ├── reference/                 transcribed values and crosswalks
│   ├── metadata/                  source registry and raw-file checksums
│   ├── derived/                   prepared inputs, account results, restoration products, draws, rasters, and diagnostics
│   └── logs/                      source-processing logs
├── code/
│   ├── src/gcw/                   reusable calculation and validation modules
│   ├── scripts/                   pipeline, rebuild, audit, and analysis entry points
│   ├── notebooks/                 figures, analysis, and manuscript-output notebooks
│   └── tests/                     pipeline unit tests
├── results/
│   ├── tables/                    paper and supplementary tables
│   ├── figures/                   paper figures, supplementary figures and reviewed alternatives
│   └── archive/                   superseded manuscript-facing exports
├── docs/                          methods and data provenance
├── .github/                       automated tests and repository workflows
├── CITATION.cff                   repository citation metadata
├── LICENSE                        MIT licence for code
└── LICENSE-CCBY40.md              CC BY 4.0 terms for project data and documentation
```

</details>

### Where to start

| Task | Main entry point | Main output or guide |
| --- | --- | --- |
| Rebuild the accounts, analyses and machine-readable tables | [`code/scripts/main.py`](code/scripts/main.py) | Working accounts and analysis artifacts under `data/derived/`; manuscript tables under `results/tables/` |
| Recalculate Gibbs/GFW biome rates | [`code/scripts/build_gfw_rates.py`](code/scripts/build_gfw_rates.py) | `data/derived/gibbs_gfw/gfw_gibbs_biome_rates_non_mangrove.csv` |
| Inspect the forest calculation | `code/src/gcw/forest_areas.py`, `biome_shares.py`, `gfw_rates.py`, `forest_uptake_gfw.py` | `data/derived/` inputs and `data/derived/forest_account/` results |
| Rebuild account tables and checks | `code/src/gcw/gcw.py`, `ncw.py`, `tables.py`, `checks.py` | `data/derived/accounts/`, `data/derived/draws/`, and `data/derived/validation/` |
| Reproduce the spatial sequence | [`code/scripts/run_spatial_full_sequence.py`](code/scripts/run_spatial_full_sequence.py) | `data/derived/validation/spatial_emissions_2024_model_selection_evidence.csv` |
| Run the 2024 emissions extension | [`code/scripts/run_spatial_emissions_extension.py`](code/scripts/run_spatial_emissions_extension.py) | `data/derived/validation/` |
| Compare climate-finance approaches | [`code/scripts/compare_finance_and_action_costs.py`](code/scripts/compare_finance_and_action_costs.py) | `data/derived/validation/` |
| Build historical Figure 4 finance data (superseded published-curve comparison) | [`code/scripts/build_finance_figure4.py`](code/scripts/build_finance_figure4.py) | Historical outputs only; not used by the current Busch calculation pipeline |

The reusable account modules in `code/src/gcw/` calculate GCW and NCW. `main.py` runs data preparation, account calculations, analyses, validations, and machine-readable table builders. Generated analytical intermediates go to `data/derived/`; manuscript-facing tables and figures go to `results/`. The notebooks are independent deep dives: they read the prepared results and may also read source/reference files needed for their analyses or maps. Run them separately after `main.py`.

## Reproduce the project

### Local installation

Python 3.11 or newer is required.

```bash
git clone https://github.com/aurvl/ncw.git
cd ncw
python -m venv .venv
```

Activate the environment, then install and run the checks:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev,spatial]"
python -m pytest -q
```

For a full rebuild of the current paper outputs, run:

```bash
python code/scripts/main.py
```

By default, the command reuses the prepared data versioned under `data/derived/`; it does not download or recompute large source datasets. It updates the accounts, validation outputs, deforestation and socioeconomic analyses, spatial results, and manuscript-facing CSV tables. It does not execute notebooks, build the manuscript workbook, or export paper figures. Use `--accounts-only` for the central accounts and checks. To download and rebuild the derived data from the large source datasets before updating the accounts and tables, run `python code/scripts/main.py --rebuild-derived`. This option is off by default. It rebuilds the GMW 2025 polygon-to-EEZ overlay, Gibbs/GFW rates and forest raster allocation, and the Busch cell reconstruction. These source stages are available as separate commands: `rebuild_gmw_2025_pipeline.py`, `rebuild_gibbs_gfw_pipeline.py`, `rebuild_forest_raster_allocation.py`, and `rebuild_busch_pipeline.py`. `--recompute-gfw-rates` recalculates Gibbs/GFW rates from tiles that are already present locally; `--rasters` rebuilds only the GEZ x country x JRC forest-mask allocation.

### Large source files

> [!IMPORTANT]
> Recomputing the Gibbs/GFW biome rates requires both raster tile sets, about 46 GB compressed in total. The source rasters are not stored in Git. The compact generated rate table is versioned under `data/derived/gibbs_gfw/`, so an account rebuild can reuse it without processing the rasters again.

The reusable Monte Carlo draw arrays in `data/derived/` are tracked with Git LFS. Install Git LFS before cloning, or run `git lfs install` followed by `git lfs pull` in the repository after cloning.

The 272 Gibbs/GFW gross-removal GeoTIFF tiles and 272 matching forest-type tiles are large downloads and are not stored in Git. The rate-building workflow downloads and verifies them with `code/scripts/download_gfw_dataverse.py` and `code/scripts/download_gfw_forest_types.py`. The compressed gross-removal set is about 37 GB; the forest-type set is about 9 GB. Place them under:

```text
data/raw/environmental/forest/gfw_gibbs_2025/gross_removals/
data/raw/environmental/forest/gfw_gibbs_2025/forest_type/
```

From the repository root, download, verify, aggregate, then reuse the four-biome CSV:

```bash
python code/scripts/rebuild_gibbs_gfw_pipeline.py --download-workers 8 --processing-workers 2
python code/scripts/main.py --reuse-gfw-rates
```

The dedicated Gibbs/GFW pipeline downloads the two 272-tile source collections, verifies them, computes biome rates, and writes compact rate tables plus a source/output manifest under `data/derived/gibbs_gfw/`. The source GeoTIFFs remain outside Git. Use `python code/scripts/rebuild_gibbs_gfw_pipeline.py` to run this stage independently. The GMW archive is also excluded from Git; `python code/scripts/rebuild_gmw_2025_pipeline.py` downloads and verifies it before overlaying it with the EEZ units. Increase the Gibbs/GFW worker count only when memory permits.

The Busch restoration scenario is calculated from the public country-level cell inputs and the authors' modelling framework; the resulting costs and curves are our calculations. The pipeline processes every country `.dta` file in the archive before joining any positive FRA-loss targets. It keeps all country-cost outputs under `data/derived/busch_reconstruction/`; the separate coverage file records the later ISO3 join for positive-loss study entities. Published national curves are not loaded or compared. The workbook contributes only the shared price-threshold grid. Country parameters and constants transcribed from the Stata program are in `code/scripts/busch_stata_parameters.py` and `code/scripts/rebuild_busch_country_finance.py`. `python code/scripts/rebuild_busch_pipeline.py` downloads the 12.4 GB `08_input_dtas.zip` archive to `.tmp/busch_08_reconstruction/` outside Git, verifies its size and MD5, calculates all country inputs and writes the derived outputs. `main.py --rebuild-derived` runs this stage as part of the full rebuild.

## Results and manuscript material

| Path | Contents |
| --- | --- |
| `data/derived/accounts/country_level_gcw.csv` | Working forest account by entity |
| `data/derived/accounts/country_level_ncw_accounts.csv` | Core calculated forest-plus-marine account by entity; pipeline input for downstream tables |
| `results/tables/manuscript/` | Current Tables 1-4 and supplementary tables, including the full 2024 country accounts and mangrove audit |
| `code/notebooks/08_paper_figures.ipynb` | Paper figures and supplementary visual diagnostics generated from the current canonical account and analysis outputs |
| `results/figures/Candidate_Figure*` and `results/figures/Alternative_original_Figure*` | Optional PNG/PDF exports when `SAVE_FIGURES` is enabled after visual review |
| `results/tables/manuscript/Supplementary_country_level_accounts_2024.csv` | Canonical study-unit Results table; `UNIT_CODE` is the study-unit key, `ISO3` is validated where available, and `region` names the analytical geographic grouping |
| `data/derived/validation/country_level_results_master.csv` | Full calculation master used by the artifact builder; legacy comparison fields are filtered from paper-facing outputs |

Analytical checks and model diagnostics are written under `data/derived/validation/`, not alongside the manuscript tables.

[`code/notebooks/09_manuscript_tables.ipynb`](code/notebooks/09_manuscript_tables.ipynb) independently previews the generated manuscript tables and writes `results/tables/manuscript/Manuscript_tables.xlsx`. The narrower account table produced by `main.py` remains in `data/derived/accounts/country_level_ncw_accounts.csv`.

Superseded manuscript figure and table exports are retained under `results/archive/legacy_manuscript_2026-10-19/` for audit only. They are not used by the current notebooks or canonical tables.

Build the current paper tables from canonical outputs with:

```bash
python code/scripts/build_manuscript_artifacts.py --tables-only
```

[`code/notebooks/08_paper_figures.ipynb`](code/notebooks/08_paper_figures.ipynb) is run separately to display the figures and save its approved figure files. Figure 5 uses the cell-level Busch reconstruction; when a refresh is needed, `main.py` verifies the inputs and downloads the public DTA archive to scratch space outside Git. The R/Quarto notebook `code/notebooks/07_spatial_econometrics.qmd` reviews the spatial relationships; its prepared model outputs are generated by the Python pipeline and the document is rendered separately.

## Data, licensing, and citation

- Code: MIT, see [`LICENSE`](LICENSE).
- Project-produced data and documentation: CC BY 4.0, see [`LICENSE-CCBY40.md`](LICENSE-CCBY40.md).
- Source datasets retain their own licences and citation requirements. See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).
- Input periods are listed in [`data/metadata/account_variable_vintages.csv`](data/metadata/account_variable_vintages.csv); added source files have SHA-256 values in [`data/metadata/paper_extension_source_checksums.csv`](data/metadata/paper_extension_source_checksums.csv).
- Repository citation metadata: [`CITATION.cff`](CITATION.cff).

Please cite the associated manuscript when using its research results, and cite the original data sources listed in the data documentation.
