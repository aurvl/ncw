"""Build the paper accounts, analyses, and machine-readable tables.

The standard run reuses the versioned derived intermediates and does not fetch
large source datasets. ``--rebuild-derived`` downloads and rebuilds
the GMW, Gibbs/GFW, raster-allocation, and Busch stages before final tables.
Source-specific stages can also be run independently. ``--accounts-only``
stops after the central accounts. Notebooks run separately after this pipeline.
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

BUSCH_RECON_LABEL = "all_dta"


def run_script(name: str, *args: str) -> None:
    """Run one prepared stage in the same interpreter and repository context."""
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(ROOT / "code" / "scripts" / name), *args], cwd=ROOT, check=True)


def prepare_gmw(rebuild: bool = False) -> None:
    """Use the committed GMW area table or explicitly rebuild it from source polygons."""
    cached = ROOT / "data" / "derived" / "gmw_2025_mangrove_area_by_unit.csv"
    if rebuild:
        run_script("rebuild_gmw_2025_pipeline.py")
    elif cached.is_file():
        print(f"== GMW area cache ==\n  Reusing {cached.relative_to(ROOT)}; run rebuild_gmw_2025_pipeline.py to refresh it.", flush=True)
    else:
        raise FileNotFoundError(
            f"Prepared GMW area table is missing: {cached}. "
            "Run code/scripts/rebuild_gmw_2025_pipeline.py to download and rebuild it."
        )


def prepare_busch_reconstruction(rebuild: bool = False) -> None:
    """Use the committed Busch reconstruction or explicitly download and rebuild it."""
    output_dir = ROOT / "data" / "derived" / "busch_reconstruction"
    prefix = f"busch_{BUSCH_RECON_LABEL}"
    summary_path = output_dir / f"{prefix}_summary.json"
    required = [
        output_dir / f"{prefix}_country_finance.csv",
        output_dir / f"{prefix}_coverage.csv",
        output_dir / f"{prefix}_25_price_curves.csv",
        output_dir / f"{prefix}_effective_cost_curves.csv",
        output_dir / f"{prefix}_soil_sensitivity_country.csv",
        output_dir / f"{prefix}_soil_sensitivity_price_curves.csv",
        output_dir / f"{prefix}_soil_sensitivity_effective_cost_curves.csv",
        output_dir / f"{prefix}_soil_sensitivity_coverage.csv",
        output_dir / f"{prefix}_figure4c_candidate.csv",
    ]
    if rebuild:
        run_script("rebuild_busch_pipeline.py", "--label", BUSCH_RECON_LABEL)
        return
    missing = [path.relative_to(ROOT).as_posix() for path in [summary_path, *required] if not path.is_file() or not path.stat().st_size]
    if missing:
        raise FileNotFoundError(
            "Prepared Busch outputs are missing: " + ", ".join(missing) + ". "
            "Run code/scripts/rebuild_busch_pipeline.py or pass --rebuild-derived to main.py."
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("processed_units", 0) <= 0
            or summary.get("processed_country_dta_count") != summary.get("archive_country_dta_count")
            or not summary.get("processing_scope_complete")
            or not summary.get("country_costs_calculated_for_all_archive_dta_before_loss_join")
            or summary.get("published_curve_comparison_performed") is not False):
        raise ValueError("The prepared Busch reconstruction does not include every country DTA; run its dedicated rebuild pipeline.")
    inputs = [
        ROOT / "data" / "raw" / "economic" / "busch_2024" / "11_MAC_curves_consolidated.xlsx",
        ROOT / "code" / "scripts" / "download_busch_inputs.py",
        ROOT / "code" / "scripts" / "busch_stata_parameters.py",
        ROOT / "code" / "scripts" / "rebuild_busch_country_finance.py",
    ]
    current_hashes = {}
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(f"Busch cache provenance input is missing: {path.relative_to(ROOT)}")
        with path.open("rb") as source:
            current_hashes[path.relative_to(ROOT).as_posix()] = hashlib.file_digest(source, "sha256").hexdigest()
    if summary.get("input_sha256") != current_hashes:
        raise RuntimeError(
            "Prepared Busch cost outputs do not match the current code and source workbook. "
            "Run code/scripts/rebuild_busch_pipeline.py or pass --rebuild-derived to main.py."
        )
    allocation_path = ROOT / "data" / "derived" / "validation" / "our_2pct_gcw_allocation_and_pledge.csv"
    with allocation_path.open("rb") as allocation_file:
        target_join_hash = hashlib.file_digest(allocation_file, "sha256").hexdigest()
    if summary.get("target_join_input_sha256") != target_join_hash:
        raise RuntimeError(
            "Prepared Busch FRA-target join does not match the current allocation/loss table. "
            "Run code/scripts/rebuild_busch_pipeline.py or pass --rebuild-derived to main.py."
        )
    print("== Busch cell reconstruction cache ==\n  Reusing the prepared cell-level results in data/derived/busch_reconstruction.", flush=True)


def verify_outputs(started_at: float) -> None:
    """Fail if a core account or manuscript CSV table was not refreshed."""
    expected = [
        ROOT / "data" / "derived" / "accounts" / "country_level_gcw.csv",
        ROOT / "data" / "derived" / "accounts" / "country_level_ncw_accounts.csv",
        ROOT / "data" / "derived" / "validation" / "global_checks.csv",
        ROOT / "data" / "derived" / "validation" / "country_level_results_master.csv",
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
    parser.add_argument(
        "--rebuild-derived",
        action="store_true",
        help="download and rebuild source-derived GMW, Gibbs/GFW, raster and Busch intermediates before producing final tables",
    )
    rate_mode = parser.add_mutually_exclusive_group()
    rate_mode.add_argument("--reuse-gfw-rates", action="store_true", help="use the validated four-biome rate cache")
    rate_mode.add_argument("--recompute-gfw-rates", action="store_true", help="require complete raw tiles and recompute rates")
    parser.add_argument("--accounts-only", action="store_true", help="stop after central account tables and validation")
    args = parser.parse_args()
    if args.rebuild_derived and (args.accounts_only or args.reuse_gfw_rates or args.recompute_gfw_rates):
        parser.error("--rebuild-derived runs the full workflow; do not combine it with account-only or Gibbs rate mode flags")
    start = time.time()

    if args.rebuild_derived:
        prepare_gmw(rebuild=True)
        run_script("rebuild_gibbs_gfw_pipeline.py")
    else:
        prepare_gmw()
    cache_mode = True if args.reuse_gfw_rates or args.rebuild_derived else False if args.recompute_gfw_rates else True
    print("== Source summaries ==", flush=True)
    inputs = build_summaries(
        recompute_rasters=args.rasters or args.rebuild_derived,
        reuse_gfw_rates=cache_mode,
    )

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
        # This first export refreshes Table 3 and the current GCW allocation,
        # which are prerequisites for the independent cell-level Busch rebuild.
        run_script("compare_finance_and_action_costs.py")
        run_script("build_manuscript_artifacts.py", "--tables-only")
        prepare_busch_reconstruction(rebuild=args.rebuild_derived)
        # The finance comparison and final manuscript tables must use the
        # freshly rebuilt deforestation and restoration outputs.
        run_script("compare_finance_and_action_costs.py")
        run_script("build_manuscript_artifacts.py", "--tables-only")
        verify_outputs(start)

    print(f"Done in {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
