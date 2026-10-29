"""Rebuild the GEZ x country x JRC forest-mask allocation independently."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code/src"))

from gcw import biome_shares  # noqa: E402


if __name__ == "__main__":
    biome_shares.run(recompute_rasters=True)
