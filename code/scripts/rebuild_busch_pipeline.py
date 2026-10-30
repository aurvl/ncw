"""Download the public Busch input archive and rebuild its cell-level outputs.

The archive and extracted country DTA files stay in scratch space outside Git.
The derived curves, country summaries, and provenance are written to
data/derived/busch_reconstruction/ and can be committed with the repository.
If the current 2% GCW allocation exists, positive FRA-loss targets are joined
after every country DTA has been processed. Without it, the all-country cost
outputs are still calculated and the target-coverage tables are empty.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABEL = "all_dta"
OUTPUT_DIR = ROOT / "data/derived/busch_reconstruction"


def run_script(name: str, *arguments: str) -> None:
    script = ROOT / "code/scripts" / name
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=DEFAULT_LABEL, help="Output label for the reconstruction")
    args = parser.parse_args()
    run_script("download_busch_inputs.py")
    run_script("rebuild_busch_country_finance.py", "--label", args.label)

    summary_path = OUTPUT_DIR / f"busch_{args.label}_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Busch reconstruction summary was not created: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("processed_units", 0) <= 0
            or summary.get("processed_country_dta_count") != summary.get("archive_country_dta_count")):
        raise RuntimeError("Busch reconstruction finished without processing every country DTA in the archive")
    print(
        f"Verified all Busch country DTA inputs: {summary['processed_units']} processed; "
        f"outputs in {OUTPUT_DIR.relative_to(ROOT)}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
