"""Download the public Busch input archive and rebuild its cell-level outputs.

The archive and extracted country DTA files stay in scratch space outside Git.
The derived curves, country summaries, and provenance are written to
data/outputs/busch_reconstruction/ and can be committed with the repository.
The current 2% GCW allocation must already exist; main.py creates it from the
current account before invoking this pipeline in full-rebuild mode.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABEL = "mangrove_refresh_20261023"
ALLOCATION = ROOT / "data/outputs/validation/our_2pct_gcw_allocation_and_pledge.csv"
OUTPUT_DIR = ROOT / "data/outputs/busch_reconstruction"


def run_script(name: str, *arguments: str) -> None:
    script = ROOT / "code/scripts" / name
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=DEFAULT_LABEL, help="Output label for the reconstruction")
    args = parser.parse_args()
    if not ALLOCATION.is_file():
        raise FileNotFoundError(
            f"Current 2% GCW allocation is missing: {ALLOCATION.relative_to(ROOT)}. "
            "Run main.py first to create the current account target."
        )

    run_script("download_busch_inputs.py")
    run_script("rebuild_busch_sample_finance.py", "--label", args.label)

    summary_path = OUTPUT_DIR / f"busch_{args.label}_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Busch reconstruction summary was not created: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("processed_units", 0) <= 0 or summary.get("missing_country_input_dtas", 1) != 0:
        raise RuntimeError("Busch reconstruction finished without processing the complete country input set")
    print(
        f"Verified Busch reconstruction: {summary['processed_units']} country inputs; "
        f"outputs in {OUTPUT_DIR.relative_to(ROOT)}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
