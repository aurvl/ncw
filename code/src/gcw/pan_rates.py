"""Q: Which carbon uptake rate (tC/ha/yr, mean and sd) applies to each harmonised biome?

Rates are built entirely on Pan et al. (2024):
    q_b = Phi_b / A_b^Pan
- Phi_b: Table 1 flux for PAN_PERIOD (Pg C/yr); the tropical flux is the "All tropical forests" row,
  i.e. intact + regrowth, so no FAO forest type is matched to Pan categories;
- A_b^Pan: mean of the 2010 and 2020 Pan areas of the biome (Extended Data Table 1).

Outputs (data/derived/):
- pan_biome_flux.csv  : Pan Table 1 fluxes used and checked
- biome_rates.csv     : one rate per Pan biome (tropical, temperate, boreal)
- pan_rate_checks.csv : q_b x A_b^Pan versus Phi_b, and q_b versus Pan's published rate per area
"""

from __future__ import annotations

import re

import pandas as pd

from .config import FOREST_OUTPUT, PAN_AREA_YEARS, PAN_BIOME_AREAS_CSV, PAN_BIOME_ROWS, PAN_PERIOD, PAN_TABLE1_HTML
from .validation import write_table

PG_TO_T = 1e9
MHA_TO_HA = 1e6
CHECK_ROWS = ["Tropical intact forest", "Tropical regrowth forest", *PAN_BIOME_ROWS.values()]


def _mean_sd(cell: str) -> tuple[float, float]:
    numbers = re.findall(r"[−-]?\d+(?:\.\d+)?", str(cell))
    mean, sd = (float(n.replace("−", "-")) for n in numbers[:2])
    return mean, sd


def read_pan_table1() -> pd.DataFrame:
    table = pd.read_html(PAN_TABLE1_HTML, encoding="utf-8")[0]
    label_column = table.columns[0]
    period_digits = re.sub(r"\D", "", PAN_PERIOD)
    period_column = next(c for c in table.columns if period_digits in re.sub(r"\D", "", str(c)))
    rows = table.drop_duplicates(subset=label_column, keep="first")
    rows = rows.loc[rows[label_column].isin(CHECK_ROWS)]
    records = []
    for _, row in rows.iterrows():
        mean, sd = _mean_sd(row[period_column])
        records.append({"pan_row": row[label_column], "period": PAN_PERIOD, "flux_pgc_yr_mean": mean, "flux_pgc_yr_sd": sd})
    return pd.DataFrame(records)


def pan_areas() -> pd.DataFrame:
    areas = pd.read_csv(PAN_BIOME_AREAS_CSV)
    areas["area_ha"] = areas[PAN_AREA_YEARS].mean(axis=1) * MHA_TO_HA
    return areas.rename(columns={"pan_biome_row": "pan_row"})


def build_rates(flux: pd.DataFrame, areas: pd.DataFrame) -> pd.DataFrame:
    merged = flux.merge(areas, on="pan_row", how="inner", validate="one_to_one")
    records = []
    for biome, pan_row in PAN_BIOME_ROWS.items():
        row = merged.set_index("pan_row").loc[pan_row]
        records.append({
            "pan_biome": biome,
            "pan_row": pan_row,
            "flux_pgc_yr_mean": row["flux_pgc_yr_mean"],
            "flux_pgc_yr_sd": row["flux_pgc_yr_sd"],
            "pan_area_ha": row["area_ha"],
            "rate_tc_ha_yr_mean": row["flux_pgc_yr_mean"] * PG_TO_T / row["area_ha"],
            "rate_tc_ha_yr_sd": row["flux_pgc_yr_sd"] * PG_TO_T / row["area_ha"],
            "source": f"Pan et al. (2024) Table 1 ({PAN_PERIOD}) / mean Pan area 2010-2020 (Extended Data Table 1)",
        })
    return pd.DataFrame(records)


def rate_checks(flux: pd.DataFrame, areas: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Checks performed before rates are applied to FRA x GEZ country areas."""
    records = []
    for _, rate in rates.iterrows():
        reproduced = rate["rate_tc_ha_yr_mean"] * rate["pan_area_ha"] / PG_TO_T
        records.append({
            "check": f"{rate['pan_row']}: rate x Pan area reproduces Pan flux (Pg C/yr)",
            "value": reproduced, "reference": rate["flux_pgc_yr_mean"], "ok": abs(reproduced - rate["flux_pgc_yr_mean"]) < 1e-9,
        })
    merged = flux.merge(areas, on="pan_row")
    merged["rate"] = merged["flux_pgc_yr_mean"] * PG_TO_T / merged["area_ha"]
    for _, row in merged.iterrows():
        records.append({
            "check": f"{row['pan_row']}: derived rate matches Pan Extended Data Table 3 (tC/ha/yr, rounded to 0.01)",
            "value": row["rate"], "reference": row["published_rate_2010_2019_mgc_ha_yr"],
            "ok": abs(row["rate"] - row["published_rate_2010_2019_mgc_ha_yr"]) <= 0.006,
        })
    tropical = flux.set_index("pan_row")["flux_pgc_yr_mean"]
    parts = tropical["Tropical intact forest"] + tropical["Tropical regrowth forest"]
    records.append({
        "check": "All tropical forests flux equals intact + regrowth (Pg C/yr)",
        "value": parts, "reference": tropical["All tropical forests"], "ok": abs(parts - tropical["All tropical forests"]) < 0.011,
    })
    return pd.DataFrame(records)


def run() -> pd.DataFrame:
    flux = read_pan_table1()
    output_dir = FOREST_OUTPUT / "pan"
    write_table(flux, output_dir / "pan_biome_flux.csv")
    areas = pan_areas()
    rates = build_rates(flux, areas)
    write_table(rates, output_dir / "biome_rates.csv")
    checks = rate_checks(flux, areas, rates)
    write_table(checks, output_dir / "pan_rate_checks.csv")
    if not checks["ok"].all():
        raise ValueError(f"Pan rate checks failed:\n{checks.loc[~checks['ok']].to_string(index=False)}")
    return rates
