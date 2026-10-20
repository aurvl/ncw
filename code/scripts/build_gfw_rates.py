"""Aggregate the published Gibbs/GFW 2001-2023 gross-removal tiles into biome rates.

The source tiles must first be placed in data/raw/environmental/forest/gfw_gibbs_2025/gross_removals/.
The complete source set is approximately 37 GB. This command does not run the country
accounting pipeline or create national results.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcw.gfw_rates import run  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8, help="Number of tile workers (default: 8)")
    parser.add_argument(
        "--forest-type-dir", type=Path,
        help="Use the matching WRI v1.3.2 forest-type tiles and exclude code 6 (mangroves).",
    )
    args = parser.parse_args()
    run(max_workers=args.workers, forest_type_dir=args.forest_type_dir)
