# Results

Generated outputs are kept separate from source data and calculation code.

```text
results/
  country_level_gcw.csv
  country_level_ncw_accounts.csv   core calculated forest-plus-marine account
  tables/
    manuscript/       paper and supplementary tables
  figures/
    Figure1.png ... Figure5.png  current numbered paper figures
    Paper_Illustration.png         unnumbered paper illustration
  validation/         global checks, audits, and diagnostics
  draws/              Monte Carlo matrices, generated locally and ignored by Git
```

Run the main pipeline from the repository root with `python code/scripts/main.py`. Large analysis outputs in `validation/` include intermediate audits and diagnostics; they are not all manuscript results.

`main.py` produces the account CSVs and machine-readable manuscript tables. Notebook 09 runs separately to create `tables/manuscript/Manuscript_tables.xlsx`. Notebook 08 runs separately to save the paper figures. The narrower account intermediate is `country_level_ncw_accounts.csv`. Units and calculation scope are described in [`../docs/METHODS.md`](../docs/METHODS.md) and [`../docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).
