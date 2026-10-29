"""Execute a presentation notebook independently of the main data pipeline.

The figure and manuscript-table notebooks own their respective presentation
exports. ``main.py`` builds their canonical input tables but does not execute
notebooks or require their files as pipeline outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = ROOT / "code" / "notebooks"
ALLOWED = {"08_paper_figures.ipynb", "09_manuscript_tables.ipynb"}


def run(name: str) -> None:
    if name not in ALLOWED:
        raise ValueError(f"Not a current paper export notebook: {name}")
    notebook = nbformat.read(NOTEBOOKS / name, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=3600,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        store_widget_state=False,
    )
    client.execute()
    print(f"Executed {name} from first to last cell; source notebook was not rewritten.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", choices=sorted(ALLOWED))
    args = parser.parse_args()
    run(args.notebook)


if __name__ == "__main__":
    main()
