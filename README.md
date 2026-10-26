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

<p align="center">
  <img src="docs/figures/ncw-workflow.svg" alt="Workflow from source data to national carbon wealth and paper outputs" width="70%" style="border-radius: 4px;"><br>
  <em>Repository workflow. Source-specific physical measures and assumptions remain documented separately.</em>
</p>

## Study accounts

- **Forest account.** Annual carbon additions to above- and below-ground living forest biomass are estimated using Gibbs/GFW gross-removal pixels for 2001-2023. Four non-mangrove mean rates are calculated for the tropical, subtropical, temperate, and boreal FAO GEZ domains and applied to FRA 2025 forest area allocated by biome. This measure does not include forest soils, deadwood, or the net ecosystem carbon balance.
- **Marine account.** Published Blue Carbon Wealth (BCW) components are combined with a spatial update of mangrove area from Global Mangrove Watch 2025. The update changes mangrove area; the other BCW components and source-specific rates are retained.
- **National account.** Green Carbon Wealth (GCW) and Blue Carbon Wealth (BCW) are combined as Natural Carbon Wealth (NCW). The primary uncertainty draws propagate the GSCC draws. Spatial variation in Gibbs/GFW pixels is reported as a separate sensitivity, not as a confidence interval for the biome rates.
- **Complementary analyses.** FAOSTAT forest flux, deforestation-related capacity loss, a 2% GCW allocation scenario, the Busch et al. reforestation action-cost comparison ([2024](https://doi.org/10.1038/s41558-024-02068-1)), and spatial model sequences are retained as separately documented analyses.

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
│   ├── derived/                   reusable intermediate tables
│   └── logs/                      source-processing logs
├── code/
│   ├── src/gcw/                   reusable calculation and validation modules
│   ├── scripts/                   pipeline, rebuild, audit, and analysis entry points
│   ├── notebooks/                 figures, analysis, and manuscript-output notebooks
│   └── tests/                     pipeline unit tests
├── results/
│   ├── country_level_gcw.csv      country and territory forest account
│   ├── country_level_ncw.csv      combined country-level account
│   ├── tables/                    paper and supplementary tables
│   ├── figures/                   paper figures, supplementary figures and reviewed alternatives
│   └── validation/                checks, inventories, and analysis diagnostics
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
| Rebuild the full country accounts | [`code/scripts/main.py`](code/scripts/main.py) | `results/country_level_gcw.csv`, `results/country_level_ncw.csv` |
| Recalculate Gibbs/GFW biome rates | [`code/scripts/build_gfw_rates.py`](code/scripts/build_gfw_rates.py) | `data/derived/gfw_gibbs_biome_rates_non_mangrove.csv` |
| Inspect the forest calculation | `code/src/gcw/forest_areas.py`, `biome_shares.py`, `gfw_rates.py`, `forest_uptake_gfw.py` | `data/derived/` |
| Rebuild account tables and checks | `code/src/gcw/gcw.py`, `ncw.py`, `tables.py`, `checks.py` | `results/` |
| Reproduce the spatial sequence | [`code/scripts/run_spatial_full_sequence.py`](code/scripts/run_spatial_full_sequence.py) | `results/validation/spatial_emissions_2024_model_selection_evidence.csv` |
| Run the 2024 emissions extension | [`code/scripts/run_spatial_emissions_extension.py`](code/scripts/run_spatial_emissions_extension.py) | `results/validation/` |
| Compare climate-finance approaches | [`code/scripts/compare_finance_and_action_costs.py`](code/scripts/compare_finance_and_action_costs.py) | `results/validation/` |
| Build Figure 4 finance data | [`code/scripts/build_finance_figure4.py`](code/scripts/build_finance_figure4.py) | `results/tables/manuscript/Supplementary_Figure4_*.csv` and `results/validation/finance_figure4_summary.json` |

The reusable calculation modules in `code/src/gcw/` are the source of truth. Scripts call those modules. Notebooks are used for analysis and figures, not as hidden replacements for the pipeline.

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

For a quick rebuild using the committed four-biome Gibbs/GFW rate table and cached biome allocation, run:

```bash
python code/scripts/main.py --reuse-gfw-rates
```

To recompute the Gibbs/GFW rates from the published tiles, run `python code/scripts/build_gfw_rates.py --forest-type-dir data/raw/environmental/forest/gfw_gibbs_2025/forest_type`, then run `python code/scripts/main.py --reuse-gfw-rates`. This uses the non-mangrove rate table just produced, without processing the tiles a second time. Add `--rasters` to the second command to recompute the GEZ x country x JRC forest-mask allocation as well. Without `--rasters`, the pipeline uses the cached allocation in `data/derived/`.

### Large source files

> [!IMPORTANT]
> Recomputing the Gibbs/GFW biome rates requires both raster tile sets, about 46 GB compressed in total. These files are not stored in Git. The quick account rebuild can instead reuse the committed rate table and does not require these downloads.

The 272 Gibbs/GFW gross-removal GeoTIFF tiles and 272 matching forest-type tiles are large downloads and are not stored in Git. The rate-building workflow downloads and verifies them with `code/scripts/download_gfw_dataverse.py` and `code/scripts/download_gfw_forest_types.py`. The compressed gross-removal set is about 37 GB; the forest-type set is about 9 GB. Place them under:

```text
data/raw/environmental/forest/gfw_gibbs_2025/gross_removals/
data/raw/environmental/forest/gfw_gibbs_2025/forest_type/
```

Then use `python code/scripts/build_gfw_rates.py --forest-type-dir data/raw/environmental/forest/gfw_gibbs_2025/forest_type --workers 2`. Increase the worker count only when memory permits. The GMW polygon archive is also large and is excluded from Git; download, checksum, and overlay instructions are in [`docs/GMW_GCW_VALUATION_AND_ABATEMENT_SCENARIOS.md`](docs/GMW_GCW_VALUATION_AND_ABATEMENT_SCENARIOS.md).

## Results and manuscript material

| Path | Contents |
| --- | --- |
| `results/country_level_gcw.csv` | Forest account by accounting unit |
| `results/country_level_ncw.csv` | Combined forest and marine account by unit |
| `results/tables/manuscript/` | Current Tables 1-4 and supplementary tables, including the full 2024 country accounts and mangrove audit |
| `code/notebooks/08_paper_figures.ipynb` | Paper figures and supplementary visual diagnostics generated from the current canonical account and analysis outputs |
| `results/figures/Candidate_Figure*` and `results/figures/Alternative_original_Figure*` | Optional PNG/PDF exports when `SAVE_FIGURES` is enabled after visual review |
| `results/tables/manuscript/Supplementary_country_level_accounts_2024.csv` | Canonical 267-unit Results table; `UNIT_CODE` is the study-unit key, `ISO3` is validated where available, and `region` names the analytical geographic grouping |
| `results/validation/country_level_results_master.csv` | Full calculation master used by the artifact builder; legacy comparison fields are filtered from paper-facing outputs |

The validation folder also contains intermediate audits and local rendering checks. Those files are not all manuscript outputs.

Superseded manuscript figure and table exports are retained under `results/archive/legacy_manuscript_2026-10-19/` for audit only. They are not used by the current notebooks or canonical tables.

Build the current paper tables from canonical outputs with:

```bash
python code/scripts/build_manuscript_artifacts.py --tables-only
```

Run `code/notebooks/08_paper_figures.ipynb` for the manuscript figures and explicitly labelled supplementary diagnostics. It reads the current canonical tables and analysis outputs; it does not replace the account pipeline. Figure 4 displays the stipulated 2% allocation scenario together with the reconstructed Busch reforestation comparison. The provisional minimum-BIC spatial chart remains separate until the researcher records final model choices. The R/Quarto notebook `code/notebooks/07_spatial_econometrics.qmd` reviews the nine spatial relationships; rendering it requires R, knitr and Quarto. Its upstream model fits are generated by the documented Python pipeline.

## Data, licensing, and citation

- Code: MIT, see [`LICENSE`](LICENSE).
- Project-produced data and documentation: CC BY 4.0, see [`LICENSE-CCBY40.md`](LICENSE-CCBY40.md).
- Source datasets retain their own licences and citation requirements. See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).
- Repository citation metadata: [`CITATION.cff`](CITATION.cff).

Please cite the associated manuscript when using its research results, and cite the original data sources listed in the data documentation.
