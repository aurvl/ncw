"""Download, verify, and aggregate the source Gibbs/GFW raster tiles.

Run from any working directory with:
    python code/scripts/rebuild_gibbs_gfw_pipeline.py

Raw GeoTIFFs and download manifests remain under data/raw/. Compact rate,
tile-audit, and provenance outputs are written under data/derived/gibbs_gfw/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "data/raw/environmental/forest/gfw_gibbs_2025"
REMOVALS_DIR = SOURCE_ROOT / "gross_removals"
FOREST_TYPE_DIR = SOURCE_ROOT / "forest_type"
OUTPUT_DIR = ROOT / "data/derived/gibbs_gfw"
RATE_FILE = OUTPUT_DIR / "gfw_gibbs_biome_rates_non_mangrove.csv"
TILE_FILE = OUTPUT_DIR / "gfw_gibbs_tile_rates_non_mangrove.csv"


def run_script(name: str, *arguments: str) -> None:
    """Run a pipeline step from the repository root and stop on failure."""
    script = ROOT / "code/scripts" / name
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT, check=True)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-workers", type=int, default=12)
    parser.add_argument("--processing-workers", type=int, default=8)
    args = parser.parse_args()
    if args.download_workers < 1 or args.processing_workers < 1:
        parser.error("worker counts must be positive integers")

    run_script(
        "download_gfw_dataverse.py",
        "--destination", str(REMOVALS_DIR.relative_to(ROOT)),
        "--workers", str(args.download_workers),
    )
    run_script(
        "download_gfw_forest_types.py",
        "--removals-manifest", str((SOURCE_ROOT / "gfw_dataverse_manifest.json").relative_to(ROOT)),
        "--destination", str(FOREST_TYPE_DIR.relative_to(ROOT)),
        "--workers", str(args.download_workers),
    )
    run_script(
        "build_gfw_rates.py",
        "--forest-type-dir", str(FOREST_TYPE_DIR.relative_to(ROOT)),
        "--workers", str(args.processing_workers),
    )

    removals_manifest = SOURCE_ROOT / "gfw_dataverse_manifest.json"
    forest_type_manifest = SOURCE_ROOT / "gfw_forest_type_manifest.json"
    if not all(path.is_file() for path in (removals_manifest, forest_type_manifest, RATE_FILE, TILE_FILE)):
        raise FileNotFoundError("The Gibbs/GFW pipeline did not produce all manifests and rate tables")
    removals = json.loads(removals_manifest.read_text(encoding="utf-8"))
    forest_types = json.loads(forest_type_manifest.read_text(encoding="utf-8"))
    rates = pd.read_csv(RATE_FILE)
    tiles = pd.read_csv(TILE_FILE)
    expected_biomes = {"tropical", "subtropical", "temperate", "boreal"}
    if len(removals) != 272 or len(forest_types) != 272:
        raise ValueError("Expected 272 verified source tiles for each Gibbs/GFW raster collection")
    if len(rates) != 4 or set(rates["biome"]) != expected_biomes:
        raise ValueError("The calculated rate table must contain exactly the four expected biomes")
    if tiles.empty or tiles["source_tile"].nunique() == 0:
        raise ValueError("No tile-level Gibbs/GFW summaries were generated")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pipeline": "Gibbs/GFW non-mangrove biome-rate reconstruction",
        "source_period": "2001-2023",
        "removals_source": "Harvard Dataverse DOI 10.7910/DVN/V2ISRH",
        "forest_type_source": "WRI/GFW removal forest-type tiles, 20240308 release",
        "source_tile_count": {"gross_removals": len(removals), "forest_type": len(forest_types)},
        "aggregated_tile_count": int(tiles["source_tile"].nunique()),
        "output_sha256": {RATE_FILE.name: sha256(RATE_FILE), TILE_FILE.name: sha256(TILE_FILE)},
        "completed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUTPUT_DIR / "gfw_pipeline_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
