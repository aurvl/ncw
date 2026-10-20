"""Run every utility module and write its table to data/derived/.

Usage:
    python code/scripts/build_summaries.py               # reuse cached raster table if present
    python code/scripts/build_summaries.py --rasters     # recompute GEZ x boundaries x forest mask
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Gibbs/GFW is the forest-rate source for the main pipeline. Pan comparison modules
# remain separate and are intentionally not called from this builder.
from gcw import biome_shares, faostat_flux, forest_areas, forest_uptake_gfw, gfw_rates, gscc, territories  # noqa: E402
from gcw.config import (  # noqa: E402
    GFW_GIBBS_FOREST_TYPE_DIR,
    GFW_GIBBS_REMOVALS_DIR,
    GFW_GIBBS_REMOVALS_PATTERN,
    SUMMARY,
)


def build_summaries(recompute_rasters: bool = False, reuse_gfw_rates: bool = False) -> dict:
    cached_rates = SUMMARY / "gfw_gibbs_biome_rates_non_mangrove.csv"
    if reuse_gfw_rates and not cached_rates.is_file():
        raise FileNotFoundError(f"Cached Gibbs/GFW rates requested but missing: {cached_rates}")
    if not reuse_gfw_rates and not any(GFW_GIBBS_REMOVALS_DIR.glob(GFW_GIBBS_REMOVALS_PATTERN)):
        raise FileNotFoundError(
            f"Gibbs/GFW source tiles are missing from {GFW_GIBBS_REMOVALS_DIR}; "
            "stage the published 2001-2023 gross-removals GeoTIFF set before building summaries."
        )
    if not reuse_gfw_rates and not GFW_GIBBS_FOREST_TYPE_DIR.is_dir():
        raise FileNotFoundError(
            f"The source-version forest-type mask tiles are missing from {GFW_GIBBS_FOREST_TYPE_DIR}. "
            "They are required to exclude code-6 mangrove pixels from the main rates."
        )
    print("[1/7] territories")
    territory_table = territories.run()
    print("[2/7] forest areas (FRA 2025)")
    area_table = forest_areas.run()
    print("[3/7] biome shares (GEZ x boundaries x forest mask)")
    share_table = biome_shares.run(recompute_rasters=recompute_rasters)
    if reuse_gfw_rates:
        print(f"[4/7] reusing cached Gibbs/GFW gross living-biomass rates ({cached_rates})")
        rate_table = pd.read_csv(cached_rates)
    else:
        print("[4/7] Gibbs/GFW non-mangrove gross living-biomass rates by biome")
        rate_table = gfw_rates.run(forest_type_dir=GFW_GIBBS_FOREST_TYPE_DIR)
        rate_table.to_csv(cached_rates, index=False)
    print("[5/7] GSCC draws")
    gscc_draws = gscc.run()
    print("[6/7] Country forest uptake (FRA biome area x Gibbs/GFW rate)")
    _, forest_draws = forest_uptake_gfw.run(area_table, share_table, rate_table, n_draws=gscc_draws.size)
    print("[7/7] Route A FAOSTAT net flux")
    faostat_table = faostat_flux.run(territory_table)
    return {
        "territories": territory_table,
        "rates": rate_table,
        "gscc": gscc_draws,
        "forest_draws": forest_draws,
        "faostat": faostat_table,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rasters", action="store_true", help="recompute the GEZ x boundaries x forest mask table")
    parser.add_argument(
        "--reuse-gfw-rates",
        action="store_true",
        help="reuse data/derived/gfw_gibbs_biome_rates_non_mangrove.csv",
    )
    args = parser.parse_args()
    build_summaries(recompute_rasters=args.rasters, reuse_gfw_rates=args.reuse_gfw_rates)


if __name__ == "__main__":
    main()
