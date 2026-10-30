"""Prepare reusable inputs and build forest-analysis outputs.

Harmonised source inputs are stored under data/derived/. Calculated rates,
forest uptake tables and analysis draws are written under data/derived/.

Usage:
    python code/scripts/build_summaries.py               # reuse cached raster table if present
    python code/scripts/build_summaries.py --rasters     # recompute GEZ x boundaries x forest mask
"""

from __future__ import annotations

import argparse
import json
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
    GIBBS_OUTPUT,
)


def build_summaries(recompute_rasters: bool = False, reuse_gfw_rates: bool = True) -> dict:
    cached_rates = GIBBS_OUTPUT / "gfw_gibbs_biome_rates_non_mangrove.csv"
    source_root = GFW_GIBBS_REMOVALS_DIR.parent
    manifests = (
        (source_root / "gfw_dataverse_manifest.json", GFW_GIBBS_REMOVALS_DIR),
        (source_root / "gfw_forest_type_manifest.json", GFW_GIBBS_FOREST_TYPE_DIR),
    )
    raw_available = True
    for manifest_path, folder in manifests:
        if not manifest_path.is_file():
            raw_available = False
            break
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        if len(entries) != 272 or any(
            not (folder / entry["filename"]).is_file()
            or (folder / entry["filename"]).stat().st_size != entry["size"]
            for entry in entries
        ):
            raw_available = False
            break
    if reuse_gfw_rates and not cached_rates.is_file():
        raise FileNotFoundError(f"Cached Gibbs/GFW rates requested but missing: {cached_rates}")
    if not reuse_gfw_rates and not raw_available:
        raise FileNotFoundError(
            "The two Gibbs/GFW manifests do not match complete 272-tile source sets by filename and size; "
            "stage the source-version removals and forest-type masks or use the validated cached rates."
        )
    print("[1/7] territories")
    territory_table = territories.run()
    print("[2/7] forest areas (FRA 2025)")
    area_table = forest_areas.run()
    print("[3/7] biome shares (FRA first; GEZ/JRC fallback)")
    share_table = biome_shares.run(recompute_rasters=recompute_rasters)
    if reuse_gfw_rates:
        print(f"[4/7] reusing cached Gibbs/GFW gross living-biomass rates ({cached_rates})")
        rate_table = pd.read_csv(cached_rates)
        required = {"biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd", "period", "pool", "source"}
        if not required.issubset(rate_table.columns):
            raise ValueError(f"Cached Gibbs/GFW rates lack columns: {sorted(required - set(rate_table))}")
        if set(rate_table["biome"]) != {"tropical", "subtropical", "temperate", "boreal"} or len(rate_table) != 4:
            raise ValueError("Cached Gibbs/GFW rates must contain each of the four biomes once")
        if not rate_table["period"].eq("2001-2023 mean annual rate").all():
            raise ValueError("Cached Gibbs/GFW rates have an unexpected source period")
        if not rate_table["pool"].eq("above- and below-ground living biomass").all():
            raise ValueError("Cached Gibbs/GFW rates have an unexpected carbon pool")
        if not raw_available:
            print("  Source tiles/masks are absent: this is a cache-based reproduction, not a fresh raster audit.")
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--reuse-gfw-rates",
        action="store_true",
        help="reuse data/derived/gibbs_gfw/gfw_gibbs_biome_rates_non_mangrove.csv",
    )
    mode.add_argument("--recompute-gfw-rates", action="store_true", help="require raw Gibbs/GFW tiles and recompute rates")
    args = parser.parse_args()
    use_cache = True if args.reuse_gfw_rates or not args.recompute_gfw_rates else False
    build_summaries(recompute_rasters=args.rasters, reuse_gfw_rates=use_cache)


if __name__ == "__main__":
    main()
