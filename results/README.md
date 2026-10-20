# Results

Generated outputs are kept separate from source data and calculation code.

```text
results/
  country_level_gcw.csv
  country_level_ncw.csv
  tables/
    manuscript/       paper and supplementary tables
  figures/
    paper_v2/         current paper figure set
  validation/         global checks, audits, diagnostics, and inventories
  draws/              Monte Carlo matrices, generated locally and ignored by Git
```

Run the main pipeline from the repository root with `python code/scripts/main.py`. Large analysis outputs in `validation/` include intermediate audits and diagnostics; they are not all manuscript results. The current full inventory is `validation/RESULTS_INVENTORY_2026-10-20.txt`.

CSV is the canonical format for country accounts and tables. Units and column definitions are described in [`../docs/METHODS.md`](../docs/METHODS.md) and the country-level table dictionary in [`../docs/COUNTRY_LEVEL_RESULTS_MASTER_DATA_DICTIONARY_2026-10-20.md`](../docs/COUNTRY_LEVEL_RESULTS_MASTER_DATA_DICTIONARY_2026-10-20.md).
