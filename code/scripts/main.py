"""Build the paper accounts, analyses, and machine-readable tables.

The standard run uses complete raw Gibbs/GFW tiles when available, otherwise
validates and uses the four-rate cache. ``--recompute-gfw-rates`` requires all
source-version tiles. ``--accounts-only`` stops after the central accounts.
Exploratory and presentation notebooks run independently after this pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT / "code" / "scripts"))

from build_summaries import build_summaries  # noqa: E402
from gcw import checks, gcw, ncw, tables  # noqa: E402

BUSCH_RECON_LABEL = "mangrove_refresh_20261023"


def run_script(name: str, *args: str) -> None:
    """Run one prepared stage in the same interpreter and repository context."""
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(ROOT / "code" / "scripts" / name), *args], cwd=ROOT, check=True)


def prepare_gmw() -> None:
    """Build mangrove areas from the direct GMW polygon x EEZ overlay."""
    sources = [
        ROOT / "data" / "raw" / "environmental" / "marine" / "gmw"
        / "gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg",
        ROOT / "data" / "raw" / "geospatial" / "boundaries"
        / "EEZ_land_union_v4_202410.shp",
    ]
    overlay_outputs = [
        ROOT / "results" / "validation" / "gmw_2025_direct_overlay_summary.json",
        ROOT / "results" / "validation" / "gmw_2025_direct_overlay_by_eez_unit_and_source.csv",
        ROOT / "results" / "validation" / "gmw_2025_direct_overlay_area_by_eez_unit.csv",
    ]
    if all(path.is_file() for path in sources):
        if not all(path.is_file() for path in overlay_outputs):
            run_script("overlay_gmw_2025_direct_eez.py")
        run_script("build_gmw_2025_direct_area_table.py")
        return
    cached = ROOT / "data" / "derived" / "gmw_2025_mangrove_area_by_unit.csv"
    if not cached.is_file():
        raise FileNotFoundError("GMW/EEZ sources and the prepared direct-overlay area table are missing")
    print("== GMW area cache ==\n  Spatial sources are absent; NCW will validate the prepared direct-overlay area table against its audit.", flush=True)


def prepare_busch_reconstruction() -> None:
    """Refresh cell-level restoration results when inputs or code change."""
    output_dir = ROOT / "results" / "validation" / "busch_reconstruction"
    prefix = f"busch_{BUSCH_RECON_LABEL}"
    summary_path = output_dir / f"{prefix}_summary.json"
    required = [
        output_dir / f"{prefix}_country_finance.csv",
        output_dir / f"{prefix}_coverage_105.csv",
        output_dir / f"{prefix}_25_price_curves.csv",
        output_dir / f"{prefix}_effective_cost_curves.csv",
        output_dir / f"{prefix}_soil_sensitivity_country.csv",
        output_dir / f"{prefix}_soil_sensitivity_price_curves.csv",
        output_dir / f"{prefix}_soil_sensitivity_effective_cost_curves.csv",
    ]
    inputs = [
        ROOT / "data" / "raw" / "economic" / "busch_2024" / "11_MAC_curves_consolidated.xlsx",
        ROOT / "results" / "validation" / "our_2pct_gcw_allocation_and_pledge.csv",
        ROOT / "code" / "scripts" / "download_busch_inputs.py",
        ROOT / "code" / "scripts" / "busch_stata_parameters.py",
        ROOT / "code" / "scripts" / "rebuild_busch_sample_finance.py",
    ]
    if summary_path.is_file() and all(path.is_file() and path.stat().st_size for path in required):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        stored_hashes = summary.get("input_sha256", {})
        current_hashes = {}
        for path in inputs:
            with path.open("rb") as source:
                current_hashes[str(path)] = hashlib.file_digest(source, "sha256").hexdigest()
        processed = summary.get("processed_units", 0)
        expected = summary.get("covered_positive_loss_units", None)
        missing_inputs = summary.get("missing_country_input_dtas", 1)
        if (current_hashes == stored_hashes and processed > 0
                and missing_inputs == 0
                and (expected is None or processed == expected)):
            print("== Busch cell reconstruction cache ==\n  Inputs and direct-reconstruction outputs are current.", flush=True)
            return
    run_script("download_busch_inputs.py")
    run_script("rebuild_busch_sample_finance.py", "--label", BUSCH_RECON_LABEL)


def verify_outputs(started_at: float) -> None:
    """Fail if a core account or manuscript CSV table was not refreshed."""
    expected = [
        ROOT / "results" / "country_level_gcw.csv",
        ROOT / "results" / "country_level_ncw_accounts.csv",
        ROOT / "results" / "validation" / "global_checks.csv",
        ROOT / "results" / "validation" / "country_level_results_master.csv",
        ROOT / "results" / "tables" / "manuscript" / "Table1_global_carbon_wealth.csv",
        ROOT / "results" / "tables" / "manuscript" / "Table2_geographic_economic_profiles.csv",
        ROOT / "results" / "tables" / "manuscript" / "Table3_forest_capacity_erosion.csv",
        ROOT / "results" / "tables" / "manuscript" / "Table4_our_2pct_gcw_allocation.csv",
        ROOT / "results" / "tables" / "manuscript" / "TableS1_forest_biome_additions.csv",
    ]
    missing = [
        str(path.relative_to(ROOT)) for path in expected
        if not path.is_file() or path.stat().st_size == 0 or path.stat().st_mtime < started_at - 2
    ]
    if missing:
        raise FileNotFoundError(f"The paper export is missing or stale: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rasters", action="store_true", help="recompute the GEZ x boundaries x forest mask table")
    rate_mode = parser.add_mutually_exclusive_group()
    rate_mode.add_argument("--reuse-gfw-rates", action="store_true", help="use the validated four-biome rate cache")
    rate_mode.add_argument("--recompute-gfw-rates", action="store_true", help="require complete raw tiles and recompute rates")
    parser.add_argument("--accounts-only", action="store_true", help="stop after central account tables and validation")
    parser.add_argument(
        "--skip-busch-reconstruction",
        action="store_true",
        help="keep the existing Busch cell-reconstruction outputs without downloading its large input archive",
    )
    args = parser.parse_args()
    start = time.time()

    cache_mode = True if args.reuse_gfw_rates else False if args.recompute_gfw_rates else None
    prepare_gmw()
    print("== Source summaries ==", flush=True)
    inputs = build_summaries(recompute_rasters=args.rasters, reuse_gfw_rates=cache_mode)

    print("== GCW ==")
    gcw_table, gcw_draws = gcw.run(inputs["territories"], inputs["forest_draws"], inputs["faostat"], inputs["gscc"])

    print("== BCW and NCW ==", flush=True)
    ncw_table, ncw_draws = ncw.run(inputs["territories"], gcw_draws)

    print("== Central paper tables ==", flush=True)
    tables.run(inputs["forest_draws"], inputs["faostat"], gcw_table, gcw_draws, ncw_table, ncw_draws)

    print("== Validation ==")
    checks.run(inputs["territories"], gcw_table, ncw_table, inputs["forest_draws"], inputs["rates"], gcw_draws, ncw_draws)

    if not args.accounts_only:
        run_script("audit_unresolved_mangrove_overlap_bounds.py")
        # Value the selected FRA loss rate at each unit's mean GCW rate U_i/A_i_total.
        run_script("rebuild_deforestation_capacity.py")
        run_script("compare_finance_and_action_costs.py")
        run_script("build_socioeconomic_2024.py")
        run_script("run_spatial_full_sequence.py")
        run_script("run_spatial_emissions_extension.py")
        run_script("build_country_level_results_master.py")
        run_script("build_manuscript_artifacts.py", "--tables-only")
        if args.skip_busch_reconstruction:
            print("== Busch cell reconstruction ==\n  Skipped by request; existing reconstruction outputs are retained.", flush=True)
        else:
            prepare_busch_reconstruction()
        verify_outputs(start)

    print(f"Done in {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
