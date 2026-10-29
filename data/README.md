# Data

This directory separates downloaded inputs, prepared analysis inputs, and generated outputs.

```text
data/
  raw/
    environmental/forest/  FRA, GEZ, Gibbs/GFW, JRC, FAOSTAT, Pan
    environmental/marine/  BCW source account and GMW mangrove data
    economic/              national emissions, population, GDP, action-cost data
    geospatial/            country and EEZ boundaries
  reference/               transcribed published values and territory crosswalks
  metadata/                source registry and checksums
  derived/                 harmonised tables reused as inputs by later calculations
  outputs/                 generated accounts, Gibbs/GFW and Busch results, draws, rasters, and diagnostics
  logs/                    processing logs where retained
```

Generated analytical artifacts belong in `outputs/`, not in the manuscript-facing `results/` folder. Calculated tables, provenance, Monte Carlo draws, and the small derived raster intermediates are versioned with the code. Large source rasters and source archives are excluded and downloaded by their dedicated pipelines when a full rebuild is requested.

Raw files are not edited in place. Their source, release, access date, licence, and use are recorded in [`metadata/source_registry.csv`](metadata/source_registry.csv). Checksums for versioned raw files are in [`metadata/raw_checksums.csv`](metadata/raw_checksums.csv). Source-specific citation and licence requirements are described in [`../docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).

Files under `raw/` retain their provider's terms. Large raster tiles and the GMW polygon archive are excluded from Git; retrieval and verification instructions are in the data-source documentation and the root README.
