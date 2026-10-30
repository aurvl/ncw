"""Direct cell-level reconstruction from Busch et al. input data.

This script calculates restoration supply and costs for every country DTA in
the public input archive. It does not filter the inputs by FRA coverage or
compare calculated curves with published curves. An optional join to positive
FRA loss is applied only after the full set of country calculations.

Cell values come from the DTA files; the price thresholds are read from the
source workbook and converted to 2015 US dollars. Stata-coded parameters are
transcribed in `busch_stata_parameters.py` and declared below.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from busch_stata_parameters import (
    CONTINENT_GROUPS,
    COUNTRY_PARAMETER_GROUPS,
    DEFAULT_ROOT_SHOOT_RATIO,
    GENUS_BY_TYPE,
    ROOT_RATIO_RULES,
)


REPO = Path(__file__).resolve().parents[2]
HERE = REPO / "data/derived/busch_reconstruction"
CACHE = REPO.parent / ".tmp/busch_08_reconstruction"
INPUT_ZIP = CACHE / "08_input_dtas.zip"
INPUT_ARCHIVE_URL = "https://zenodo.org/records/19239386/files/08_input_dtas.zip?download=1"
# Published archive integrity metadata, not model inputs.
INPUT_ARCHIVE_MD5 = "0fb5708381b11a9d173219f55bca5e81"
INPUT_ARCHIVE_SIZE = 12_384_216_498
WORKBOOK = REPO / "data/raw/economic/busch_2024/11_MAC_curves_consolidated.xlsx"
DOWNLOAD_SCRIPT = REPO / "code/scripts/download_busch_inputs.py"
ALLOCATIONS = REPO / "data/derived/validation/our_2pct_gcw_allocation_and_pledge.csv"
PREFIX = "MAC_mi_whrv_sGr_bu_ad_"
# Core time parameters transcribed from `1. Model loop all data.do`, lines 201-210.
HORIZON_YEARS = 30
DISCOUNT_RATE = 0.05
NR_SOIL_C_PER_YEAR = 0.415107735
PL_SOIL_C_PER_YEAR = 0.092749069
# The source program weights year t by (1-d)^(t-1); this is its 30-year sum.
SOURCE_FACTOR = sum((1 - DISCOUNT_RATE) ** year for year in range(HORIZON_YEARS))
# Conventional present-value factor retained as a comparison scenario, not a Stata parameter.
CONVENTIONAL_FACTOR = sum(
    1 / (1 + DISCOUNT_RATE) ** year for year in range(1, HORIZON_YEARS + 1)
)
CARBON_TO_CO2 = 44.0 / 12.0
# BLS CPI-U annual averages: 2015 = 237.017 and 2020 = 258.811.
USD2020_TO_2015 = 237.017 / 258.811
# The zero-change scenario is the researcher-defined sensitivity; Post & Kwon (2000)
# report 33.8 g C m^-2 yr^-1, equivalent to 0.338 t C ha^-1 yr^-1.
NR_SOIL_SENSITIVITY_SCENARIOS = {
    "busch_reference": NR_SOIL_C_PER_YEAR,
    "zero_soil_change": 0.0,
    "post_kwon_2000": 0.338,
}
# BAU coefficients transcribed from `1. Model loop all data.do`, lines 705-710.
BAU_WEIGHTS = (0.510928, 0.305911, 0.183161)
BAU_DEFAULT = 0.0571795
# These are DTA field names only; observed cell-level values are read from the DTA.
INPUT_COLUMNS = [
    "nr_A", "nr_k", "pinu_A", "pinu_k", "cunn_A", "cunn_k",
    "euca_A", "euca_k", "brde_A", "brde_k", "brev_A", "brev_k",
    "nede_A", "nede_k", "neev_A", "neev_k", "biomes", "type",
    "griscom", "nr_buffer", "pl_buffer", "bau_2020_2030",
    "bau_2030_2040", "bau_2040_2050", "crop_va", "nr_cost",
    "np_cost", "ep_cost", "fao_ecoz", "area_m2", "pxl_id",
]


def input_hashes() -> dict[str, str]:
    result = {}
    paths = [
        WORKBOOK,
        DOWNLOAD_SCRIPT,
        Path(__file__).resolve(),
        Path(__file__).with_name("busch_stata_parameters.py"),
    ]
    for path in paths:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        result[path.relative_to(REPO).as_posix()] = digest.hexdigest()
    return result


def ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add absent output fields as missing values without changing existing data."""
    for column in columns:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame


def source_mappings() -> tuple[dict, dict, dict, dict]:
    """Return source-code parameters transcribed into busch_stata_parameters.py."""
    iso_codes = {
        iso3
        for groups in COUNTRY_PARAMETER_GROUPS.values()
        for codes in groups.values()
        for iso3 in codes
    }
    params = {
        iso3: {"w": 0.0, "p": 0.0, "exotic": 0.0}
        for iso3 in iso_codes
    }
    for variable, groups in COUNTRY_PARAMETER_GROUPS.items():
        for value, codes in groups.items():
            for iso3 in codes:
                params[iso3][variable] = float(value)
    continents = {
        iso3: continent
        for continent, codes in CONTINENT_GROUPS.items()
        for iso3 in codes
    }
    root_rules = {name: list(rules) for name, rules in ROOT_RATIO_RULES.items()}
    return params, continents, dict(GENUS_BY_TYPE), root_rules


def stata_condition(frame: pd.DataFrame, iso3: str, continent: str,
                    genus: np.ndarray, expression: str) -> np.ndarray:
    """Evaluate the simple Stata == / & / | conditions used in assignments."""
    result = np.zeros(len(frame), dtype=bool)
    for disjunction in re.split(r"\s*\|\s*", expression):
        conjunction_mask = np.ones(len(frame), dtype=bool)
        for atom in re.split(r"\s*&\s*", disjunction):
            match = re.fullmatch(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*==\s*(?:"([^"]*)"|([-+\d.eE]+))\s*', atom)
            if not match:
                raise ValueError(f"Unsupported Stata condition in root-ratio mapping: {atom}")
            variable, text_value, numeric_value = match.groups()
            if variable == "ISO":
                mask = np.full(len(frame), iso3 == text_value, dtype=bool)
            elif variable == "continent":
                mask = np.full(len(frame), continent == text_value, dtype=bool)
            elif variable == "genus":
                mask = genus == text_value
            elif numeric_value is not None:
                if variable not in frame:
                    raise KeyError(f"Stata mapping references missing input field {variable!r}")
                values = pd.to_numeric(frame[variable], errors="coerce").to_numpy(dtype=float)
                mask = values == float(numeric_value)
            else:
                raise ValueError(f"Unsupported Stata mapping variable {variable!r}")
            conjunction_mask &= mask
        result |= conjunction_mask
    return result


def mapped_root_ratio(frame: pd.DataFrame, iso3: str, continent: str,
                      genus: np.ndarray, variable: str,
                      rules: dict[str, list[tuple[float, str]]]) -> np.ndarray:
    values = np.full(len(frame), DEFAULT_ROOT_SHOOT_RATIO, dtype=float)
    for value, condition in rules[variable]:
        values[stata_condition(frame, iso3, continent, genus, condition)] = value
    return values


def workbook_price_grid_usd2020() -> np.ndarray:
    """Read only the shared price thresholds; do not read published curves."""
    book = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    sheet = book["Core results"]
    price_rows = list(sheet.iter_rows(min_row=2, max_col=1, values_only=True))
    book.close()
    prices = np.array([row[0] for row in price_rows], dtype=float)
    if (prices.ndim != 1 or not len(prices) or not np.isfinite(prices).all()
            or np.any(np.diff(prices) <= 0)):
        raise ValueError("Invalid restoration price thresholds in the source workbook")
    return prices


def histogram(q: np.ndarray, c: np.ndarray, prices: np.ndarray) -> np.ndarray:
    valid = (q > 0) & np.isfinite(q) & np.isfinite(c)
    indices = np.searchsorted(prices, c[valid], side="left")
    within = indices < len(prices)
    return np.bincount(indices[within], weights=q[valid][within], minlength=len(prices))[:len(prices)]


def select_method(carbon_n: np.ndarray, carbon_p: np.ndarray,
                  buffer_n: np.ndarray, buffer_p: np.ndarray,
                  cost_n: np.ndarray, cost_p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mirror the source method choice using rebuilt carbon and source buffers."""
    efficiency_n = np.divide(carbon_n * buffer_n, cost_n,
                             out=np.full_like(carbon_n, np.nan), where=cost_n != 0)
    efficiency_p = np.divide(carbon_p * buffer_p, cost_p,
                             out=np.full_like(carbon_p, np.nan), where=cost_p != 0)
    choose_p = (efficiency_p > efficiency_n) | (efficiency_p < 0)
    choose_n = (efficiency_n > efficiency_p) & ~choose_p
    return choose_n, choose_p


def target_finance(q_parts: list[np.ndarray], cost_parts: list[np.ndarray],
                   target: float) -> tuple[dict, list[dict]]:
    """Least effective-cost cell allocation, fractional last cell."""
    q = np.concatenate(q_parts) if q_parts else np.empty(0)
    full_cost = np.concatenate(cost_parts) if cost_parts else np.empty(0)
    valid = (q > 0) & np.isfinite(q) & np.isfinite(full_cost)
    q, full_cost = q[valid], full_cost[valid]
    available = float(q.sum())
    result = {"available_discounted_tco2": available,
              "target_coverage_pct": min(100.0, 100 * available / target) if target else np.nan,
              "priced_cells": len(q)}
    effective_cost = full_cost / q
    order = np.argsort(effective_cost, kind="stable")
    sorted_q, sorted_cost, sorted_price = q[order], full_cost[order], effective_cost[order]
    cumulative = np.cumsum(sorted_q)
    cumulative_net = np.cumsum(sorted_cost)
    cumulative_positive = np.cumsum(np.maximum(sorted_cost, 0))
    detailed_curve = []
    if len(cumulative):
        for percentile in range(1, 101):
            volume = available * percentile / 100
            at = min(int(np.searchsorted(cumulative, volume, side="left")), len(cumulative) - 1)
            prior_q = float(cumulative[at - 1]) if at else 0.0
            fraction = (volume - prior_q) / sorted_q[at]
            detailed_curve.append({
                "supply_percentile": percentile,
                "cumulative_discounted_tco2": volume,
                "marginal_effective_cost_usd2015_per_tco2": float(sorted_price[at]),
                "cumulative_net_project_cost_pv_usd2015": (
                    (float(cumulative_net[at - 1]) if at else 0.0)
                    + fraction * sorted_cost[at]),
                "cumulative_positive_project_cost_pv_usd2015": (
                    (float(cumulative_positive[at - 1]) if at else 0.0)
                    + fraction * max(sorted_cost[at], 0)),
            })
    if target <= 0 or available < target:
        result["status"] = "target_outside_cell_supply" if target > 0 else "zero_target"
        return result, detailed_curve
    cutoff = int(np.searchsorted(cumulative, target, side="left"))
    amount_before = float(cumulative[cutoff - 1]) if cutoff else 0.0
    fraction = (target - amount_before) / sorted_q[cutoff]
    economic_cost = float(sorted_cost[:cutoff].sum() + fraction * sorted_cost[cutoff])
    positive_projects = float(np.maximum(sorted_cost[:cutoff], 0).sum()
                              + fraction * max(sorted_cost[cutoff], 0))
    marginal = float(sorted_price[cutoff])
    uniform_payment = max(marginal, 0) * target
    result.update({
        "status": "target_within_cell_supply",
        "marginal_effective_cost_usd2015_per_discounted_tco2": marginal,
        "net_economic_cost_pv_usd2015": economic_cost,
        "positive_project_cost_pv_usd2015": positive_projects,
        "uniform_carbon_payment_pv_usd2015": uniform_payment,
        "selected_cells_with_fractional_last": cutoff + fraction,
        "net_economic_cost_annual_usd2015": economic_cost / SOURCE_FACTOR,
        "positive_project_cost_annual_usd2015": positive_projects / SOURCE_FACTOR,
        "uniform_carbon_payment_annual_usd2015": uniform_payment / SOURCE_FACTOR,
    })
    return result, detailed_curve


def discounted_stand_stock(area: np.ndarray, rate: np.ndarray, age: np.ndarray) -> np.ndarray:
    return area * (1 - np.exp(-rate * age)) ** 2


def discounted_additions(area: np.ndarray, rate: np.ndarray,
                         harvest_year: np.ndarray | None = None) -> np.ndarray:
    total = np.zeros_like(area, dtype=float)
    for year in range(1, HORIZON_YEARS + 1):
        if harvest_year is None:
            age_now = np.full(len(area), year, dtype=int)
            age_before = age_now - 1
        else:
            age_now = year % harvest_year
            age_before = (year - 1) % harvest_year
        addition = (discounted_stand_stock(area, rate, age_now)
                    - discounted_stand_stock(area, rate, age_before))
        total += (1 - DISCOUNT_RATE) ** (year - 1) * addition
    return total


# This implements Stata's selected F=1 rotation rule (scalar at source line 207).
def source_harvest_year(area: np.ndarray, rate: np.ndarray) -> np.ndarray:
    """Reproduce the source harvest-age rule (source lines 279-286)."""
    harvest_year = np.full(len(area), HORIZON_YEARS + 1, dtype=int)
    # Stata loops over t=3..Y and evaluates growth at age a=t-1 (ages 2..Y-1).
    for candidate in range(3, HORIZON_YEARS + 1):
        age = candidate - 1
        previous = discounted_stand_stock(area, rate, np.full(len(area), age - 1))
        current = discounted_stand_stock(area, rate, np.full(len(area), age))
        growth = np.divide(current - previous, previous,
                           out=np.full_like(area, np.nan), where=previous != 0)
        threshold = DISCOUNT_RATE / (1 - (1 + DISCOUNT_RATE) ** (-age))
        harvest_year[growth > threshold] = candidate
    return harvest_year


def plantation_harvested_carbon(area: np.ndarray, rate: np.ndarray,
                                harvest_year: np.ndarray) -> np.ndarray:
    total = np.zeros_like(area, dtype=float)
    for year in range(1, HORIZON_YEARS + 1):
        harvest = (year % harvest_year) == 0
        full_age_stock = discounted_stand_stock(area, rate, np.full(len(area), year))
        total += np.where(harvest, (1 - DISCOUNT_RATE) ** (year - 1) * full_age_stock, 0.0)
    return total


def plantation_establishment_cost(base_cost: np.ndarray,
                                  harvest_year: np.ndarray) -> np.ndarray:
    """Apply the source program's discounted replanting-cost recurrence."""
    total = base_cost.copy()
    for year in range(1, HORIZON_YEARS + 1):
        harvest = (year % harvest_year) == 0
        discounted = (1 - DISCOUNT_RATE) ** (year - 1)
        total = np.where(harvest, total + discounted * total, total)
    return total


def safe_price(cost: np.ndarray, carbon_tco2: np.ndarray) -> np.ndarray:
    return np.divide(cost, carbon_tco2, out=np.full_like(cost, np.nan),
                     where=np.isfinite(carbon_tco2) & (carbon_tco2 > 0))


def process_country(iso3: str, data_file: Path, mappings: tuple,
                    analysis_prices_usd2015: np.ndarray) -> tuple[
                        dict, list[dict], list[dict], list[dict], list[dict], list[dict], dict
                    ]:
    t0 = time.monotonic()
    price_histogram = np.zeros(len(analysis_prices_usd2015))
    q_parts: list[np.ndarray] = []
    cost_parts: list[np.ndarray] = []
    sensitivity = {
        scenario: {
            "rate": rate,
            "hist": np.zeros(len(analysis_prices_usd2015)),
            "q_parts": [],
            "cost_parts": [],
            "nr_cells": 0,
            "plant_cells": 0,
            "method_switches_vs_reference": 0,
        }
        for scenario, rate in NR_SOIL_SENSITIVITY_SCENARIOS.items()
    }
    rows = selected_nr_cells = selected_plant_cells = 0
    country, continents, genus_by_type, root_rules = mappings
    # Missing ISO mappings retain Stata's initialized defaults: w=p=exotic=0.
    country_info = country.get(iso3, {"w": 0.0, "p": 0.0, "exotic": 0.0})
    wood_fraction = country_info["w"]
    wood_revenue_2020 = country_info["p"]
    wood_revenue_2015 = wood_revenue_2020 * USD2020_TO_2015
    continent = continents.get(iso3, "")

    # Import each cell's source values from the country DTA in bounded chunks.
    for chunk in pd.read_stata(data_file, columns=INPUT_COLUMNS,
                               chunksize=200_000, convert_categoricals=False):
        eligible_rows = (~chunk.biomes.isin([13, 14]) & chunk.nr_A.notna() & chunk.type.notna())
        chunk = chunk.loc[eligible_rows].copy()
        if chunk.empty:
            continue
        rows += len(chunk)
        for variable in [name for pair in (
            ("nr_A", "nr_k"), ("pinu_A", "pinu_k"), ("cunn_A", "cunn_k"),
            ("euca_A", "euca_k"), ("brde_A", "brde_k"), ("brev_A", "brev_k"),
            ("nede_A", "nede_k"), ("neev_A", "neev_k"),
        ) for name in pair]:
            # pandas may expose the underlying Stata chunk array as read-only;
            # this cleanup mutates negatives to zero, so make an owned copy.
            values = pd.to_numeric(chunk[variable], errors="coerce").to_numpy(
                dtype=float, copy=True
            )
            values[values < 0] = 0.0
            chunk[variable] = values

        type_values = pd.to_numeric(chunk.type, errors="coerce").to_numpy(dtype=float)
        genus = np.full(len(chunk), "", dtype=object)
        for type_code, name in genus_by_type.items():
            genus[type_values == type_code] = name
        plant_area = np.full(len(chunk), np.nan)
        plant_rate = np.full(len(chunk), np.nan)
        for name in set(genus_by_type.values()):
            selected = genus == name
            plant_area[selected] = pd.to_numeric(chunk.loc[selected, f"{name}_A"], errors="coerce")
            plant_rate[selected] = pd.to_numeric(chunk.loc[selected, f"{name}_k"], errors="coerce")

        natural_area = pd.to_numeric(chunk.nr_A, errors="coerce").to_numpy(dtype=float)
        natural_rate = pd.to_numeric(chunk.nr_k, errors="coerce").to_numpy(dtype=float)
        natural_root_ratio = mapped_root_ratio(
            chunk, iso3, continent, genus, "nr_rootshoot", root_rules
        )
        plant_root_ratio = mapped_root_ratio(
            chunk, iso3, continent, genus, "pl_rootshoot", root_rules
        )
        natural_ag = discounted_additions(natural_area, natural_rate)
        natural_root = natural_ag * natural_root_ratio
        natural_soil = np.full(len(chunk), NR_SOIL_C_PER_YEAR * SOURCE_FACTOR)
        natural_carbon = natural_ag + natural_root + natural_soil

        harvest_year = source_harvest_year(plant_area, plant_rate)
        plant_stock = discounted_additions(plant_area, plant_rate, harvest_year)
        plant_root = plant_stock * plant_root_ratio
        plant_soil = np.zeros(len(chunk))
        for year in range(1, HORIZON_YEARS + 1):
            plant_soil += np.where(
                year < harvest_year,
                (1 - DISCOUNT_RATE) ** (year - 1) * PL_SOIL_C_PER_YEAR,
                0.0,
            )
        plant_harvested = plantation_harvested_carbon(
            plant_area, plant_rate, harvest_year
        )
        plant_carbon = (plant_stock + plant_root + plant_soil
                        + wood_fraction * plant_harvested)

        area_ha = pd.to_numeric(chunk.area_m2, errors="coerce").to_numpy(dtype=float) / 10_000
        general_screen = pd.to_numeric(chunk.griscom, errors="coerce").fillna(0).to_numpy(dtype=float)
        buffer_n = pd.to_numeric(chunk.nr_buffer, errors="coerce").fillna(0).to_numpy(dtype=float)
        buffer_p = pd.to_numeric(chunk.pl_buffer, errors="coerce").fillna(0).to_numpy(dtype=float)
        bau = sum(
            pd.to_numeric(chunk[column], errors="coerce").to_numpy(dtype=float) * weight
            for column, weight in zip(
                ("bau_2020_2030", "bau_2030_2040", "bau_2040_2050"), BAU_WEIGHTS
            )
        )
        bau = np.where(np.isfinite(bau), bau, BAU_DEFAULT)
        additional_fraction = 1 - bau
        # Source DTA costs are in USD 2020; convert once to USD 2015.
        crop_value_2020 = pd.to_numeric(chunk.crop_va, errors="coerce").to_numpy(dtype=float)
        crop_value_2015 = crop_value_2020 * USD2020_TO_2015
        crop_cost_2015 = crop_value_2015 * SOURCE_FACTOR
        nr_cost_input = pd.to_numeric(chunk.nr_cost, errors="coerce").to_numpy(dtype=float)
        nr_cost_2015 = nr_cost_input * USD2020_TO_2015
        exotic = country_info["exotic"]
        np_cost_input = pd.to_numeric(chunk.np_cost, errors="coerce").to_numpy(dtype=float)
        ep_cost_input = pd.to_numeric(chunk.ep_cost, errors="coerce").to_numpy(dtype=float)
        np_cost_2015 = np_cost_input * USD2020_TO_2015
        ep_cost_2015 = ep_cost_input * USD2020_TO_2015
        plant_cost_base_2015 = exotic * ep_cost_2015 + (1 - exotic) * np_cost_2015
        plant_cost_base_2015[genus == "cunn"] = ep_cost_2015[genus == "cunn"]
        plant_cost_base_2015[(genus == "cunn") & (iso3 == "CHN")] = np_cost_2015[(genus == "cunn") & (iso3 == "CHN")]
        plant_cost_base_2015[genus == "euca"] = ep_cost_2015[genus == "euca"]
        plant_cost_2015 = plantation_establishment_cost(plant_cost_base_2015, harvest_year)

        net_cost_n_2015 = crop_cost_2015 + nr_cost_2015
        net_cost_p_2015 = (
            crop_cost_2015 + plant_cost_2015 - wood_revenue_2015 * plant_harvested
        )
        selected_nr, selected_plant = select_method(
            natural_carbon, plant_carbon, buffer_n, buffer_p,
            net_cost_n_2015, net_cost_p_2015,
        )
        selected_nr_cells += int(selected_nr.sum())
        selected_plant_cells += int(selected_plant.sum())

        selected_carbon = np.where(
            selected_plant, plant_carbon,
            np.where(selected_nr, natural_carbon, 0.0),
        )
        selected_buffer = np.where(
            selected_plant, buffer_p, np.where(selected_nr, buffer_n, 0.0)
        )
        selected_cost_2015 = np.where(
            selected_plant, net_cost_p_2015,
            np.where(selected_nr, net_cost_n_2015, np.nan),
        )
        quantity_tco2 = (
            selected_carbon * area_ha * general_screen * selected_buffer
            * additional_fraction * CARBON_TO_CO2
        )
        price_usd2015 = safe_price(selected_cost_2015, CARBON_TO_CO2 * selected_carbon)
        price_histogram += histogram(
            quantity_tco2, price_usd2015, analysis_prices_usd2015
        )
        full_cell_cost_2015 = selected_cost_2015 * area_ha
        finance_eligible = ((quantity_tco2 > 0) & np.isfinite(price_usd2015)
                            & np.isfinite(full_cell_cost_2015))
        if finance_eligible.any():
            q_parts.append(quantity_tco2[finance_eligible].astype(np.float64))
            cost_parts.append(full_cell_cost_2015[finance_eligible].astype(np.float64))
        baseline = sensitivity["busch_reference"]
        baseline["hist"] += histogram(quantity_tco2, price_usd2015, analysis_prices_usd2015)
        baseline["nr_cells"] += int(selected_nr.sum())
        baseline["plant_cells"] += int(selected_plant.sum())
        if finance_eligible.any():
            baseline["q_parts"].append(quantity_tco2[finance_eligible].astype(np.float64))
            baseline["cost_parts"].append(full_cell_cost_2015[finance_eligible].astype(np.float64))

        for scenario, state in sensitivity.items():
            if scenario == "busch_reference":
                continue
            natural_scenario_c = (
                natural_ag + natural_root + state["rate"] * SOURCE_FACTOR
            )
            choose_n, choose_p = select_method(
                natural_scenario_c, plant_carbon, buffer_n, buffer_p,
                net_cost_n_2015, net_cost_p_2015,
            )
            state["method_switches_vs_reference"] += int(
                ((choose_n != selected_nr) | (choose_p != selected_plant)).sum()
            )
            scenario_carbon = np.where(
                choose_p, plant_carbon,
                np.where(choose_n, natural_scenario_c, 0.0),
            )
            scenario_buffer = np.where(
                choose_p, buffer_p, np.where(choose_n, buffer_n, 0.0)
            )
            scenario_cost = np.where(
                choose_p, net_cost_p_2015,
                np.where(choose_n, net_cost_n_2015, np.nan),
            )
            scenario_q_tco2 = (
                scenario_carbon * area_ha * general_screen * scenario_buffer
                * additional_fraction * CARBON_TO_CO2
            )
            scenario_price = safe_price(
                scenario_cost, CARBON_TO_CO2 * scenario_carbon
            )
            state["hist"] += histogram(
                scenario_q_tco2, scenario_price, analysis_prices_usd2015
            )
            state["nr_cells"] += int(choose_n.sum())
            state["plant_cells"] += int(choose_p.sum())
            scenario_full_cell_cost_2015 = scenario_cost * area_ha
            scenario_eligible = (
                (scenario_q_tco2 > 0) & np.isfinite(scenario_price)
                & np.isfinite(scenario_full_cell_cost_2015)
            )
            if scenario_eligible.any():
                state["q_parts"].append(
                    scenario_q_tco2[scenario_eligible].astype(np.float64)
                )
                state["cost_parts"].append(
                    scenario_full_cell_cost_2015[scenario_eligible].astype(np.float64)
                )

    record = {
        "iso3": iso3, "output_cells": rows, "wood_fraction_w": wood_fraction,
        "wood_revenue_coefficient_p_usd2015_per_tC": wood_revenue_2015,
        "selected_natural_regeneration_cells": selected_nr_cells,
        "selected_plantation_cells": selected_plant_cells,
        "available_discounted_tco2": float(sum(part.sum() for part in q_parts)),
        "runtime_seconds": round(time.monotonic() - t0, 2),
    }
    baseline_finance, detailed_curve = target_finance(q_parts, cost_parts, 0.0)
    record["available_discounted_tco2"] = baseline_finance["available_discounted_tco2"]
    cumulative_supply = np.cumsum(price_histogram)
    curves = [{
        "iso3": iso3,
        "price_usd2015_per_tco2": float(price),
        "cell_supply_discounted_tco2": float(price_histogram[j]),
        "cumulative_supply_discounted_tco2": float(cumulative_supply[j]),
    } for j, price in enumerate(analysis_prices_usd2015)]
    sensitivity_records: list[dict] = []
    sensitivity_curves: list[dict] = []
    sensitivity_effective_curves: list[dict] = []
    for scenario, state in sensitivity.items():
        cumulative_supply = np.cumsum(state["hist"])
        scenario_finance, scenario_details = target_finance(
            state["q_parts"], state["cost_parts"], 0.0
        )
        scenario_record = {
            "iso3": iso3,
            "soil_scenario": scenario,
            "nr_soil_rate_tC_ha_yr": state["rate"],
            "plantation_soil_rate_tC_ha_yr": PL_SOIL_C_PER_YEAR,
            "natural_regeneration_cells_selected": state["nr_cells"],
            "plantation_cells_selected": state["plant_cells"],
            "method_switches_vs_reference": state["method_switches_vs_reference"],
            "available_discounted_tco2": float(cumulative_supply[-1]),
        }
        sensitivity_records.append(scenario_record)
        sensitivity_curves.extend({
            "iso3": iso3,
            "soil_scenario": scenario,
            "nr_soil_rate_tC_ha_yr": state["rate"],
            "price_usd2015_per_tco2": float(price),
            "cell_supply_discounted_tco2": float(state["hist"][j]),
            "cumulative_supply_discounted_tco2": float(cumulative_supply[j]),
        } for j, price in enumerate(analysis_prices_usd2015))
        sensitivity_effective_curves.extend({
            "iso3": iso3,
            "soil_scenario": scenario,
            "nr_soil_rate_tC_ha_yr": state["rate"],
            **row,
        } for row in scenario_details)
    finance_arrays = {
        "reference_q": np.concatenate(q_parts) if q_parts else np.empty(0, dtype=np.float64),
        "reference_cost": np.concatenate(cost_parts) if cost_parts else np.empty(0, dtype=np.float64),
    }
    for scenario, state in sensitivity.items():
        finance_arrays[f"{scenario}_q"] = (
            np.concatenate(state["q_parts"]) if state["q_parts"] else np.empty(0, dtype=np.float64)
        )
        finance_arrays[f"{scenario}_cost"] = (
            np.concatenate(state["cost_parts"]) if state["cost_parts"] else np.empty(0, dtype=np.float64)
        )
    return (
        record,
        curves,
        [{"iso3": iso3, **row} for row in detailed_curve],
        sensitivity_records,
        sensitivity_curves,
        sensitivity_effective_curves,
        finance_arrays,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--countries", nargs="*", help="ISO3 subset; default every country DTA in the archive")
    parser.add_argument("--label", default="all_dta")
    args = parser.parse_args()
    if args.countries and args.label == "all_dta":
        parser.error("--countries creates a partial run; choose a diagnostic --label other than 'all_dta'")
    if not INPUT_ZIP.is_file():
        raise FileNotFoundError(f"{INPUT_ZIP}; run code/scripts/download_busch_inputs.py first")
    if INPUT_ZIP.stat().st_size != INPUT_ARCHIVE_SIZE:
        raise RuntimeError(
            f"Unexpected Busch input archive size: {INPUT_ZIP.stat().st_size}; "
            f"expected {INPUT_ARCHIVE_SIZE} bytes"
        )
    HERE.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    initial_hashes = input_hashes()
    if ALLOCATIONS.is_file():
        allocations = pd.read_csv(ALLOCATIONS)
        positive_loss = allocations.loc[
            allocations.reported_deforestation.eq(True) & allocations.lost_capacity_tco2_yr.gt(0)
        ].copy()
        initial_target_join_hash = hashlib.sha256(ALLOCATIONS.read_bytes()).hexdigest()
    else:
        allocations = pd.DataFrame(columns=[
            "iso3", "name", "groups", "reported_deforestation", "lost_capacity_tco2_yr",
            "our_2pct_gcw_allocation_usd2015_yr",
        ])
        positive_loss = allocations.copy()
        initial_target_join_hash = None
    if positive_loss.iso3.duplicated().any():
        duplicates = positive_loss.loc[positive_loss.iso3.duplicated(), "iso3"].tolist()
        raise ValueError(f"Positive FRA-loss target input has duplicate ISO3 keys: {duplicates}")
    source_price_grid_usd2020 = workbook_price_grid_usd2020()
    analysis_prices_usd2015 = source_price_grid_usd2020 * USD2020_TO_2015
    mappings = source_mappings()
    table_schemas = {
        "country_finance": [
            "iso3", "output_cells", "wood_fraction_w",
            "wood_revenue_coefficient_p_usd2015_per_tC",
            "selected_natural_regeneration_cells", "selected_plantation_cells",
            "available_discounted_tco2", "runtime_seconds",
        ],
        "25_price_curves": [
            "iso3", "price_usd2015_per_tco2", "cell_supply_discounted_tco2",
            "cumulative_supply_discounted_tco2",
        ],
        "effective_cost_curves": [
            "iso3", "supply_percentile", "cumulative_discounted_tco2",
            "marginal_effective_cost_usd2015_per_tco2",
            "cumulative_net_project_cost_pv_usd2015",
            "cumulative_positive_project_cost_pv_usd2015",
        ],
        "soil_sensitivity_country": [
            "iso3", "soil_scenario", "nr_soil_rate_tC_ha_yr",
            "plantation_soil_rate_tC_ha_yr", "natural_regeneration_cells_selected",
            "plantation_cells_selected", "method_switches_vs_reference",
            "available_discounted_tco2",
        ],
        "soil_sensitivity_price_curves": [
            "iso3", "soil_scenario", "nr_soil_rate_tC_ha_yr",
            "price_usd2015_per_tco2", "cell_supply_discounted_tco2",
            "cumulative_supply_discounted_tco2",
        ],
        "soil_sensitivity_effective_cost_curves": [
            "iso3", "soil_scenario", "nr_soil_rate_tC_ha_yr",
            "supply_percentile", "cumulative_discounted_tco2",
            "marginal_effective_cost_usd2015_per_tco2",
            "cumulative_net_project_cost_pv_usd2015",
            "cumulative_positive_project_cost_pv_usd2015",
        ],
    }

    def append_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
        if not path.exists():
            pd.DataFrame(columns=columns).to_csv(path, index=False)
        if rows:
            pd.DataFrame(rows).reindex(columns=columns).to_csv(
                path, mode="a", header=False, index=False
            )

    def publish_csv(source: Path, filename: str) -> None:
        destination = HERE / filename
        temporary = HERE / f".{filename}.{time.time_ns()}.tmp"
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)

    with zipfile.ZipFile(INPUT_ZIP) as archive:
        members: dict[str, str] = {}
        for member in archive.namelist():
            match = re.search(r"(?:^|/)(?:maps_)?([A-Z]{3})\.dta$", member)
            if match:
                iso3 = match.group(1)
                if iso3 in members:
                    raise ValueError(f"More than one country DTA found for {iso3}: {members[iso3]}, {member}")
                members[iso3] = member
        selected_iso3 = sorted(members)
        if args.countries:
            requested = set(args.countries)
            unknown = sorted(requested - set(members))
            if unknown:
                raise ValueError(f"Requested country DTA files are absent from the archive: {unknown}")
            selected_iso3 = sorted(requested)
        run_complete = len(selected_iso3) == len(members)
        with tempfile.TemporaryDirectory(prefix=f"busch_{args.label}_", dir=CACHE) as temp_name:
            staging = Path(temp_name)
            table_paths = {
                table: staging / f"{table}.csv.partial"
                for table in table_schemas
            }
            for table, columns in table_schemas.items():
                append_rows(table_paths[table], [], columns)

            for n, iso3 in enumerate(selected_iso3, 1):
                country_data = staging / f"{iso3}.dta"
                with archive.open(members[iso3]) as source, country_data.open("wb") as dest:
                    shutil.copyfileobj(source, dest, 16 * 1024 * 1024)
                try:
                    (
                        record,
                        curves,
                        detailed_curve,
                        scenario_records,
                        scenario_curves,
                        scenario_effective_curves,
                        finance_arrays,
                    ) = process_country(
                        iso3, country_data, mappings, analysis_prices_usd2015,
                    )
                    append_rows(table_paths["country_finance"], [record], table_schemas["country_finance"])
                    append_rows(table_paths["25_price_curves"], curves, table_schemas["25_price_curves"])
                    append_rows(
                        table_paths["effective_cost_curves"], detailed_curve,
                        table_schemas["effective_cost_curves"],
                    )
                    append_rows(
                        table_paths["soil_sensitivity_country"], scenario_records,
                        table_schemas["soil_sensitivity_country"],
                    )
                    append_rows(
                        table_paths["soil_sensitivity_price_curves"], scenario_curves,
                        table_schemas["soil_sensitivity_price_curves"],
                    )
                    append_rows(
                        table_paths["soil_sensitivity_effective_cost_curves"],
                        scenario_effective_curves,
                        table_schemas["soil_sensitivity_effective_cost_curves"],
                    )
                    np.savez_compressed(staging / f"{iso3}_finance_arrays.npz", **finance_arrays)
                    print(
                        f"[costs {n}/{len(selected_iso3)}] {iso3} "
                        f"cells={record['output_cells']} "
                        f"available={record['available_discounted_tco2']:.6g} tCO2 "
                        f"{record['runtime_seconds']}s",
                        flush=True,
                    )
                finally:
                    country_data.unlink(missing_ok=True)

            # Phase 2 starts only after all selected country DTA calculations finish.
            # FRA losses select targets here; they never select which country costs run.
            processed_set = set(selected_iso3)
            coverage_rows: list[dict] = []
            sensitivity_coverage_rows: list[dict] = []
            for target_row in positive_loss.itertuples(index=False):
                iso3 = str(target_row.iso3)
                base = {
                    "iso3": iso3,
                    "name": getattr(target_row, "name", iso3),
                    "groups": getattr(target_row, "groups", np.nan),
                    "reported_loss_capacity_tco2_yr": float(target_row.lost_capacity_tco2_yr),
                    "target_discounted_30yr_tco2": float(target_row.lost_capacity_tco2_yr) * SOURCE_FACTOR,
                    "our_2pct_gcw_allocation_usd2015_yr": getattr(
                        target_row, "our_2pct_gcw_allocation_usd2015_yr", np.nan
                    ),
                    "country_dta_available": iso3 in members,
                    "cell_input_available": iso3 in processed_set,
                }
                array_path = staging / f"{iso3}_finance_arrays.npz"
                if iso3 not in processed_set or not array_path.is_file():
                    status = "not_processed_this_run" if iso3 in members else "no_country_input_dta"
                    coverage_rows.append({**base, "status": status})
                    for scenario, rate in NR_SOIL_SENSITIVITY_SCENARIOS.items():
                        sensitivity_coverage_rows.append({
                            **base,
                            "soil_scenario": scenario,
                            "nr_soil_rate_tC_ha_yr": rate,
                            "status": status,
                        })
                    continue

                target = base["target_discounted_30yr_tco2"]
                with np.load(array_path) as arrays:
                    target_result, _ = target_finance(
                        [arrays["reference_q"]], [arrays["reference_cost"]], target
                    )
                    coverage_rows.append({**base, **target_result})
                    for scenario, rate in NR_SOIL_SENSITIVITY_SCENARIOS.items():
                        scenario_result, _ = target_finance(
                            [arrays[f"{scenario}_q"]],
                            [arrays[f"{scenario}_cost"]],
                            target,
                        )
                        sensitivity_coverage_rows.append({
                            **base,
                            "soil_scenario": scenario,
                            "nr_soil_rate_tC_ha_yr": rate,
                            **scenario_result,
                        })
                print(f"[FRA join {iso3}] {target_result['status']}", flush=True)

            coverage = pd.DataFrame(coverage_rows)
            coverage = ensure_columns(coverage, [
                "iso3", "name", "groups", "reported_loss_capacity_tco2_yr",
                "target_discounted_30yr_tco2", "our_2pct_gcw_allocation_usd2015_yr",
                "country_dta_available", "cell_input_available", "status",
                "available_discounted_tco2", "target_coverage_pct", "priced_cells",
                "marginal_effective_cost_usd2015_per_discounted_tco2",
                "net_economic_cost_pv_usd2015", "positive_project_cost_pv_usd2015",
                "uniform_carbon_payment_pv_usd2015", "selected_cells_with_fractional_last",
                "net_economic_cost_annual_usd2015", "positive_project_cost_annual_usd2015",
                "uniform_carbon_payment_annual_usd2015",
            ])
            coverage["allocation_over_positive_project_cost"] = np.divide(
                coverage.our_2pct_gcw_allocation_usd2015_yr,
                coverage.positive_project_cost_annual_usd2015,
                out=np.full(len(coverage), np.nan),
                where=coverage.positive_project_cost_annual_usd2015.gt(0),
            )
            coverage["allocation_over_uniform_payment"] = np.divide(
                coverage.our_2pct_gcw_allocation_usd2015_yr,
                coverage.uniform_carbon_payment_annual_usd2015,
                out=np.full(len(coverage), np.nan),
                where=coverage.uniform_carbon_payment_annual_usd2015.gt(0),
            )
            coverage["figure4c_category"] = np.select(
                [
                    coverage.status.eq("no_country_input_dta"),
                    coverage.status.eq("target_outside_cell_supply"),
                    coverage.status.eq("target_within_cell_supply")
                    & coverage.marginal_effective_cost_usd2015_per_discounted_tco2.gt(0),
                    coverage.status.eq("target_within_cell_supply"),
                ],
                ["No country input DTA", "Insufficient modelled supply",
                 "Target within supply; positive marginal cost",
                 "Target within supply; non-positive marginal cost"],
                default="Not assessed",
            )
            if len(coverage):
                figure4c = coverage.groupby("figure4c_category", dropna=False).agg(
                    country_units=("iso3", "count"),
                    annual_lost_capacity_tco2=("reported_loss_capacity_tco2_yr", "sum"),
                    gcw_2pct_allocation_usd2015_per_year=("our_2pct_gcw_allocation_usd2015_yr", "sum"),
                ).reset_index()
            else:
                figure4c = pd.DataFrame(columns=[
                    "figure4c_category", "country_units", "annual_lost_capacity_tco2",
                    "gcw_2pct_allocation_usd2015_per_year", "share_of_positive_loss_pct",
                ])
            total_loss = float(coverage.reported_loss_capacity_tco2_yr.sum())
            if len(figure4c):
                figure4c["share_of_positive_loss_pct"] = (
                    100 * figure4c.annual_lost_capacity_tco2 / total_loss if total_loss else np.nan
                )

            if input_hashes() != initial_hashes:
                raise RuntimeError("A cell-cost input file changed during reconstruction")
            target_join_hash = (
                hashlib.sha256(ALLOCATIONS.read_bytes()).hexdigest()
                if ALLOCATIONS.is_file() else None
            )
            if target_join_hash != initial_target_join_hash:
                raise RuntimeError("The FRA-loss target/allocation file changed during reconstruction")
            archive_country_dta_codes = sorted(members)
            summary = {
                "archive_country_dta_count": len(members),
                "processed_country_dta_count": len(selected_iso3),
                "processed_units": len(selected_iso3),
                "processing_scope_complete": run_complete,
                "archive_country_dta_codes": archive_country_dta_codes,
                "processed_country_dta_codes": selected_iso3,
                "positive_loss_entities": len(positive_loss),
                "positive_loss_entities_with_dta": len(set(positive_loss.iso3) & set(members)),
                "positive_loss_entities_without_dta": len(set(positive_loss.iso3) - set(members)),
                "positive_loss_entities_processed_this_run": int(coverage.cell_input_available.sum()),
                "positive_loss_targets_within_supply": int(
                    coverage.status.eq("target_within_cell_supply").sum()
                ),
                "discount_factor_source": SOURCE_FACTOR,
                "discount_factor_conventional_sensitivity": CONVENTIONAL_FACTOR,
                "nr_soil_sensitivity_scenarios_tC_ha_yr": NR_SOIL_SENSITIVITY_SCENARIOS,
                "bau_weights_by_period": dict(zip(
                    ("bau_2020_2030", "bau_2030_2040", "bau_2040_2050"), BAU_WEIGHTS
                )),
                "bau_default_when_source_value_missing": BAU_DEFAULT,
                "plantation_soil_rate_fixed_tC_ha_yr": PL_SOIL_C_PER_YEAR,
                "analysis_cost_currency": "USD2015",
                "usd2020_to_usd2015_conversion_applied_before_cost_calculation": True,
                "price_thresholds_source_currency": "USD2020",
                "price_thresholds_analysis_currency": "USD2015",
                "source_workbook_use": "shared price-threshold column only; country curves are not loaded",
                "published_curve_comparison_performed": False,
                "country_costs_calculated_for_all_archive_dta_before_loss_join": run_complete,
                "analysis_order": [
                    "calculate each country DTA independently of FRA loss and our study entity coverage",
                    "after those calculations finish, join available positive FRA-loss targets by ISO3",
                ],
                "soil_sensitivity_country_rows": int(len(selected_iso3) * len(NR_SOIL_SENSITIVITY_SCENARIOS)),
                "soil_sensitivity_coverage_rows": len(sensitivity_coverage_rows),
                "usd2020_to_usd2015_factor": USD2020_TO_2015,
                "input_sha256": initial_hashes,
                "target_join_input_sha256": target_join_hash,
                "source_archive_zenodo": INPUT_ARCHIVE_URL,
                "source_archive_md5": INPUT_ARCHIVE_MD5,
                "source_code_parameters": (
                    "Transcribed from Busch et al., `1. Model loop all data.do`; "
                    "see code/scripts/busch_stata_parameters.py."
                ),
                "method_status": "direct cost reconstruction from all available public country-level cell inputs",
            }

            output_files = {
                "country_finance": f"busch_{args.label}_country_finance.csv",
                "25_price_curves": f"busch_{args.label}_25_price_curves.csv",
                "effective_cost_curves": f"busch_{args.label}_effective_cost_curves.csv",
                "soil_sensitivity_country": f"busch_{args.label}_soil_sensitivity_country.csv",
                "soil_sensitivity_price_curves": f"busch_{args.label}_soil_sensitivity_price_curves.csv",
                "soil_sensitivity_effective_cost_curves": f"busch_{args.label}_soil_sensitivity_effective_cost_curves.csv",
            }
            for table, filename in output_files.items():
                publish_csv(table_paths[table], filename)
            coverage.to_csv(staging / "coverage.csv", index=False)
            sensitivity_coverage = pd.DataFrame(sensitivity_coverage_rows)
            sensitivity_coverage = ensure_columns(sensitivity_coverage, [
                "iso3", "name", "groups", "reported_loss_capacity_tco2_yr",
                "target_discounted_30yr_tco2", "our_2pct_gcw_allocation_usd2015_yr",
                "country_dta_available", "cell_input_available", "soil_scenario",
                "nr_soil_rate_tC_ha_yr", "status", "available_discounted_tco2",
                "target_coverage_pct", "priced_cells",
                "marginal_effective_cost_usd2015_per_discounted_tco2",
                "net_economic_cost_pv_usd2015", "positive_project_cost_pv_usd2015",
                "uniform_carbon_payment_pv_usd2015", "selected_cells_with_fractional_last",
                "net_economic_cost_annual_usd2015", "positive_project_cost_annual_usd2015",
                "uniform_carbon_payment_annual_usd2015",
            ])
            sensitivity_coverage.to_csv(staging / "soil_sensitivity_coverage.csv", index=False)
            figure4c.to_csv(staging / "figure4c_candidate.csv", index=False)
            for filename in ("coverage.csv", "soil_sensitivity_coverage.csv", "figure4c_candidate.csv"):
                suffix = {
                    "coverage.csv": f"busch_{args.label}_coverage.csv",
                    "soil_sensitivity_coverage.csv": f"busch_{args.label}_soil_sensitivity_coverage.csv",
                    "figure4c_candidate.csv": f"busch_{args.label}_figure4c_candidate.csv",
                }[filename]
                publish_csv(staging / filename, suffix)

            summary_path = HERE / f"busch_{args.label}_summary.json"
            summary_temp = HERE / f".{summary_path.name}.{time.time_ns()}.tmp"
            summary_temp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(summary_temp, summary_path)
            print(json.dumps({k: v for k, v in summary.items() if k != "input_sha256"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
