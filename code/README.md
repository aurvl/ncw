# Code

The reusable calculations live in `code/src/gcw/`. Scripts are command-line entry points that call these modules. Notebooks support analysis and figures; tests check the reusable pipeline.

## Main components

| Component | Reusable modules | Entry point or output |
| --- | --- | --- |
| Forest areas and biome allocation | `code/src/gcw/forest_areas.py`, `biome_shares.py` | `code/scripts/main.py --rasters` |
| Gibbs/GFW rates and forest additions | `code/src/gcw/gfw_rates.py`, `forest_uptake_gfw.py` | `code/scripts/build_gfw_rates.py` |
| FAOSTAT comparator | `code/src/gcw/faostat_flux.py`, `forest_uptake_pan.py`, `pan_rates.py` | `code/scripts/main.py` |
| National accounts | `code/src/gcw/gcw.py`, `ncw.py`, `tables.py` | `code/scripts/main.py` |
| Marine-area update and audits | scripts named `gmw`, `mangrove`, and `bcw` | `data/derived/` and `data/derived/validation/` |
| Socioeconomic and emissions inputs | scripts named `socioeconomic` and `spatial` | `data/derived/` and `data/derived/validation/` |
| Climate-finance comparisons | `code/scripts/compare_finance_and_action_costs.py` | `data/derived/validation/` |

## Command-line scripts

Run commands from the repository root. By default, `python code/scripts/main.py` reuses the versioned derived data under `data/derived/`; it does not download or recompute the large source datasets. To rebuild the derived data from the large sources before the accounts and tables, run `python code/scripts/main.py --rebuild-derived`. This option is off by default. The source stages can also be launched separately with `python code/scripts/rebuild_gmw_2025_pipeline.py`, `python code/scripts/rebuild_gibbs_gfw_pipeline.py`, `python code/scripts/rebuild_forest_raster_allocation.py`, and `python code/scripts/rebuild_busch_pipeline.py`.

The script directory includes reproducible pipeline steps, source downloads, validation, spatial analyses, and manuscript utilities. Prepared inputs and all intermediate analytical data go to `data/derived/`; manuscript-facing tables and figures go to `results/`. Source inputs under `data/raw/` are not modified.

## Notebooks

The nine current notebooks are directly under `code/notebooks/`. They are the reader-facing analysis, figure and manuscript-output workflows: each reads prepared data or results, states its sample and units, and points back to the reusable pipeline that produced its inputs. The R/Quarto spatial notebook reviews the prepared model evidence. Earlier exploratory notebooks and short component navigation guides remain locally under `code/notebooks/archive/`, which is ignored by Git. See [`code/notebooks/README.md`](notebooks/README.md) for the full index and run instructions.

## Tests

Run `python -m pytest -q` from the repository root. The test suite checks calculation helpers and accounting identities. Spatial-analysis dependencies are provided by the `spatial` optional dependency group.
