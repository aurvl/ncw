# Derived data

`main.py` and the dedicated analysis scripts write and reuse derived data here. It contains prepared inputs for later calculations, account results, raster products, audit trails, spatial-model results, and the cell-level restoration reconstruction. Manuscript tables and figures are stored separately under `results/`.

```text
data/derived/
  accounts/                 entity-level GCW and NCW working accounts
  busch_reconstruction/     cell-level reconstruction, country curves, costs, and sensitivities
  draws/                    Monte Carlo forest, GCW, and NCW arrays
  forest_account/           forest areas by biome, uptake summaries, and related draws
    pan/                    separate Pan comparison outputs
  gibbs_gfw/                biome rates and tile-by-biome aggregation audits
  rasters/                  generated raster intermediates for spatial allocation
  validation/               checks, source audits, model diagnostics, and analysis tables
```

The pipeline creates the required folders when it writes each derived file. Prepared tables, provenance summaries, Monte Carlo draw arrays, and the small derived raster layers are versioned so a checkout can reuse the prepared analytical state. Draw arrays use Git LFS; install Git LFS before cloning, or run `git lfs install` and `git lfs pull` after cloning. Large provider rasters, the Busch source archive, and extracted source files are downloaded only when a dedicated rebuild is requested; they are not needed for a standard cache-based run.

Run `python code/scripts/main.py` to reuse the prepared derived data. Use `python code/scripts/main.py --rebuild-derived` to download and regenerate the GMW overlay, Gibbs/GFW rates, raster allocation, and Busch cell reconstruction before rebuilding the accounts and tables. The option is off by default. Each source-specific stage can also be run separately with `rebuild_gmw_2025_pipeline.py`, `rebuild_gibbs_gfw_pipeline.py`, `rebuild_forest_raster_allocation.py`, or `rebuild_busch_pipeline.py`.
