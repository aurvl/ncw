"""Full pipeline: raw sources -> summaries -> GCW -> NCW -> paper tables -> validation.

Usage:
    python code/scripts/main.py              # reuse cached raster table if present
    python code/scripts/main.py --rasters    # recompute GEZ x boundaries x forest mask (slow)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_summaries import build_summaries  # noqa: E402
from gcw import checks, gcw, ncw, tables     # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rasters", action="store_true", help="recompute the GEZ x boundaries x forest mask table")
    parser.add_argument(
        "--reuse-gfw-rates",
        action="store_true",
        help="reuse data/derived/gfw_gibbs_biome_rates_non_mangrove.csv",
    )
    args = parser.parse_args()
    start = time.time()

    print("== Summaries ==")
    inputs = build_summaries(recompute_rasters=args.rasters, reuse_gfw_rates=args.reuse_gfw_rates)

    print("== GCW ==")
    gcw_table, gcw_draws = gcw.run(inputs["territories"], inputs["forest_draws"], inputs["faostat"], inputs["gscc"])

    print("== NCW ==")
    ncw_table, ncw_draws = ncw.run(inputs["territories"], gcw_draws)

    print("== Paper tables ==")
    tables.run(inputs["forest_draws"], inputs["faostat"], gcw_table, gcw_draws, ncw_table, ncw_draws)

    print("== Validation ==")
    checks.run(inputs["territories"], gcw_table, ncw_table, inputs["forest_draws"], inputs["rates"], gcw_draws, ncw_draws)

    print(f"Done in {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
