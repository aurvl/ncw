# Repository guide for coding agents

## Start with the canonical documentation

- Read `README.md` for the repository layout and execution commands.
- Use `docs/PIPELINE.md` as the English description of the calculations and `docs/PIPELINE_FR.md` as its French counterpart.
- Use `docs/DATA_SOURCES.md` for source provenance. `docs/figures/ncw-workflow.svg` is the high-level workflow diagram.
- Other dated audit, planning, and sensitivity notes under `docs/` are local working files and are excluded from Git.

## Run the project

- Run commands from the repository root.
- `python code/scripts/main.py` is the standard account and table pipeline. It reuses prepared products under `data/derived/` and does not execute notebooks.
- `python code/scripts/main.py --rebuild-derived` downloads or rebuilds the large source-derived stages before continuing. Use it only when a full source rebuild is required; it is not the default workflow.
- Notebooks under `code/notebooks/` are independent analyses. Execute them separately when their figures or workbook outputs need refreshing.
- Use the dedicated scripts under `code/scripts/` when rebuilding a single source-derived stage instead of running unrelated stages.

## Keep code and outputs aligned

- When changing a scientific definition, formula, input source, or output schema, update both pipeline documents and the relevant code or data-source documentation.
- Treat files in `data/derived/` and `results/` as generated outputs. Change their producing code and regenerate them when requested; do not hand-edit their values.
- Keep large raw downloads, credentials, local audit notes, and planning files out of Git, following `.gitignore`.
