# Data

This directory separates source data, derived data used by the calculations, references, and processing logs.

```text
data/
  raw/
    environmental/forest/  FRA, GEZ, Gibbs/GFW, JRC, FAOSTAT, Pan
    environmental/marine/  BCW source account and GMW mangrove data
    economic/              national emissions, population, GDP, action-cost data
    geospatial/            country and EEZ boundaries
  reference/               transcribed published values and territory crosswalks
  metadata/                source registry and checksums
  derived/                 prepared data, account calculations, restoration results, draws, rasters, and diagnostics
  logs/                    processing logs where retained
```

All intermediate data produced by the analyses are kept under `derived/`. This includes the prepared inputs reused by later calculations, account calculations, restoration results, Monte Carlo draws, raster intermediates, and diagnostics. Manuscript-facing tables and figures are kept separately under `../results/`.

Raw files are not edited in place. Their source, release, access date, licence, and use are recorded in [`metadata/source_registry.csv`](metadata/source_registry.csv). Checksums for versioned raw files are in [`metadata/raw_checksums.csv`](metadata/raw_checksums.csv). Source-specific citation and licence requirements are described in [`../docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).

Files under `raw/` retain their provider's terms. Large raster tiles and the GMW polygon archive are excluded from Git; retrieval and verification instructions are in the data-source documentation and the root README.
