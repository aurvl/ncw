"""Estimate annual forest-addition capacity lost from FRA deforestation rates.

FRA supplies the latest available annual deforestation rate for each unit. The
rate is valued at the unit's mean forest uptake rate already used in GCW:
annual GCW forest additions divided by the forest area used in that account.
Reported missing values remain missing and reported zero loss remains zero.
The monetary P05-P95 interval is calculated from the existing GSCC draws.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
from gcw.config import BIOMES, CARBON_TO_CO2, FRA_ZIP  # noqa: E402

RATE_FILE = ROOT / "data" / "derived" / "gfw_gibbs_biome_rates_non_mangrove.csv"
AREA_FILE = ROOT / "data" / "derived" / "forest_area_by_biome.csv"
TERRITORY_FILE = ROOT / "data" / "derived" / "territories.csv"
GCW_FILE = ROOT / "results" / "country_level_gcw.csv"
DRAW_FILE = ROOT / "results" / "draws" / "gcw_draws.npz"
OUTPUT = ROOT / "results" / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv"
AUDIT = ROOT / "results" / "validation" / "deforestation_capacity_country_rate.csv"
SUMMARY = ROOT / "results" / "validation" / "deforestation_capacity_country_rate.json"
REPORT_MEMBER = "Intervals_variables/1d_deforestation_2026-09-16.csv"
PERIODS = ["2010-2015", "2015-2020", "2020-2025"]
PERIOD_PRIORITY = ["2020-2025", "2015-2020", "2010-2015"]
EXPECTED_REPORTERS = 139
EXPECTED_POSITIVE_FRA_REPORTS = 100
COHORT_DURATION_YEARS = 1.0


def read_fra_deforestation() -> pd.DataFrame:
    """Read the published FRA deforestation intervals directly from its archive."""
    with zipfile.ZipFile(FRA_ZIP) as archive:
        with archive.open(REPORT_MEMBER) as stream:
            source = pd.read_csv(stream)
    required = {"iso3", "name", *PERIODS}
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"FRA deforestation input is missing columns: {missing}")
    if source["iso3"].duplicated().any():
        raise ValueError("FRA deforestation input has duplicate accounting-unit codes")
    for period in PERIODS:
        source[period] = pd.to_numeric(source[period], errors="coerce")
    source["reported_deforestation"] = source[PERIODS].notna().any(axis=1)
    source["loss_period_selected"] = source[PERIOD_PRIORITY].notna().idxmax(axis=1)
    source.loc[~source["reported_deforestation"], "loss_period_selected"] = pd.NA
    selected_thousand_ha_yr = source[PERIOD_PRIORITY].bfill(axis=1).iloc[:, 0]
    source["loss_area_ha_yr"] = selected_thousand_ha_yr * 1000.0
    return source[[
        "iso3", "name", *PERIODS, "loss_period_selected", "loss_area_ha_yr",
        "reported_deforestation",
    ]]


def build_country_forest_rates(
    gcw: pd.DataFrame,
    biome_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate U_i / A_i and retain the existing biome-dispersion sensitivity."""
    areas = pd.read_csv(AREA_FILE)
    required_area = {"iso3", "biome", "variant", "area_ha"}
    missing_area = sorted(required_area - set(areas.columns))
    if missing_area:
        raise ValueError(f"Forest-area input is missing columns: {missing_area}")
    areas = areas.loc[areas["variant"].eq("documented_overlap_removed")].copy()
    if areas.duplicated(["iso3", "biome"]).any():
        raise ValueError("GCW forest areas are not unique by unit and biome")
    if not set(areas["biome"].dropna()).issubset(BIOMES):
        raise ValueError("GCW forest-area input contains an unexpected biome")
    if (areas["area_ha"].dropna() < 0).any():
        raise ValueError("GCW forest-area input contains a negative area")

    area_matrix = (
        areas.pivot(index="iso3", columns="biome", values="area_ha")
        .reindex(columns=BIOMES)
    )
    total_area = area_matrix.sum(axis=1, min_count=1).rename("forest_area_total_ha")

    required_rate = {"biome", "rate_tc_ha_yr_mean", "rate_tc_ha_yr_spatial_sd"}
    missing_rate = sorted(required_rate - set(biome_rates.columns))
    if missing_rate:
        raise ValueError(f"Biome-rate input is missing columns: {missing_rate}")
    if biome_rates["biome"].duplicated().any() or set(biome_rates["biome"]) != set(BIOMES):
        raise ValueError("Expected exactly one Gibbs/GFW rate and spatial SD per biome")
    indexed_rates = biome_rates.set_index("biome").reindex(BIOMES)
    central_tc = indexed_rates["rate_tc_ha_yr_mean"].astype(float)
    spatial_sd_tc = indexed_rates["rate_tc_ha_yr_spatial_sd"].astype(float)
    low_tc = (central_tc - spatial_sd_tc).clip(lower=0.0)
    high_tc = central_tc + spatial_sd_tc

    gcw_required = {"iso3", "uptake_tco2_yr_mean"}
    missing_gcw = sorted(gcw_required - set(gcw.columns))
    if missing_gcw:
        raise ValueError(f"GCW input is missing columns: {missing_gcw}")
    if gcw["iso3"].duplicated().any():
        raise ValueError("Current GCW table has duplicate accounting-unit codes")

    result = gcw[["iso3", "uptake_tco2_yr_mean"]].merge(
        total_area.reset_index(), on="iso3", how="outer", validate="one_to_one"
    )
    result["forest_rate_tco2_ha_yr"] = result["uptake_tco2_yr_mean"] / result[
        "forest_area_total_ha"
    ].where(result["forest_area_total_ha"].gt(0))

    aligned_areas = area_matrix.reindex(result["iso3"]).fillna(0.0)
    aligned_total = result["forest_area_total_ha"].to_numpy(dtype="float64")
    valid_area = np.isfinite(aligned_total) & (aligned_total > 0)
    for suffix, rates_tc in (("low", low_tc), ("high", high_tc)):
        weighted_tc = aligned_areas.to_numpy(dtype="float64") @ rates_tc.to_numpy(dtype="float64")
        rate_tco2 = np.full(len(result), np.nan, dtype="float64")
        rate_tco2[valid_area] = (
            weighted_tc[valid_area] / aligned_total[valid_area] * CARBON_TO_CO2
        )
        result[f"forest_rate_spatial_sd_{suffix}_tco2_ha_yr"] = rate_tco2
    return result


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rates = pd.read_csv(RATE_FILE)
    fra = read_fra_deforestation()
    gcw = pd.read_csv(GCW_FILE)
    forest_rates = build_country_forest_rates(gcw, rates)

    losses = fra.merge(forest_rates, on="iso3", how="left", validate="one_to_one")
    cohort_area = losses["loss_area_ha_yr"] * COHORT_DURATION_YEARS
    losses["loss_tco2_mean"] = cohort_area * losses["forest_rate_tco2_ha_yr"]
    losses["loss_spatial_sd_low_tco2_yr"] = (
        cohort_area * losses["forest_rate_spatial_sd_low_tco2_ha_yr"]
    )
    losses["loss_spatial_sd_high_tco2_yr"] = (
        cohort_area * losses["forest_rate_spatial_sd_high_tco2_ha_yr"]
    )
    zero_loss = losses["loss_area_ha_yr"].eq(0)
    losses.loc[zero_loss, [
        "loss_tco2_mean", "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
    ]] = 0.0

    with np.load(DRAW_FILE, allow_pickle=True) as archive:
        gscc = np.asarray(archive["gscc"], dtype="float64")
    if not np.isfinite(gscc).all() or len(gscc) == 0:
        raise ValueError("GSCC draw vector is empty or contains non-finite values")

    territories = pd.read_csv(TERRITORY_FILE)[["iso3", "UNIT_CODE", "ISO3", "region"]]
    output = gcw[[
        "iso3", "name", "groups", "gdp", "uptake_tco2_yr_mean", "gcw_usd2015_yr_mean",
    ]].merge(
        territories, on="iso3", how="left", validate="one_to_one"
    ).merge(
        losses.drop(columns=["name", "uptake_tco2_yr_mean"]).drop(
            columns=PERIODS, errors="ignore"
        ),
        on="iso3", how="left", validate="one_to_one", suffixes=("", "_fra"),
    )
    output["reported_deforestation"] = output["reported_deforestation"].fillna(False).astype(bool)
    for period in PERIODS:
        output[f"loss_area_{period.replace('-', '_')}_ha_yr"] = (
            fra.set_index("iso3")[period].reindex(output["iso3"]).to_numpy(dtype="float64") * 1000.0
        )

    value_draws = output["loss_tco2_mean"].to_numpy(dtype="float64")[:, None] * gscc[None, :]
    reported_mask = output["reported_deforestation"].to_numpy(dtype=bool)
    output["loss_usd_mean"] = np.nan
    output["loss_usd_p05"] = np.nan
    output["loss_usd_p95"] = np.nan
    output.loc[reported_mask, "loss_usd_mean"] = np.mean(value_draws[reported_mask], axis=1)
    output.loc[reported_mask, "loss_usd_p05"] = np.percentile(value_draws[reported_mask], 5, axis=1)
    output.loc[reported_mask, "loss_usd_p95"] = np.percentile(value_draws[reported_mask], 95, axis=1)
    gscc_mean = float(gscc.mean())
    output["loss_spatial_sd_low_usd2015_yr"] = output["loss_spatial_sd_low_tco2_yr"] * gscc_mean
    output["loss_spatial_sd_high_usd2015_yr"] = output["loss_spatial_sd_high_tco2_yr"] * gscc_mean
    output["erosion_pct_of_gcw"] = (
        100.0 * output["loss_area_ha_yr"] * COHORT_DURATION_YEARS
        / output["forest_area_total_ha"].where(output["forest_area_total_ha"].gt(0))
    )
    output["loss_pct_of_gdp"] = 100.0 * output["loss_usd_mean"] / output["gdp"]
    output = output[[
        "UNIT_CODE", "ISO3", "name", "region", "iso3", "groups", "gdp",
        "uptake_tco2_yr_mean", "gcw_usd2015_yr_mean", "forest_area_total_ha",
        "forest_rate_tco2_ha_yr", "forest_rate_spatial_sd_low_tco2_ha_yr",
        "forest_rate_spatial_sd_high_tco2_ha_yr", "reported_deforestation",
        *[f"loss_area_{period.replace('-', '_')}_ha_yr" for period in PERIODS],
        "loss_period_selected", "loss_area_ha_yr", "loss_tco2_mean",
        "loss_usd_mean", "loss_usd_p05", "loss_usd_p95",
        "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
        "loss_spatial_sd_low_usd2015_yr", "loss_spatial_sd_high_usd2015_yr",
        "erosion_pct_of_gcw", "loss_pct_of_gdp",
    ]].sort_values("iso3").reset_index(drop=True)

    old = (
        pd.read_csv(OUTPUT)[["iso3", "loss_tco2_mean"]]
        .rename(columns={"loss_tco2_mean": "previous_loss_tco2"})
        if OUTPUT.is_file()
        else pd.DataFrame(columns=["iso3", "previous_loss_tco2"])
    )
    audit = output.merge(old, on="iso3", how="left", validate="one_to_one")
    audit["change_tco2_yr"] = audit["loss_tco2_mean"] - audit["previous_loss_tco2"]
    audit["change_pct"] = 100.0 * audit["change_tco2_yr"] / audit["previous_loss_tco2"].replace(0.0, np.nan)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(AUDIT, index=False, float_format="%.10g")
    output.to_csv(OUTPUT, index=False, float_format="%.10g")

    reporters = output.loc[output["reported_deforestation"]]
    positive = reporters["loss_area_ha_yr"].gt(0)
    zero = reporters["loss_area_ha_yr"].eq(0)
    capacity_complete = reporters["loss_tco2_mean"].notna().all()
    total_capacity = float(reporters["loss_tco2_mean"].sum(min_count=1))
    total_value = float(reporters["loss_usd_mean"].sum(min_count=1))
    summary = {
        "deforestation_source": f"{FRA_ZIP.name}:{REPORT_MEMBER}",
        "forest_flux_source": str(GCW_FILE.relative_to(ROOT)),
        "forest_area_source": str(AREA_FILE.relative_to(ROOT)),
        "forest_area_variant": "documented_overlap_removed",
        "period_selection_priority": PERIOD_PRIORITY,
        "area_conversion": "select the latest non-missing FRA interval; thousand ha/year x 1000 = ha/year; no averaging across intervals",
        "fra_units_by_selected_interval": {
            period: int(fra["loss_period_selected"].eq(period).sum())
            for period in PERIODS
        },
        "fra_units_without_reported_interval": int(fra["loss_period_selected"].isna().sum()),
        "cohort_duration_years": COHORT_DURATION_YEARS,
        "country_rate_formula": "mean annual GCW forest additions U_i (tCO2/year) / forest area A_i_total (ha)",
        "capacity_loss_formula": "latest FRA annual deforestation rate x 1-year cohort duration x U_i/A_i_total",
        "monetary_draws": "fixed physical capacity loss x the same 20,000 GSCC draws used for the monetary account",
        "monetary_interval": "P05-P95 of the resulting GSCC-valued draws; conditional on fixed FRA area loss and GCW country rate",
        "spatial_sensitivity": "country forest-area-weighted biome rates mean +/- biome spatial SD; deterministic scenario, not a confidence interval",
        "units": int(len(output)),
        "reporters": int(len(reporters)),
        "positive_fra_loss_units": int(positive.sum()),
        "reported_zero_loss_units": int(zero.sum()),
        "reported_units_with_country_rate": int(reporters["forest_rate_tco2_ha_yr"].notna().sum()),
        "reported_units_without_country_rate": int(reporters["forest_rate_tco2_ha_yr"].isna().sum()),
        "annual_lost_addition_capacity_tco2": total_capacity if capacity_complete else None,
        "annual_lost_gcw_value_usd2015": total_value if capacity_complete else None,
        "reported_deforestation_area_ha_yr": float(reporters["loss_area_ha_yr"].sum(min_count=1)),
        "positive_capacity_units": int(reporters["loss_tco2_mean"].gt(0).sum()),
        "gscc_draws": int(len(gscc)),
        "gscc_mean_usd2015_tco2": gscc_mean,
        "capacity_total_complete_for_all_fra_reporters": bool(capacity_complete),
    }
    if summary["reporters"] != EXPECTED_REPORTERS or summary["positive_fra_loss_units"] != EXPECTED_POSITIVE_FRA_REPORTS:
        raise ValueError(f"Unexpected FRA sample counts after refresh: {summary}")
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output, audit, summary


def main() -> None:
    output, _, summary = build()
    print(json.dumps({
        "output": str(OUTPUT),
        "rows": len(output),
        "reporters": summary["reporters"],
        "positive_fra_loss_units": summary["positive_fra_loss_units"],
        "reported_units_without_country_rate": summary["reported_units_without_country_rate"],
        "complete_lost_capacity_mtco2_yr": (
            summary["annual_lost_addition_capacity_tco2"] / 1e6
            if summary["annual_lost_addition_capacity_tco2"] is not None
            else None
        ),
        "complete_lost_gcw_value_billion_usd2015_yr": (
            summary["annual_lost_gcw_value_usd2015"] / 1e9
            if summary["annual_lost_gcw_value_usd2015"] is not None
            else None
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
