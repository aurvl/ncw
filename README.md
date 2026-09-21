# Natural Carbon Wealth (NCW) pipeline

Rebuilds, from untouched raw sources, the annual **Green Carbon Wealth** (GCW) of each country — forest CO2 uptake valued at the global social cost of carbon — and adds **Blue Carbon Wealth** (BCW) to obtain **Natural Carbon Wealth** (NCW).

- **Route B (main).** FRA 2025 forest area, split into three biomes harmonised with Pan et al. (2024) — tropical (incl. subtropical), temperate, boreal — using FAO GEZ 2010 × country polygons × JRC forest cover 2020, multiplied by one Pan rate per biome.
- **Route A (complementary).** FAOSTAT net forest CO2 flux, 2015–2024 (removals minus losses).
- **Uncertainty.** 20 000 Monte Carlo draws sharing the GSCC draws of BCW; every total is summed draw by draw.

Method: [`docs/METHODS.md`](docs/METHODS.md). Sources, licences and citations: [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Structure

```text
src/gcw/                     one module = one question = one table
  config.py                  paths, constants, documented parameters
  territories.py        ->   summary/territories.csv, bcw_territory_mapping.csv
  forest_areas.py       ->   summary/forest_areas.csv
  biome_shares.py       ->   summary/gez_area_by_country.csv, biome_shares.csv, biome_shares_fra.csv
  pan_rates.py          ->   summary/pan_biome_flux.csv, biome_rates.csv, pan_rate_checks.csv
  gscc.py               ->   summary/gscc_summary.csv
  forest_uptake_pan.py  ->   summary/forest_area_by_biome.csv, forest_uptake_pan.csv (+ draws)
  faostat_flux.py       ->   summary/faostat_forest_flux_annual.csv, forest_uptake_faostat.csv
  gcw.py                ->   output/country_level_gcw.csv (+ draws)
  ncw.py                ->   output/country_level_ncw.csv (+ draws), summary/bcw_draw_alignment.csv
  tables.py             ->   output/tables/table1 … table5
  checks.py             ->   output/validation/coverage.csv, biome_share_comparison.csv, global_checks.csv
  validation.py              shared helpers (IO, draw summaries, draw-wise sums)
scripts/
  main.py                    full pipeline
  build_summaries.py         utility tables only
  checksum_raw_sources.py    SHA-256 inventory of data_source/raw/
data_source/
  raw/                       untouched sources
  reference/                 transcribed values and validated crosswalk
  metadata/                  source registry and checksums
  summary/                   generated utility tables
output/                      generated country tables, paper tables, validation
tests/                       unit tests
docs/                        methods, sources and licences
```

## Run in GitHub Codespaces

1. **Code → Codespaces → ⋯ → New with options**, machine type **4-core / 16 GB**, **Create codespace**. The package installs automatically (`.devcontainer/devcontainer.json`).
2. In the terminal:

```bash
python -m pytest -q
python scripts/main.py --rasters
```

`--rasters` recomputes the GEZ × country × forest-mask table (a few minutes). Omit it when `data_source/summary/gez_area_by_country.csv` is up to date.

## Run elsewhere (Python ≥ 3.11)

```bash
git clone https://github.com/aurvl/ncw.git && cd ncw
python -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/main.py --rasters
```

Verify raw files: `python scripts/checksum_raw_sources.py --output check_checksums.csv`, then compare its `sha256` column with `data_source/metadata/raw_checksums.csv`.

## Read the results

1. `output/validation/global_checks.csv` — every line should be `ok`; `REVIEW` lines must be understood first.
2. `output/tables/` — `table1_global_by_ecosystem`, `table2_by_continent`, `table3_by_group`, `table4_top_territories`, `table5_route_a_faostat`.
3. `output/country_level_gcw.csv`, `output/country_level_ncw.csv` — one row per accounting unit.

Columns `*_mean`, `*_sd`, `*_p05`, `*_p50`, `*_p95` summarise the draws; `*_sd` is the spread of the value. Units: hectares, tCO2/yr, constant 2015 US$/yr.

## Licences

This repository follows the licensing of the companion blue carbon wealth repository
([`aurvl/bcw-paper-2025`](https://github.com/aurvl/bcw-paper-2025)):

- code: MIT, see [`LICENSE`](LICENSE);
- data and documentation produced here: CC BY 4.0, see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0).

Each raw source keeps its own licence (FAO, Marine Regions and BCW: CC BY 4.0; JRC: free use with citation; Pan et al. values cited from *Nature*). See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the required citations.
