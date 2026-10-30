# Forest and ocean carbon sinks underpin national wealth

<p align="center">
  <img src="https://img.shields.io/badge/Forest_carbon-166534?style=for-the-badge" alt="Forest carbon">
  <img src="https://img.shields.io/badge/Marine_carbon-0E7490?style=for-the-badge" alt="Marine carbon">
  <img src="https://img.shields.io/badge/Natural_wealth-4F46E5?style=for-the-badge" alt="Natural wealth">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11 or newer">
  <a href="LICENSE"><img src="https://img.shields.io/badge/Code-MIT-111827?style=for-the-badge" alt="MIT licensed code"></a>
  <a href="LICENSE-CCBY40.md"><img src="https://img.shields.io/badge/Data_and_docs-CC_BY_4.0-7C3AED?style=for-the-badge" alt="CC BY 4.0 data and documentation"></a>
</p>

**Data and code for the national natural carbon wealth study.**

Associated manuscript: *Forest and ocean carbon sinks underpin national wealth as deforestation may concentrate burdens in poorer countries*.
Authors: Nathalie Hilmi, Maria-Sophia Chondrou, Loua Aurel De Vince Vehi, Ibrahim Issifu, and Fabio Berzaghi.

## Purpose

The study values the carbon that forests and coastal and ocean ecosystems remove each year, country by country, and combines the two into **Natural Carbon Wealth** (NCW). It then asks how this wealth relates to national economies and emissions, how deforestation erodes it, and what restoring the lost capacity would cost. This repository holds the source data, the code that rebuilds every account and analysis, and the resulting tables.

<p align="center">
  <img src="docs/figures/ncw-workflow.svg" alt="Workflow from source data to national carbon wealth and paper outputs" width="70%" style="border-radius: 4px;"><br>
  <em>Repository workflow.</em>
</p>

## Data and methods

- **Green Carbon Wealth (GCW).** Annual carbon additions to living forest biomass, from Gibbs/GFW gross-removal rates by climate domain applied to FRA 2025 forest area, and valued with the social cost of carbon.
- **Blue Carbon Wealth (BCW).** The published blue-carbon account (mangroves, seagrass, saltmarsh, open-ocean biological pump), with mangrove area updated from Global Mangrove Watch 2025.
- **NCW** is the sum of GCW and BCW. Uncertainty ranges propagate the social-cost-of-carbon draws.
- **Analyses.** Lost forest capacity from FRA deforestation, a hypothetical allocation of 2% of GCW, forest-restoration costs computed from the cell-level inputs of Busch et al. (2024), and spatial models of the links between carbon wealth, economies, and emissions.

> [!NOTE]
> GCW and BCW share a monetary valuation, but their physical inputs follow source-specific definitions. Check the account boundaries before comparing carbon quantities.

The equations and every processing step are in [`docs/PIPELINE.md`](docs/PIPELINE.md) (French: [`docs/PIPELINE_FR.md`](docs/PIPELINE_FR.md)). Sources, versions, and licences are in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Repository layout

| Folder | Contents |
| --- | --- |
| `data/` | Raw sources, reference crosswalks, and derived intermediates ([README](data/README.md)) |
| `code/` | Calculation modules, pipeline scripts, notebooks, and tests ([README](code/README.md)) |
| `results/` | Study tables and paper figures ([README](results/README.md)) |
| `web/` | Interactive web explorer of the results ([README](web/README.md)) |
| `docs/` | Pipeline description and data sources |

## Reproduce

Python 3.11 or newer and [Git LFS](https://git-lfs.com) (for the uncertainty draws) are required.

```bash
git clone https://github.com/aurvl/ncw.git && cd ncw
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,spatial]"
python code/scripts/main.py
```

`main.py` rebuilds the accounts, analyses, and study tables from the prepared data in `data/derived/`, without downloading anything. Notebooks run separately afterwards (see [`code/notebooks/README.md`](code/notebooks/README.md)). Main options:

- `--accounts-only` stops after the central accounts and their checks;
- `--skip-web` leaves the web explorer data unchanged;
- `--rebuild-derived` downloads the large sources below and rebuilds the derived data before the tables.

### Large source files

These sources are not stored in Git and are not needed for the standard run, which uses the prepared results already in `data/derived/`. For a full rebuild, each command below downloads its source, verifies it, and stores it in the folder shown (excluded from Git) before recalculating:

| Source | Size | Downloaded to | Command |
| --- | --- | --- | --- |
| Gibbs/GFW removal and forest-type tiles | ~46 GB | `data/raw/environmental/forest/gfw_gibbs_2025/` | `python code/scripts/rebuild_gibbs_gfw_pipeline.py` |
| Global Mangrove Watch 2025 polygons | GeoPackage archive | `data/raw/environmental/marine/gmw/` | `python code/scripts/rebuild_gmw_2025_pipeline.py` |
| Busch et al. cell inputs (`08_input_dtas.zip`) | 12.4 GB | `data/raw/economic/busch_2024/` | `python code/scripts/rebuild_busch_pipeline.py` |

## Web explorer

`web/` is a static site that shows the accounts on an interactive globe, published at <https://aurvl.github.io/ncw/>. `main.py` refreshes its data in `web/public/data/` at the end of each run; pass `--skip-web` to keep the current data.

## Licence and citation

Code is under MIT ([`LICENSE`](LICENSE)); project data and documentation are under CC BY 4.0 ([`LICENSE-CCBY40.md`](LICENSE-CCBY40.md)). Source datasets keep their own terms (see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)). Cite the associated manuscript and the original data sources; citation metadata is in [`CITATION.cff`](CITATION.cff).
