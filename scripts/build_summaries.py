"""Run every utility module and write its table to data_source/summary/.

Usage:
    python scripts/build_summaries.py               # reuse cached raster table if present
    python scripts/build_summaries.py --rasters     # recompute GEZ x boundaries x forest mask
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcw import biome_shares, faostat_flux, forest_areas, forest_uptake_pan, gscc, pan_rates, territories  # noqa: E402


def build_summaries(recompute_rasters: bool = False) -> dict:
    print("[1/7] territories")
    territory_table = territories.run()
    print("[2/7] forest areas (FRA 2025)")
    area_table = forest_areas.run()
    print("[3/7] biome shares (GEZ x boundaries x forest mask)")
    share_table = biome_shares.run(recompute_rasters=recompute_rasters)
    print("[4/7] Pan biome rates")
    rate_table = pan_rates.run(area_table, share_table)
    print("[5/7] GSCC draws")
    gscc_draws = gscc.run()
    print("[6/7] Route B forest uptake (area x rate)")
    _, pan_draws = forest_uptake_pan.run(area_table, share_table, rate_table, n_draws=gscc_draws.size)
    print("[7/7] Route A FAOSTAT net flux")
    faostat_table = faostat_flux.run(territory_table)
    return {
        "territories": territory_table,
        "rates": rate_table,
        "gscc": gscc_draws,
        "pan_draws": pan_draws,
        "faostat": faostat_table,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rasters", action="store_true", help="recompute the GEZ x boundaries x forest mask table")
    build_summaries(recompute_rasters=parser.parse_args().rasters)


if __name__ == "__main__":
    main()
