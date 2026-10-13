"""Aggregate the published Gibbs/GFW 2001-2023 gross-removal tiles into biome rates.

The source tiles must first be placed in data_source/raw/gfw_gibbs_2025/gross_removals/.
The complete source set is approximately 37 GB. This command does not run the country
accounting pipeline or create national results.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcw.gfw_rates import run  # noqa: E402


if __name__ == "__main__":
    run()
