"""Rebuild reported deforestation capacity loss from current FRA biome areas.

FRA deforestation is allocated across the four current forest biomes using each
unit's post-overlap-removal forest-area shares. The annual area loss is multiplied
by the corresponding Gibbs/GFW living-biomass addition rates and 44/12. Missing
FRA reports remain missing; reported zero loss remains zero.
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

AREA_FILE = ROOT / "data" / "derived" / "forest_area_by_biome.csv"
RATE_FILE = ROOT / "data" / "derived" / "gfw_gibbs_biome_rates_non_mangrove.csv"
TERRITORY_FILE = ROOT / "data" / "derived" / "territories.csv"
GCW_FILE = ROOT / "results" / "country_level_gcw.csv"
DRAW_FILE = ROOT / "results" / "draws" / "gcw_draws.npz"
OUTPUT = ROOT / "results" / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv"
AUDIT = ROOT / "results" / "validation" / "deforestation_capacity_mangrove_recalculation.csv"
SUMMARY = ROOT / "results" / "validation" / "deforestation_capacity_mangrove_recalculation.json"
REPORT_MEMBER = "Intervals_variables/1d_deforestation_2026-09-16.csv"
PERIODS = ["2010-2015", "2015-2020"]
AREA_VARIANT = "documented_overlap_removed"
EXPECTED_REPORTERS = 139
EXPECTED_POSITIVE = 105


def weighted_biome_rate(shares: pd.DataFrame, rates: pd.Series) -> pd.Series:
    """Return the area-share-weighted annual rate for each accounting unit."""
    missing = sorted(set(BIOMES) - set(shares.columns))
    if missing:
        raise ValueError(f"Biome shares are missing columns: {missing}")
    if set(BIOMES) - set(rates.index):
        raise ValueError("Gibbs/GFW rate table does not contain all four biomes")
    return shares.reindex(columns=BIOMES).mul(rates.reindex(BIOMES), axis="columns").sum(axis=1)


def estimate_capacity_loss(
    annual_area_loss_ha: pd.Series,
    biome_shares: pd.DataFrame,
    biome_rates_tc_ha_yr: pd.Series,
) -> pd.Series:
    """Apply the existing area x rate calculation to a representative annual cohort."""
    weighted_rate = weighted_biome_rate(biome_shares, biome_rates_tc_ha_yr)
    result = annual_area_loss_ha * weighted_rate * CARBON_TO_CO2
    return result.where(annual_area_loss_ha.notna())


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
    source["loss_area_ha_yr"] = source[PERIODS].mean(axis=1, skipna=True) * 1000.0
    source["reported_deforestation"] = source[PERIODS].notna().any(axis=1)
    return source[["iso3", "name", *PERIODS, "loss_area_ha_yr", "reported_deforestation"]]


def build() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    area = pd.read_csv(AREA_FILE)
    area = area.loc[area["variant"].eq(AREA_VARIANT), ["iso3", "biome", "area_ha"]].copy()
    if area.duplicated(["iso3", "biome"]).any():
        raise ValueError("Current forest area has duplicate unit-by-biome rows")
    area_matrix = (
        area.pivot(index="iso3", columns="biome", values="area_ha")
        .reindex(columns=BIOMES)
        .fillna(0.0)
    )
    total_area = area_matrix.sum(axis=1)
    shares = area_matrix.div(total_area.replace(0.0, np.nan), axis="index")

    rates = pd.read_csv(RATE_FILE).set_index("biome")
    if rates.index.duplicated().any() or set(rates.index) != set(BIOMES):
        raise ValueError("Expected exactly one current non-mangrove Gibbs/GFW rate per biome")
    mean_rate = rates["rate_tc_ha_yr_mean"].reindex(BIOMES)
    rate_sd = rates["rate_tc_ha_yr_spatial_sd"].reindex(BIOMES)
    rate_low = (mean_rate - rate_sd).clip(lower=0.0)
    rate_high = mean_rate + rate_sd

    fra = read_fra_deforestation()
    reporter_without_area = fra.loc[
        fra["reported_deforestation"] & ~fra["iso3"].isin(shares.index), "iso3"
    ].tolist()
    no_area = set(shares.index[total_area.le(0)])
    reporter_without_positive_area = fra.loc[
        fra["reported_deforestation"]
        & fra["loss_area_ha_yr"].gt(0)
        & fra["iso3"].isin(no_area), "iso3"
    ].tolist()
    if reporter_without_area or reporter_without_positive_area:
        raise ValueError(
            "Reported deforestation cannot be assigned to current forest biomes: "
            f"missing area={reporter_without_area}, zero area={reporter_without_positive_area}"
        )

    losses = fra.set_index("iso3").copy()
    matched_shares = shares.reindex(losses.index)
    losses["weighted_rate_tc_ha_yr"] = weighted_biome_rate(matched_shares, mean_rate)
    losses["loss_tco2_mean"] = estimate_capacity_loss(
        losses["loss_area_ha_yr"], matched_shares, mean_rate
    )
    losses["loss_spatial_sd_low_tco2_yr"] = estimate_capacity_loss(
        losses["loss_area_ha_yr"], matched_shares, rate_low
    )
    losses["loss_spatial_sd_high_tco2_yr"] = estimate_capacity_loss(
        losses["loss_area_ha_yr"], matched_shares, rate_high
    )

    with np.load(DRAW_FILE, allow_pickle=True) as archive:
        gscc = np.asarray(archive["gscc"], dtype="float64")
    if not np.isfinite(gscc).all() or len(gscc) == 0:
        raise ValueError("GSCC draw vector is empty or contains non-finite values")
    gcw = pd.read_csv(GCW_FILE)
    if gcw["iso3"].duplicated().any():
        raise ValueError("Current GCW table has duplicate accounting-unit codes")
    territories = pd.read_csv(TERRITORY_FILE)[["iso3", "UNIT_CODE", "ISO3", "region"]]
    output = gcw[["iso3", "name", "groups", "gdp", "gcw_usd2015_yr_mean"]].merge(
        territories, on="iso3", how="left", validate="one_to_one"
    )
    output = output.merge(
        losses.reset_index()[[
            "iso3", *PERIODS, "loss_area_ha_yr", "reported_deforestation",
            "weighted_rate_tc_ha_yr", "loss_tco2_mean",
            "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
        ]], on="iso3", how="left", validate="one_to_one"
    )
    output["reported_deforestation"] = output["reported_deforestation"].fillna(False).astype(bool)
    for period in PERIODS:
        output[f"loss_area_{period.replace('-', '_')}_ha_yr"] = output.pop(period) * 1000.0

    # Monetary uncertainty follows the existing workflow: fixed physical loss
    # multiplied by the 20,000 common GSCC draws. Spatial SD remains a separate
    # deterministic sensitivity evaluated at mean GSCC.
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
    output["erosion_pct_of_gcw"] = 100.0 * output["loss_usd_mean"] / output["gcw_usd2015_yr_mean"]
    output["loss_pct_of_gdp"] = 100.0 * output["loss_usd_mean"] / output["gdp"]
    output = output[[
        "UNIT_CODE", "ISO3", "name", "region", "iso3", "groups", "gdp",
        "gcw_usd2015_yr_mean", "reported_deforestation",
        "loss_area_2010_2015_ha_yr", "loss_area_2015_2020_ha_yr", "loss_area_ha_yr",
        "weighted_rate_tc_ha_yr", "loss_tco2_mean", "loss_usd_mean", "loss_usd_p05", "loss_usd_p95",
        "loss_spatial_sd_low_tco2_yr", "loss_spatial_sd_high_tco2_yr",
        "loss_spatial_sd_low_usd2015_yr", "loss_spatial_sd_high_usd2015_yr",
        "erosion_pct_of_gcw", "loss_pct_of_gdp",
    ]].sort_values("iso3").reset_index(drop=True)

    old_path = OUTPUT
    old = pd.read_csv(old_path)[["iso3", "loss_tco2_mean"]].rename(columns={"loss_tco2_mean": "previous_loss_tco2"})
    audit = output.merge(old, on="iso3", how="left", validate="one_to_one")
    audit["change_tco2_yr"] = audit["loss_tco2_mean"] - audit["previous_loss_tco2"]
    audit["change_pct"] = 100.0 * audit["change_tco2_yr"] / audit["previous_loss_tco2"].replace(0.0, np.nan)
    for biome in BIOMES:
        audit[f"forest_area_share_{biome}"] = shares[biome].reindex(audit["iso3"]).to_numpy()
        audit[f"rate_{biome}_tc_ha_yr"] = mean_rate[biome]
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(AUDIT, index=False, float_format="%.10g")
    output.to_csv(OUTPUT, index=False, float_format="%.10g")

    reporters = output.loc[output["reported_deforestation"]]
    positive = reporters["loss_tco2_mean"].gt(0)
    zero = reporters["loss_tco2_mean"].eq(0)
    summary = {
        "source": f"{FRA_ZIP.name}:{REPORT_MEMBER}",
        "area_source": str(AREA_FILE.relative_to(ROOT)),
        "area_variant": AREA_VARIANT,
        "rate_source": str(RATE_FILE.relative_to(ROOT)),
        "area_period_columns": PERIODS,
        "area_conversion": "FRA thousand ha/year × 1000 = ha/year; mean of available periods",
        "formula": "loss area × sum(current post-overlap forest-area biome share × non-mangrove rate) × 44/12",
        "monetary_draws": "fixed physical loss × current aligned 20,000 GSCC draws",
        "spatial_sensitivity": "biome rates mean ± spatial SD, lower bound floored at zero; not a confidence interval",
        "units": int(len(output)),
        "reporters": int(len(reporters)),
        "positive_loss_units": int(positive.sum()),
        "reported_zero_loss_units": int(zero.sum()),
        "unreported_units": int((~output["reported_deforestation"]).sum()),
        "annual_area_loss_reporters_ha": float(reporters["loss_area_ha_yr"].sum()),
        "annual_lost_addition_capacity_tco2": float(reporters["loss_tco2_mean"].sum()),
        "annual_lost_gcw_value_usd2015": float(reporters["loss_usd_mean"].sum()),
        "gscc_draws": int(len(gscc)),
        "gscc_mean_usd2015_tco2": gscc_mean,
        "previous_annual_lost_addition_capacity_tco2": float(old["previous_loss_tco2"].sum(skipna=True)),
    }
    if summary["reporters"] != EXPECTED_REPORTERS or summary["positive_loss_units"] != EXPECTED_POSITIVE:
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
        "positive_loss_units": summary["positive_loss_units"],
        "lost_capacity_mtco2_yr": summary["annual_lost_addition_capacity_tco2"] / 1e6,
        "lost_gcw_value_billion_usd2015_yr": summary["annual_lost_gcw_value_usd2015"] / 1e9,
    }, indent=2))


if __name__ == "__main__":
    main()
