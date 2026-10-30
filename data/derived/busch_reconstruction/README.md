# Busch country restoration costs and supply

These outputs reconstruct country-level restoration costs and supply from the public cell-level inputs and the modelling framework of Busch et al. (2024). The calculated costs and curves are outputs of this project.

## Calculation order

1. Read every country `.dta` file in `08_input_dtas.zip` and calculate its eligible cells, costs, quantities and supply curves. This stage does not filter countries by FRA loss or by inclusion in the study's entity table.
2. After the country calculations finish, join their ISO3 codes to the study's positive FRA-loss targets. This separate step evaluates target coverage and costs where an ISO3 match exists.

The workbook `11_MAC_curves_consolidated.xlsx` supplies only the shared price-threshold grid. Its country curves are not loaded or compared with these calculations.

## Current output files

| File | Contents |
|---|---|
| `busch_all_dta_country_finance.csv` | One row per country `.dta` input, with cell counts and total modelled 30-year discounted supply. |
| `busch_all_dta_25_price_curves.csv` | Country-level supply at each shared price threshold, for every archive input. |
| `busch_all_dta_effective_cost_curves.csv` | Country-level cumulative quantities and effective costs across the modelled supply. |
| `busch_all_dta_soil_sensitivity_country.csv` | Country-level calculations under each natural-regeneration soil-rate scenario, for every archive input. |
| `busch_all_dta_soil_sensitivity_price_curves.csv` | Price-grid supply curves for every country input and soil scenario. |
| `busch_all_dta_soil_sensitivity_effective_cost_curves.csv` | Effective-cost curves for every country input and soil scenario. |
| `busch_all_dta_coverage.csv` | Positive FRA-loss study entities and their ISO3-matched target results. This is a subset created after all country calculations. |
| `busch_all_dta_soil_sensitivity_coverage.csv` | The same later target join, evaluated under each soil-rate scenario. |
| `busch_all_dta_figure4c_candidate.csv` | Summary of the positive-loss target coverage categories. |
| `busch_all_dta_summary.json` | Archive and processing counts, input hashes, currency conversion, scenario parameters and the target-join checksum. |

The summary lists every country ISO3 found in the archive and every ISO3 processed. A complete rebuild has equal archive and processed counts. Runs made with `--countries` are diagnostic subsets and are marked incomplete; `main.py` will not accept them as the current full result.

## Rebuilding

The large `08_input_dtas.zip` archive is downloaded to `.tmp/busch_08_reconstruction/`, outside the repository, and checked against the expected file size and MD5 by `download_busch_inputs.py`. Run the independent stage with:

```powershell
python code/scripts/rebuild_busch_pipeline.py
```

Or run it with the complete pipeline:

```powershell
python code/scripts/main.py --rebuild-derived
```

A normal `main.py` run reuses the prepared files under `data/derived/` and does not download the archive. Older output labels are retained as historical runs; use the `all_dta` files for the current all-country calculation.

Country parameters and constants transcribed from the Stata program are documented in `code/scripts/busch_stata_parameters.py` and `code/scripts/rebuild_busch_country_finance.py`.
