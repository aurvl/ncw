# Data sources and canonical schemas

## Principle

Raw files are immutable. Every transformation must have a script, a named output and a validation report.

## Required sources

### FAOSTAT forest flux — primary baseline

Download the FAOSTAT *Emissions from forests (Global, National - Annual)* CSV from the [official catalog](https://data.fao.org/catalog/dataset/0462095d-242c-4540-a030-03e31a2a4a1e). It covers 1990–2025, reports CO2 emissions/removals from forest land and is derived from FRA 2025 activity data under the 2006 IPCC Guidelines. Store the untouched file under `data_source/raw/faostat/`.

The standardization step must write `data_source/interim/faostat_forest_flux.csv` with:

```text
iso3,country_name,year,forest_uptake_tco2,source_item,source_element,source_unit,source_file
```

`forest_uptake_tco2` is positive for atmospheric removal. The script must explicitly document the original sign convention and the exact FAOSTAT Item and Element selected.

### FRA 2025 — forest structure diagnostics

Use the [FRA platform](https://fra-data.fao.org/assessments/fra/2025/WO/home/) for forest area, naturally regenerated forest, planted forest, carbon stocks and mangrove checks. FRA supports diagnostics and the Pan-area-rate estimator; it is not silently substituted for the annual national flow in the FAOSTAT baseline.

### Pan et al. (2024) — benchmark and sensitivity estimator

The paper states that its replication spreadsheets are available at [US Forest Service Research Data Archive RDS-2023-0051](https://doi.org/10.2737/RDS-2023-0051). Nature also provides source data for its figures and extended data. Store each download with a separate registry entry.

Create two interim tables only after inspecting the source schema:

```text
# pan_biome_rates.csv
biome,forest_class,period_start,period_end,uptake_mean_tc_ha_yr,uptake_sd_tc_ha_yr,source_table,assumption_note

# forest_area_by_biome.csv
iso3,country_name,biome,forest_class,area_ha,area_year,source_file,source_row
```

Do not equate FAO naturally regenerated forest with Pan intact forest, nor FAO planted forest with Pan regrowth forest, without preserving that choice as a sensitivity assumption.

### BCW country data and GSCC draws

Use the final `country_level_bcw.csv` and `draws.npz` from the [BCW repository](https://github.com/aurvl/bcw-paper-2025). Keep the raw files unchanged under `data_source/raw/bcw/`. They supply the territorial, socioeconomic and uncertainty reference for NCW.

## Additional collected sources

Collected broadly on 2026-09-16; unused sources will be removed before the repository is published. See `data_source/metadata/source_registry.csv` for URLs and versions, and `data_source/metadata/raw_checksums.csv` for SHA-256 checksums (regenerate with `python scripts/checksum_raw_sources.py` after any new download).

- `raw/faostat/Inputs_LandUse_*`: FAOSTAT annual forest area.
- `raw/gez/gez2010.zip`: FAO Global Ecological Zones 2010 shapefile, for forest area by biome.
- `raw/m49/`: UNSD M49 page snapshot, provenance of `reference/m49_to_iso3.csv`.
- `raw/wdi/`: World Bank GDP deflator.
- `raw/bcw/data_source/`: BCW inputs (GSCC database and draws, economy tables, coastal ecosystem areas).

### Manual downloads

1. Pan et al. replication data: open https://doi.org/10.2737/RDS-2023-0051 in a browser, download the archive into `raw/pan/`.
