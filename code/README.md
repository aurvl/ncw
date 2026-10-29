# Code

The reusable calculations live in `code/src/gcw/`. Scripts are command-line entry points that call these modules. Notebooks support analysis and figures; tests check the reusable pipeline.

## Main components

| Component | Reusable modules | Entry point or output |
| --- | --- | --- |
| Forest areas and biome allocation | `code/src/gcw/forest_areas.py`, `biome_shares.py` | `code/scripts/main.py --rasters` |
| Gibbs/GFW rates and forest additions | `code/src/gcw/gfw_rates.py`, `forest_uptake_gfw.py` | `code/scripts/build_gfw_rates.py` |
| FAOSTAT comparator | `code/src/gcw/faostat_flux.py`, `forest_uptake_pan.py`, `pan_rates.py` | `code/scripts/main.py` |
| National accounts | `code/src/gcw/gcw.py`, `ncw.py`, `tables.py` | `code/scripts/main.py` |
| Marine-area update and audits | scripts named `gmw`, `mangrove`, and `bcw` | `data/derived/` and `data/outputs/validation/` |
| Socioeconomic and emissions inputs | scripts named `socioeconomic` and `spatial` | `data/derived/` and `data/outputs/validation/` |
| Climate-finance comparisons | `code/scripts/compare_finance_and_action_costs.py` | `data/outputs/validation/` |

## Command-line scripts

Run commands from the repository root. Use `python code/scripts/main.py --reuse-gfw-rates` to rebuild accounts from the prepared non-mangrove rate table. Use `python code/scripts/main.py` to recalculate those rates from source tiles and rebuild the accounts in one run. Large raster calculations have separate prerequisites documented in the root README and method notes.

The script directory includes reproducible pipeline steps, source downloads, validation, spatial analyses, and manuscript utilities. Harmonised calculation inputs go to `data/derived/`; generated analytical artifacts go to `data/outputs/`; manuscript-facing tables and figures go to `results/`. Source inputs under `data/raw/` are not modified.

## Notebooks

The nine current notebooks are directly under `code/notebooks/`. They are the reader-facing analysis, figure and manuscript-output workflows: each reads prepared data or results, states its sample and units, and points back to the reusable pipeline that produced its inputs. The R/Quarto spatial notebook reviews the prepared model evidence. Earlier exploratory notebooks and short component navigation guides remain locally under `code/notebooks/archive/`, which is ignored by Git. See [`code/notebooks/README.md`](notebooks/README.md) for the full index and run instructions.

## Tests

Run `python -m pytest -q` from the repository root. The test suite checks calculation helpers and accounting identities. Spatial-analysis dependencies are provided by the `spatial` optional dependency group.
