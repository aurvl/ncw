"""Q: What do the main tables of the paper show?

All aggregates are summed draw by draw before being summarised (C8).
Outputs (output/tables/):
- table1_global_by_ecosystem.csv  : tCO2/yr and US$2015/yr per ecosystem, BCW, GCW and NCW
- table2_by_continent.csv         : GCW, BCW, NCW by continent
- table3_by_group.csv             : GCW, BCW, NCW by economic group
- table4_top_territories.csv      : 20 largest NCW territories
- table5_route_a_faostat.csv      : complementary FAOSTAT net flux (global and extremes)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BCW_COUNTRY_CSV, BCW_DRAWS_NPZ, CARBON_TO_CO2, TABLES
from .validation import sum_draws, summarise_draws, write_table


def _row(label: str, draws_1d: np.ndarray, unit: str, note: str = "") -> dict:
    stats = summarise_draws(np.asarray(draws_1d)[None, :], "value").iloc[0].to_dict()
    return {"item": label, "unit": unit, **stats, "note": note}


def global_by_ecosystem(forest: dict, faostat: pd.DataFrame, gcw: dict, ncw: dict) -> pd.DataFrame:
    gscc = gcw["gscc"].astype(np.float64)
    with np.load(BCW_DRAWS_NPZ, allow_pickle=True) as archive:
        coastal = {
            name: np.nansum(archive[f"bce_{key}_draws"], axis=0) * CARBON_TO_CO2
            for name, key in [("Mangroves", "mangroves"), ("Seagrasses", "seagrasses"), ("Saltmarshes", "saltmarshes")]
        }
    bcp_tco2 = pd.read_csv(BCW_COUNTRY_CSV)["BCP Seq (tC)"].sum() * CARBON_TO_CO2
    flows = {
        "Forests excl. mangroves (Gibbs/GFW gross living biomass)": np.nansum(forest["excl_mangroves"], axis=0),
        **coastal,
        "Open ocean biological carbon pump": np.full(gscc.shape, bcp_tco2),
    }
    flows["Mangroves"] = flows["Mangroves"] + np.nansum(ncw["bcw_mangrove_gapfill_tco2_yr"], axis=0)
    notes = {
        "Open ocean biological carbon pump": "BCW point estimate, no physical uncertainty",
        "Mangroves": "BCW coastal draws + FRA-area gap-fill for units without BCW mangroves (C18)",
    }
    rows = []
    for label, tco2 in flows.items():
        rows.append(_row(label, tco2, "tCO2/yr", notes.get(label, "")))
        rows.append(_row(label, tco2 * gscc, "US$2015/yr", notes.get(label, "")))
    rows.append(_row("GCW (Gibbs/GFW main estimate)", np.nansum(ncw["gcw_usd2015_yr"], axis=0), "US$2015/yr"))
    rows.append(_row("BCW (published + mangrove gap-fill, C18)", np.nansum(ncw["bcw_usd2015_yr"], axis=0), "US$2015/yr"))
    rows.append(_row("NCW = GCW + BCW", np.nansum(ncw["ncw_usd2015_yr"], axis=0), "US$2015/yr"))
    faostat_tco2 = faostat["net_uptake_tco2_yr"].sum()
    rows.append(_row("Forests net flux (Route A, FAOSTAT)", np.full(gscc.shape, faostat_tco2), "tCO2/yr", "complementary analysis"))
    rows.append(_row("Forests net flux (Route A, FAOSTAT)", faostat_tco2 * gscc, "US$2015/yr", "complementary analysis"))
    return pd.DataFrame(rows)


def by_group(ncw_table: pd.DataFrame, ncw: dict, column: str) -> pd.DataFrame:
    groups = ncw_table.set_index("iso3").reindex(ncw["iso3"])[column].reset_index(drop=True)
    if column == "continent":
        fallback = ncw_table.set_index("iso3").reindex(ncw["iso3"])["fra_region"].reset_index(drop=True)
        groups = groups.fillna(fallback)
    groups = groups.fillna("Unclassified")
    frames = []
    world = {key: np.nansum(ncw[key], axis=0) for key in ["gcw_usd2015_yr", "bcw_usd2015_yr", "ncw_usd2015_yr"]}
    for key in ["gcw_usd2015_yr", "bcw_usd2015_yr", "ncw_usd2015_yr"]:
        labels, summed = sum_draws(np.nan_to_num(ncw[key]), groups)
        summary = summarise_draws(summed, key)
        summary[f"{key}_share_of_world"] = np.mean(summed / world[key][None, :], axis=1)
        frames.append(summary)
    table = pd.concat([pd.DataFrame({column: labels}), *frames], axis=1)
    return table.sort_values("ncw_usd2015_yr_mean", ascending=False).reset_index(drop=True)


def top_territories(ncw_table: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    columns = [
        "iso3", "name", "continent", "groups", "ncw_usd2015_yr_mean", "ncw_usd2015_yr_p05", "ncw_usd2015_yr_p95",
        "gcw_usd2015_yr_mean", "bcw_usd2015_yr_mean", "forest_share_of_ncw", "ncw_per_capita_usd2015", "ncw_share_of_gdp",
    ]
    return ncw_table.head(n)[columns]


def route_a_extremes(gcw_table: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    columns = ["iso3", "name", "faostat_net_uptake_tco2_yr", "faostat_gcw_usd2015_yr_mean", "uptake_tco2_yr_mean"]
    valid = gcw_table.dropna(subset=["faostat_net_uptake_tco2_yr"])
    sinks = valid.nlargest(n, "faostat_net_uptake_tco2_yr")[columns].assign(position="largest net sinks")
    sources = valid.nsmallest(n, "faostat_net_uptake_tco2_yr")[columns].assign(position="largest net sources")
    return pd.concat([sinks, sources], ignore_index=True).rename(columns={"uptake_tco2_yr_mean": "route_b_uptake_tco2_yr_mean"})


def run(forest: dict, faostat: pd.DataFrame, gcw_table: pd.DataFrame, gcw: dict, ncw_table: pd.DataFrame, ncw: dict) -> None:
    write_table(global_by_ecosystem(forest, faostat, gcw, ncw), TABLES / "table1_global_by_ecosystem.csv")
    write_table(by_group(ncw_table, ncw, "continent"), TABLES / "table2_by_continent.csv")
    write_table(by_group(ncw_table, ncw, "groups"), TABLES / "table3_by_group.csv")
    write_table(top_territories(ncw_table), TABLES / "table4_top_territories.csv")
    write_table(route_a_extremes(gcw_table), TABLES / "table5_route_a_faostat.csv")
