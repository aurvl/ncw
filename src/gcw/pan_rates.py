"""Q: Which carbon uptake rate (tC/ha/yr, mean and sd) applies to each biome and forest type?

Outputs (data_source/summary/):
- pan_biome_flux.csv : Pan et al. (2024) Table 1 fluxes (Pg C/yr) for PAN_PERIOD
- biome_rates.csv    : per-hectare rates = Pan biome flux / global FRA area of that biome
                       (and forest type in the tropics); subtropical rate from the reference table
"""

from __future__ import annotations

import re

import pandas as pd

from .config import (
    AREA_YEAR, BIOMES, BIOMES_WITH_TYPE_SPLIT, FOREST_TYPES, PAN_PERIOD, PAN_ROW_FOR, PAN_TABLE1_HTML,
    SUBTROPICAL_RATE_CSV, SUMMARY,
)
from .validation import write_table

PG_TO_T = 1e9


def _mean_sd(cell: str) -> tuple[float, float]:
    numbers = re.findall(r"[−-]?\d+(?:\.\d+)?", str(cell))
    mean, sd = (float(n.replace("−", "-")) for n in numbers[:2])
    return mean, sd


def read_pan_table1() -> pd.DataFrame:
    table = pd.read_html(PAN_TABLE1_HTML, encoding="utf-8")[0]
    label_column = table.columns[0]
    period_column = next(c for c in table.columns if PAN_PERIOD in str(c))
    rows = table.drop_duplicates(subset=label_column, keep="first")
    rows = rows.loc[rows[label_column].isin(set(PAN_ROW_FOR.values()))]
    records = []
    for _, row in rows.iterrows():
        mean, sd = _mean_sd(row[period_column])
        records.append({"pan_row": row[label_column], "period": PAN_PERIOD, "flux_pgc_yr_mean": mean, "flux_pgc_yr_sd": sd})
    return pd.DataFrame(records)


def global_areas(forest_areas: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    """Global forest area (ha) by biome and type, mangroves excluded from NRF (C7)."""
    year = forest_areas.loc[forest_areas["year"].astype(str) == AREA_YEAR, ["iso3", "nrf_excl_mangroves", "planted"]]
    year = year.rename(columns={"nrf_excl_mangroves": "nrf"})
    merged = shares.merge(year, on="iso3", how="inner")
    records = []
    for forest_type in FOREST_TYPES:
        area = (merged["share"] * merged[forest_type]).groupby(merged["biome"]).sum()
        records += [{"biome": b, "forest_type": forest_type, "global_area_ha": area.get(b, 0.0)} for b in BIOMES]
    return pd.DataFrame(records)


def build_rates(pan: pd.DataFrame, areas: pd.DataFrame) -> pd.DataFrame:
    flux = pan.set_index("pan_row")
    area = areas.set_index(["biome", "forest_type"])["global_area_ha"]
    subtropical = pd.read_csv(SUBTROPICAL_RATE_CSV).set_index("biome").loc["subtropical"]
    records = []
    for biome in BIOMES:
        for forest_type in FOREST_TYPES:
            record = {"biome": biome, "forest_type": forest_type, "global_area_ha": area[(biome, forest_type)]}
            if biome == "subtropical":
                record.update(
                    rate_key="subtropical",
                    pan_row=None,
                    rate_tc_ha_yr_mean=subtropical["rate_tc_ha_yr_mean"],
                    rate_tc_ha_yr_sd=subtropical["rate_tc_ha_yr_sd"],
                    source="reference/subtropical_rate.csv (coauthors' interpolation, C3)",
                )
            else:
                pan_row = PAN_ROW_FOR[(biome, forest_type)]
                denominator = (
                    area[(biome, forest_type)]
                    if biome in BIOMES_WITH_TYPE_SPLIT
                    else area[(biome, "nrf")] + area[(biome, "planted")]
                )
                record.update(
                    rate_key=pan_row,
                    pan_row=pan_row,
                    denominator_area_ha=denominator,
                    rate_tc_ha_yr_mean=flux.loc[pan_row, "flux_pgc_yr_mean"] * PG_TO_T / denominator,
                    rate_tc_ha_yr_sd=flux.loc[pan_row, "flux_pgc_yr_sd"] * PG_TO_T / denominator,
                    source=f"Pan et al. (2024) Table 1, {PAN_PERIOD} / FRA {AREA_YEAR} global area",
                )
            records.append(record)
    return pd.DataFrame(records)


def run(forest_areas: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    pan = read_pan_table1()
    write_table(pan, SUMMARY / "pan_biome_flux.csv")
    rates = build_rates(pan, global_areas(forest_areas, shares))
    write_table(rates, SUMMARY / "biome_rates.csv")
    return rates
