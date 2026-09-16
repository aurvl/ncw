# Green Carbon Wealth (GCW) and Natural Carbon Wealth (NCW) pipeline

This repository rebuilds, from untouched raw sources, the annual Green Carbon Wealth of each country (forest CO2 uptake valued at the global social cost of carbon) and combines it with Blue Carbon Wealth (BCW) into Natural Carbon Wealth (NCW).

- **Route B — main (Pan area × rate).** FRA 2025 forest areas (NRF, planted, mangroves removed) are split into biomes with FAO GEZ 2010 × EEZ_land_union v4 × JRC GFC2020 forest mask, then multiplied by per-hectare rates derived from Pan et al. (2024, Table 1, 2010–2019). Same logic as BCW.
- **Route A — complementary (FAOSTAT net flux).** Country-reported net forest CO2 flux, 2015–2024 mean. Removals minus losses; can be negative.
- **Uncertainty.** Monte Carlo with the 20 000 GSCC draws of the BCW release; every aggregate is summed draw by draw.

Every subjective choice is documented, with its alternatives, in `MYCHOICES.md` (kept outside the repository, next to the manuscript).

## Structure

```text
src/gcw/                     one module = one question = one table
  config.py                  paths, constants, documented parameters
  territories.py        ->   data_source/summary/territories.csv
  forest_areas.py       ->   data_source/summary/forest_areas.csv
  biome_shares.py       ->   data_source/summary/gez_area_by_country.csv, biome_shares.csv, biome_shares_fra.csv
  pan_rates.py          ->   data_source/summary/pan_biome_flux.csv, biome_rates.csv
  gscc.py               ->   data_source/summary/gscc_summary.csv
  forest_uptake_pan.py  ->   data_source/summary/forest_area_by_biome.csv, forest_uptake_pan.csv (+ draws)
  faostat_flux.py       ->   data_source/summary/faostat_forest_flux_annual.csv, forest_uptake_faostat.csv
  gcw.py                ->   output/country_level_gcw.csv (+ draws)
  ncw.py                ->   output/country_level_ncw.csv (+ draws), summary/bcw_draw_alignment.csv
  tables.py             ->   output/tables/table1…table5
  checks.py             ->   output/validation/coverage.csv, biome_share_comparison.csv, global_checks.csv
  validation.py              shared helpers (IO, draw summaries, draw-wise sums)
scripts/
  build_summaries.py         runs the utility modules (summaries only)
  main.py                    full pipeline: summaries -> GCW -> NCW -> tables -> checks
  checksum_raw_sources.py    SHA-256 inventory of data_source/raw/
data_source/
  raw/                       untouched downloads (see metadata/source_registry.csv)
  metadata/                  source registry and checksums
  reference/                 documented assumptions (subtropical rate)
  summary/                   generated utility tables
output/                      generated country tables, paper tables, validation
tests/                       unit tests
```

## Running in GitHub Codespaces

1. On https://github.com/aurvl/ncw: **Code > Codespaces > ⋯ > New with options**, machine type **4-core / 16 GB**, then **Create codespace**.
2. Wait for the container build; `.devcontainer/devcontainer.json` installs the package automatically.
3. In the terminal:

```bash
python -m pytest -q
python scripts/main.py --rasters
```

4. Download results: right-click `output/` in the Explorer > **Download**, or commit them on a branch.

## Running on another machine

### 1. Copy the project

Clone the repository (raw sources are versioned, ~170 MB) or copy the `repo/` folder. Then verify the raw files:

```bash
python scripts/checksum_raw_sources.py --output check_checksums.csv
```

and compare `check_checksums.csv` with `data_source/metadata/raw_checksums.csv` (the `sha256` columns must be identical).

### 2. Create the environment (Python ≥ 3.11)

Linux / macOS:

```bash
cd repo
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows (PowerShell):

```powershell
cd repo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Google Colab: upload the zipped `repo/` folder, then

```python
!unzip -q repo.zip && %cd repo
!pip install -q -e ".[dev]"
```

### 3. Run the tests

```bash
python -m pytest -q
```

### 4. Run the pipeline

```bash
python scripts/main.py --rasters
```

`--rasters` computes the GEZ × boundaries × forest mask table (slowest step, a few minutes; ~1 GB RAM is comfortable). Later runs can omit it: the cached `data_source/summary/gez_area_by_country.csv` is reused.

To produce only the utility tables:

```bash
python scripts/build_summaries.py --rasters
```

### 5. Read the results

1. `output/validation/global_checks.csv` — every line should be `ok`; `REVIEW` lines must be understood before using results.
2. `output/tables/table1_global_by_ecosystem.csv` — world totals per ecosystem, GCW, BCW, NCW.
3. `output/tables/table2_by_continent.csv`, `table3_by_group.csv`, `table4_top_territories.csv`, `table5_route_a_faostat.csv`.
4. `output/country_level_gcw.csv` and `output/country_level_ncw.csv` — one row per territory.

Columns `*_mean`, `*_sd`, `*_p05`, `*_p50`, `*_p95` summarise the Monte Carlo draws. `*_sd` is the spread of the value, not the Monte Carlo standard error of the mean (the BCW `_se` columns are sd / √B).

## Units

- Areas: hectares (FRA values are in 1000 ha in the raw files).
- Flows: tCO2/yr (Pan fluxes are Pg C/yr, converted with 44/12).
- Values: constant 2015 US$ per year; GSCC mean 559.6 US$2015/tCO2.

## Scientific boundary

GCW and NCW are annual welfare contributions of carbon sinks. They are not stock values, market prices, finance needs or additional mitigation.
