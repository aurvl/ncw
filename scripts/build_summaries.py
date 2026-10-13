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

from gcw import biome_shares, faostat_flux, forest_areas, forest_uptake_gfw, gfw_rates, gscc, territories  # noqa: E402
from gcw.config import GFW_GIBBS_REMOVALS_DIR, GFW_GIBBS_REMOVALS_PATTERN  # noqa: E402


def build_summaries(recompute_rasters: bool = False) -> dict:
    if not any(GFW_GIBBS_REMOVALS_DIR.glob(GFW_GIBBS_REMOVALS_PATTERN)):
        raise FileNotFoundError(
            f"Gibbs/GFW source tiles are missing from {GFW_GIBBS_REMOVALS_DIR}; "
            "stage the published 2001-2023 gross-removals GeoTIFF set before building summaries."
        )
    print("[1/7] territories")
    territory_table = territories.run()
    print("[2/7] forest areas (FRA 2025)")
    area_table = forest_areas.run()
    print("[3/7] biome shares (GEZ x boundaries x forest mask)")
    share_table = biome_shares.run(recompute_rasters=recompute_rasters)
    print("[4/7] Gibbs/GFW gross living-biomass rates by biome")
    rate_table = gfw_rates.run()
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
    build_summaries(recompute_rasters=parser.parse_args().rasters)


if __name__ == "__main__":
    main()
