"""Q: What is the Natural Carbon Wealth of each territory (forest + ocean)?

For each accounting unit, BCW is calculated from the selected mangrove area, the
Hilmi-reported seagrass and saltmarsh areas, the three ecosystem rates, the Hilmi-
reported biological-carbon-pump flux, and the shared GSCC draws. NCW is the draw-by-
draw sum of the available GCW and BCW account values.

Outputs: results/country_level_ncw_accounts.csv, results/draws/ncw_draws.npz,
         data/derived/bcw_draw_alignment.csv,
         data/derived/bcw_mangrove_gmw_area_replacement.csv
"""

from __future__ import annotations

import hashlib
import json
import numpy as np
import pandas as pd

from .config import (
    BCW_DRAWS_NPZ,
    BCW_COUNTRY_CSV,
    BCW_ECOSYSTEM_RATE_ROWS,
    CARBON_TO_CO2,
    FRA_MANGROVE_AREA_YEAR,
    GMW_MANGROVE_AREA_CSV,
    OUTPUT,
    SUMMARY,
)
from .territories import bcw_mapping, read_bcw_table
from .validation import summarise_draws, write_npz_atomic, write_table


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def align_bcw_draws(bcw: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Match BCW draw rows to the published BCW table.

    The BCW release saves draw rows in computation order and the CSV sorted by name, so rows are
    matched on their mean and Monte Carlo standard error (the BCW `_se` column is sd / sqrt(B)).
    """
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        draws = archive["bcw_draws"]
    n_draws = draws.shape[1]
    with np.errstate(invalid="ignore"):
        means = np.nanmean(draws, axis=1)
        mc_se = np.nanstd(draws, axis=1, ddof=1) / np.sqrt(n_draws)
    aligned = np.full((len(bcw), n_draws), np.nan, dtype=np.float32)
    used: set[int] = set()
    status = []
    archive_rows: list[int | None] = []
    for position, (value, se) in enumerate(zip(bcw["Total BCW"], bcw["Total BCW_se"])):
        if np.isnan(value):
            status.append("no_bcw_value")
            archive_rows.append(None)
            continue
        candidates = [
            i for i in np.flatnonzero(np.isclose(means, value, rtol=1e-5) & np.isclose(mc_se, se, rtol=1e-3))
            if i not in used
        ]
        if not candidates:
            status.append("unmatched")
            archive_rows.append(None)
            continue
        if len(candidates) > 1 and not all(
            np.array_equal(draws[candidates[0]], draws[i], equal_nan=True)
            for i in candidates[1:]
        ):
            raise ValueError(
                f"BCW draw row for {bcw.iloc[position]['country_name']} has "
                "multiple non-identical statistical matches"
            )
        used.add(candidates[0])
        archive_rows.append(int(candidates[0]))
        aligned[position] = draws[candidates[0]]
        status.append("matched" if len(candidates) == 1 else "matched_first_of_identical")
    report = pd.DataFrame({
        "bcw_code": bcw["bcw_code"], "bcw_name": bcw["country_name"],
        "alignment": status, "source_archive_row_zero_based": archive_rows,
    })
    unmatched = report.loc[report["alignment"].eq("unmatched"), "bcw_name"].tolist()
    if unmatched:
        raise ValueError(f"BCW source rows with no matching draw row: {unmatched}")
    return aligned, report


def aggregate_bcw_to_units(bcw: pd.DataFrame, draws: np.ndarray) -> tuple[list[str], np.ndarray, pd.DataFrame]:
    """Aggregate published BCW draws and physical inputs by accounting unit."""
    mapping = bcw_mapping(bcw).set_index("bcw_code")["unit_code"]
    unit_of_row = bcw["bcw_code"].map(mapping).to_numpy()
    units = sorted(set(unit_of_row))
    unit_draws = np.full((len(units), draws.shape[1]), np.nan, dtype=np.float32)
    marine_inputs = []
    for position, unit in enumerate(units):
        rows = unit_of_row == unit
        block = draws[rows]
        if not np.isnan(block).all():
            unit_draws[position] = np.nansum(block, axis=0)
        marine_inputs.append({
            "iso3": unit,
            "hilmi_2026_mangroves_km2": bcw.loc[rows, "mangroves_area_km2"].fillna(0.0).sum(),
            "hilmi_2026_mangrove_area_reported": bool(bcw.loc[rows, "mangroves_area_km2"].notna().any()),
            "saltmarshes_area_km2": bcw.loc[rows, "saltmarshes_area_km2"].fillna(0.0).sum(),
            "saltmarsh_area_any_reported": bool(bcw.loc[rows, "saltmarshes_area_km2"].notna().any()),
            "saltmarsh_area_all_rows_reported": bool(bcw.loc[rows, "saltmarshes_area_km2"].notna().all()),
            "seagrasses_area_km2": bcw.loc[rows, "seagrasses_area_km2"].fillna(0.0).sum(),
            "seagrass_area_any_reported": bool(bcw.loc[rows, "seagrasses_area_km2"].notna().any()),
            "seagrass_area_all_rows_reported": bool(bcw.loc[rows, "seagrasses_area_km2"].notna().all()),
            "bcp_sequestration_tc_yr": bcw.loc[rows, "BCP Seq (tC)"].fillna(0.0).sum(),
            "bcp_sequestration_any_reported": bool(bcw.loc[rows, "BCP Seq (tC)"].notna().any()),
            "bcp_sequestration_all_rows_reported": bool(bcw.loc[rows, "BCP Seq (tC)"].notna().all()),
        })
    return units, unit_draws, pd.DataFrame(marine_inputs)


def select_mangrove_area(
    gmw_2025: pd.DataFrame,
    bcw_marine_inputs: pd.DataFrame,
) -> pd.DataFrame:
    """Apply the selected area-source hierarchy for each accounting unit.

    Priority: positive direct GMW-2025 EEZ overlay; FRA-2025 reported value
    (including zero); then the area reported by Hilmi et al. (2026). An area
    absent from all three sources remains missing.
    """
    areas = pd.read_csv(SUMMARY / "forest_areas.csv")
    fra = areas.loc[
        areas["year"].astype(str).eq(FRA_MANGROVE_AREA_YEAR),
        ["iso3", "mangroves", "mangroves_reported"],
    ].drop_duplicates("iso3").set_index("iso3")
    fra_reported = fra["mangroves_reported"].astype(str).str.lower().isin({"true", "1", "yes"})
    # forest_areas.csv fills missing mangrove values with 0 for a separate
    # forest-overlap calculation. Here, only an actual FRA report is eligible:
    # a reported zero remains zero, while an unreported value remains missing.
    fra_area = pd.to_numeric(fra["mangroves"], errors="coerce").where(fra_reported)
    fra_reported = fra_reported.astype("boolean")

    hilmi_rows = bcw_marine_inputs.set_index("iso3")
    hilmi_area = hilmi_rows["hilmi_2026_mangroves_km2"].mul(100.0).where(
        hilmi_rows["hilmi_2026_mangrove_area_reported"]
    )
    gmw25 = gmw_2025.set_index("iso3")["gmw_2025_mangrove_area_ha"]

    codes = sorted(set(gmw25.index) | set(fra.index) | set(hilmi_area.index))
    candidates = pd.DataFrame(index=pd.Index(codes, name="iso3"))
    candidates["gmw_2025_mangroves_ha"] = gmw25.reindex(candidates.index)
    candidates["fra_2025_mangroves_ha"] = fra_area.reindex(candidates.index)
    candidates["fra_2025_mangroves_reported"] = (
        fra_reported.reindex(candidates.index).fillna(False).astype(bool)
    )
    candidates["hilmi_2026_mangroves_ha"] = hilmi_area.reindex(candidates.index)

    candidates["selected_mangrove_area_ha"] = np.nan
    candidates["mangrove_area_source"] = "no_source_available"
    layers = [
        ("gmw_2025_mangroves_ha", "GMW_2025"),
        ("fra_2025_mangroves_ha", "FRA_2025"),
        ("hilmi_2026_mangroves_ha", "Hilmi_2026"),
    ]
    for column, source in layers:
        available = candidates["selected_mangrove_area_ha"].isna()
        values = candidates[column]
        detected = values.gt(0) if source.startswith("GMW_") else values.notna()
        use = available & detected
        candidates.loc[use, "selected_mangrove_area_ha"] = values.loc[use]
        candidates.loc[use, "mangrove_area_source"] = source
    return candidates.reset_index()


def combine_complete_accounts(gcw: np.ndarray, bcw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sum available account components, treating a missing component as zero.

    Rows with neither account remain missing. The returned final mask still
    identifies complete rows with both accounts; callers can distinguish them
    from partial NCW values.
    """
    gcw = np.asarray(gcw, dtype=np.float64)
    bcw = np.asarray(bcw, dtype=np.float64)
    if gcw.shape != bcw.shape or gcw.ndim != 2:
        raise ValueError("GCW and BCW must be same-shaped two-dimensional draw arrays")
    has_gcw = ~np.isnan(gcw).all(axis=1)
    has_bcw = ~np.isnan(bcw).all(axis=1)
    complete = has_gcw & has_bcw
    available = has_gcw | has_bcw
    ncw = np.full(gcw.shape, np.nan, dtype=np.float64)
    ncw[available] = np.nan_to_num(gcw[available]) + np.nan_to_num(bcw[available])
    return ncw, has_gcw, has_bcw, complete


def forest_share_for_composition(
    gcw_mean: np.ndarray,
    ncw_mean: np.ndarray,
    has_gcw: np.ndarray,
    has_bcw: np.ndarray,
) -> np.ndarray:
    """Forest share for map composition: missing BCW is NA; BCW-only is 0%."""
    gcw_mean = np.asarray(gcw_mean, dtype=np.float64)
    ncw_mean = np.asarray(ncw_mean, dtype=np.float64)
    has_gcw = np.asarray(has_gcw, dtype=bool)
    has_bcw = np.asarray(has_bcw, dtype=bool)
    if not (gcw_mean.shape == ncw_mean.shape == has_gcw.shape == has_bcw.shape):
        raise ValueError("Composition inputs must have identical shapes")
    share = np.full(gcw_mean.shape, np.nan, dtype=np.float64)
    complete = has_gcw & has_bcw & np.isfinite(ncw_mean) & (ncw_mean != 0)
    share[complete] = gcw_mean[complete] / ncw_mean[complete]
    share[~has_gcw & has_bcw] = 0.0
    return share


def build_ncw(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    bcw = read_bcw_table()
    bcw_row_draws, alignment = align_bcw_draws(bcw)
    bcw_units, bcw_unit_draws, bcw_marine_inputs = aggregate_bcw_to_units(bcw, bcw_row_draws)
    gscc = gcw_draws["gscc"][None, :]
    gmw_areas = pd.read_csv(GMW_MANGROVE_AREA_CSV)
    if gmw_areas["iso3"].duplicated().any() or (gmw_areas["gmw_2025_mangrove_area_ha"] < 0).any():
        raise ValueError("GMW 2025 mangrove areas must be unique by unit and non-negative")
    provenance_path = SUMMARY / "gmw_2025_mangrove_area_provenance.json"
    if provenance_path.is_file():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        root = SUMMARY.parents[1]
        for relative, expected_sha256 in provenance["files_sha256"].items():
            source = root / relative
            if not source.is_file() or _sha256(source) != expected_sha256:
                raise ValueError(f"GMW input has changed since the area table was built: {relative}")
    audit_file = SUMMARY.parents[1] / "results" / "validation" / "gmw_2025_direct_area_by_account_iso3.csv"
    if audit_file.is_file():
        audit = pd.read_csv(audit_file, usecols=["iso3", "gmw_2025_mangrove_area_ha"])
        comparison = gmw_areas.merge(
            audit, on="iso3", how="outer", indicator=True, validate="one_to_one",
            suffixes=("_input", "_audit"),
        )
        if not comparison["_merge"].eq("both").all() or not np.allclose(
            comparison["gmw_2025_mangrove_area_ha_input"],
            comparison["gmw_2025_mangrove_area_ha_audit"],
            rtol=0, atol=1e-6,
        ):
            raise ValueError("GMW area consumed by NCW differs from its direct EEZ overlay audit")
    area_selection = select_mangrove_area(gmw_areas, bcw_marine_inputs)
    iso = sorted(set(bcw_units) | set(gcw_draws["iso3"]) | set(area_selection["iso3"]))
    position = {code: i for i, code in enumerate(iso)}
    n_draws = gscc.shape[1]

    def place(codes, matrix) -> np.ndarray:
        full = np.full((len(iso), n_draws), np.nan, dtype=np.float32)
        full[[position[c] for c in codes]] = matrix
        return full

    gcw = place(gcw_draws["iso3"], gcw_draws["gcw_usd2015_yr"])
    gcw_uptake = place(gcw_draws["iso3"], gcw_draws["uptake_tco2_yr"])
    gcw_spatial_low = place(gcw_draws["iso3"], gcw_draws["gcw_spatial_sd_low_usd2015_yr"])
    gcw_spatial_high = place(gcw_draws["iso3"], gcw_draws["gcw_spatial_sd_high_usd2015_yr"])
    bcw_published = place(bcw_units, bcw_unit_draws)
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        rate_rows = [BCW_ECOSYSTEM_RATE_ROWS[name] for name in ("saltmarshes", "seagrasses", "mangroves")]
        rates = archive["bce_rates_draws"][rate_rows, :n_draws].astype(np.float64)
    source_area_km2 = bcw[
        ["saltmarshes_area_km2", "seagrasses_area_km2", "mangroves_area_km2"]
    ].fillna(0.0).to_numpy(dtype=np.float64)
    source_bcp_tc = bcw["BCP Seq (tC)"].fillna(0.0).to_numpy(dtype=np.float64)
    source_sequestration_tc = source_area_km2 @ rates + source_bcp_tc[:, None]
    source_formula_usd = source_sequestration_tc * CARBON_TO_CO2 * gscc
    formula_errors = np.full(len(bcw), np.nan, dtype=np.float64)
    for row in range(len(bcw)):
        finite = np.isfinite(source_formula_usd[row]) & np.isfinite(bcw_row_draws[row])
        if finite.any():
            relative = np.abs(source_formula_usd[row, finite] - bcw_row_draws[row, finite]) / np.maximum(
                np.abs(bcw_row_draws[row, finite]), 1.0
            )
            formula_errors[row] = float(relative.max())
    alignment["area_rate_formula_max_relative_error"] = formula_errors

    area_selection = area_selection.set_index("iso3").reindex(iso)
    selected_area = area_selection["selected_mangrove_area_ha"]
    hilmi_area = area_selection["hilmi_2026_mangroves_ha"]
    has_published_bcw = ~np.isnan(bcw_published).all(axis=1)
    marine = bcw_marine_inputs.set_index("iso3").reindex(iso)
    saltmarsh_area = marine["saltmarshes_area_km2"].fillna(0.0).to_numpy(dtype=np.float64)
    seagrass_area = marine["seagrasses_area_km2"].fillna(0.0).to_numpy(dtype=np.float64)
    bcp_tc = marine["bcp_sequestration_tc_yr"].fillna(0.0).to_numpy(dtype=np.float64)
    saltmarsh_any_reported = marine["saltmarsh_area_any_reported"].fillna(False).to_numpy(dtype=bool)
    seagrass_any_reported = marine["seagrass_area_any_reported"].fillna(False).to_numpy(dtype=bool)
    bcp_any_reported = marine["bcp_sequestration_any_reported"].fillna(False).to_numpy(dtype=bool)
    saltmarsh_all_rows_reported = marine["saltmarsh_area_all_rows_reported"].fillna(False).to_numpy(dtype=bool)
    seagrass_all_rows_reported = marine["seagrass_area_all_rows_reported"].fillna(False).to_numpy(dtype=bool)
    bcp_all_rows_reported = marine["bcp_sequestration_all_rows_reported"].fillna(False).to_numpy(dtype=bool)
    non_mangrove_sequestration_tc = (
        saltmarsh_area[:, None] * rates[0][None, :]
        + seagrass_area[:, None] * rates[1][None, :]
        + bcp_tc[:, None]
    )
    selected_mangrove_tco2 = (
        selected_area.to_numpy(dtype=np.float64)[:, None] / 100.0
        * rates[2][None, :] * CARBON_TO_CO2
    ).astype(np.float32)
    saltmarsh_tco2 = (
        saltmarsh_area[:, None] * rates[0][None, :] * CARBON_TO_CO2
    ).astype(np.float32)
    seagrass_tco2 = (
        seagrass_area[:, None] * rates[1][None, :] * CARBON_TO_CO2
    ).astype(np.float32)
    bcp_tco2 = np.broadcast_to(
        bcp_tc[:, None] * CARBON_TO_CO2, non_mangrove_sequestration_tc.shape
    ).astype(np.float32)
    non_mangrove_tco2 = saltmarsh_tco2 + seagrass_tco2 + bcp_tco2
    # Keep missing source components missing in source tables. In the sum, use
    # the reported components; an unknown mangrove area contributes no number
    # but remains unknown in selected_mangrove_tco2.
    bcw_sequestration_tco2 = non_mangrove_tco2 + np.nan_to_num(
        selected_mangrove_tco2, nan=0.0
    )
    has_any_flux_input = (
        selected_area.notna().to_numpy()
        | saltmarsh_any_reported
        | seagrass_any_reported
        | bcp_any_reported
    )
    bcw_sequestration_tco2[~has_any_flux_input] = np.nan
    bcw_flux_inputs_complete = (
        selected_area.notna().to_numpy()
        & saltmarsh_all_rows_reported
        & seagrass_all_rows_reported
        & bcp_all_rows_reported
    )
    bcw_updated = bcw_published.copy()
    # A retained mangrove area allows an updated BCW calculation even where
    # Hilmi did not publish a BCW total; the reported source columns stay intact.
    recalculate = selected_area.notna().to_numpy()
    bcw_updated[recalculate] = (
        bcw_sequestration_tco2[recalculate].astype(np.float64) * gscc
    ).astype(np.float32)
    no_area_but_published = selected_area.isna().to_numpy() & has_published_bcw
    if not np.array_equal(
        bcw_updated[no_area_but_published],
        bcw_published[no_area_but_published],
        equal_nan=True,
    ):
        raise ValueError("A missing selected mangrove area must retain the Hilmi-reported BCW draws")
    selected_area_values = selected_area.to_numpy(dtype=np.float64)
    hilmi_area_values = hilmi_area.to_numpy(dtype=np.float64)
    has_both_areas = np.isfinite(selected_area_values) & np.isfinite(hilmi_area_values)
    area_changed = np.zeros(len(iso), dtype=bool)
    area_changed[has_both_areas] = ~np.isclose(
        selected_area_values[has_both_areas], hilmi_area_values[has_both_areas], rtol=0, atol=1e-6
    )
    area_source_updated = selected_area.notna().to_numpy() & area_selection[
        "mangrove_area_source"
    ].ne("Hilmi_2026").to_numpy()
    area_new_without_hilmi = selected_area.notna().to_numpy() & hilmi_area.isna().to_numpy()
    mangrove_area_audit = pd.DataFrame(
        {
            "iso3": iso,
            "gmw_2025_mangroves_ha": area_selection["gmw_2025_mangroves_ha"].to_numpy(),
            "fra_2025_mangroves_ha": area_selection["fra_2025_mangroves_ha"].to_numpy(),
            "fra_2025_mangroves_reported": area_selection["fra_2025_mangroves_reported"].to_numpy(),
            "hilmi_2026_mangroves_ha": hilmi_area.to_numpy(),
            "selected_mangrove_area_ha": selected_area.to_numpy(),
            "mangrove_area_source": area_selection["mangrove_area_source"].to_numpy(),
            "mangrove_area_source_updated_from_hilmi": area_source_updated,
            "mangrove_area_changed_from_hilmi": area_changed,
            "mangrove_area_new_where_hilmi_missing": area_new_without_hilmi,
            "mangrove_area_comparable_to_hilmi": has_both_areas,
        }
    )

    ncw, has_gcw, has_bcw, complete_accounts = combine_complete_accounts(gcw, bcw_updated)
    ncw_spatial_low = np.full_like(ncw, np.nan)
    ncw_spatial_high = np.full_like(ncw, np.nan)
    ncw_spatial_low[complete_accounts] = (
        np.nan_to_num(gcw_spatial_low[complete_accounts]) + np.nan_to_num(bcw_updated[complete_accounts])
    )
    ncw_spatial_high[complete_accounts] = (
        np.nan_to_num(gcw_spatial_high[complete_accounts]) + np.nan_to_num(bcw_updated[complete_accounts])
    )

    table = pd.concat(
        [
            pd.DataFrame({"iso3": iso}),
            summarise_draws(ncw, "ncw_usd2015_yr"),
            summarise_draws(ncw_spatial_low, "ncw_spatial_sd_low_usd2015_yr")["ncw_spatial_sd_low_usd2015_yr_mean"].to_frame(),
            summarise_draws(ncw_spatial_high, "ncw_spatial_sd_high_usd2015_yr")["ncw_spatial_sd_high_usd2015_yr_mean"].to_frame(),
            summarise_draws(gcw, "gcw_usd2015_yr")[["gcw_usd2015_yr_mean", "gcw_usd2015_yr_p05", "gcw_usd2015_yr_p95"]],
            summarise_draws(bcw_updated, "bcw_usd2015_yr")[["bcw_usd2015_yr_mean", "bcw_usd2015_yr_p05", "bcw_usd2015_yr_p95"]],
            summarise_draws(bcw_published, "bcw_published_usd2015_yr")[["bcw_published_usd2015_yr_mean"]],
            summarise_draws(bcw_sequestration_tco2, "bcw_sequestration_tco2_yr")[["bcw_sequestration_tco2_yr_mean"]],
        ],
        axis=1,
    )
    table["has_gcw"] = has_gcw
    table["has_bcw"] = has_bcw
    table["bcw_flux_inputs_complete"] = bcw_flux_inputs_complete
    info = territories[["iso3", "name", "bcw_codes", "continent", "fra_region", "groups", "population", "gdp"]]
    table = info.merge(table, on="iso3", how="right")
    table["name"] = table["name"].fillna(table["iso3"])
    table["ncw_per_capita_usd2015"] = table["ncw_usd2015_yr_mean"] / table["population"]
    table["ncw_share_of_gdp"] = table["ncw_usd2015_yr_mean"] / table["gdp"]
    table["forest_share_of_ncw"] = forest_share_for_composition(
        table["gcw_usd2015_yr_mean"].to_numpy(),
        table["ncw_usd2015_yr_mean"].to_numpy(),
        has_gcw,
        has_bcw,
    )
    table = table.sort_values("ncw_usd2015_yr_mean", ascending=False).reset_index(drop=True)

    draws = {
        "iso3": np.array(iso), "ncw_usd2015_yr": ncw, "ncw_spatial_sd_low_usd2015_yr": ncw_spatial_low,
        "ncw_spatial_sd_high_usd2015_yr": ncw_spatial_high, "gcw_usd2015_yr": gcw, "bcw_usd2015_yr": bcw_updated,
        "gcw_additions_tco2_yr": gcw_uptake,
        "bcw_published_rows_usd2015_yr": bcw_row_draws, "bcw_codes": bcw["bcw_code"].to_numpy(),
        "bcw_sequestration_tco2_yr": bcw_sequestration_tco2,
        "selected_mangrove_tco2_yr": selected_mangrove_tco2,
        "seagrass_tco2_yr": seagrass_tco2,
        "saltmarsh_tco2_yr": saltmarsh_tco2,
        "bcp_tco2_yr": bcp_tco2,
    }
    return table, draws, alignment, mangrove_area_audit


def run(territories: pd.DataFrame, gcw_draws: dict) -> tuple[pd.DataFrame, dict]:
    table, draws, alignment, mangrove_area_audit = build_ncw(territories, gcw_draws)
    write_table(alignment, SUMMARY / "bcw_draw_alignment.csv")
    alignment_provenance = {
        "source_draws_sha256": hashlib.sha256(BCW_DRAWS_NPZ.read_bytes()).hexdigest(),
        "source_country_csv_sha256": hashlib.sha256(BCW_COUNTRY_CSV.read_bytes()).hexdigest(),
        "matching_method": "published total mean and Monte Carlo standard error; ambiguous matches require identical draws",
        "matched_rows": int(alignment["alignment"].str.startswith("matched").sum()),
    }
    (SUMMARY / "bcw_draw_alignment_provenance.json").write_text(
        json.dumps(alignment_provenance, indent=2) + "\n", encoding="utf-8"
    )
    write_table(mangrove_area_audit, SUMMARY / "bcw_mangrove_gmw_area_replacement.csv")
    write_table(table, OUTPUT / "country_level_ncw_accounts.csv")
    write_npz_atomic(OUTPUT / "draws" / "ncw_draws.npz", **draws)
    return table, draws
