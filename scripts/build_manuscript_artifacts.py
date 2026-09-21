"""Build draft manuscript tables and figures from the BNC2 analysis inputs.

This script reproduces the R1--R4 descriptive analyses without overwriting the
working outputs of ``04_analyses_R1_R4.ipynb``.  It writes manuscript-specific
artefacts to ``output/tables/manuscript`` and ``output/figures/manuscript``.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CARBON_TO_CO2 = 44.0 / 12.0
GROUP_ORDER = ["Developed economies", "Developing economies", "LDCs", "SIDS"]
GROUP_COLORS = {
    "Developed economies": "#4C72B0",
    "Developing economies": "#55A868",
    "LDCs": "#C44E52",
    "SIDS": "#8172B2",
}
PROFILE_THRESHOLD = 66.7
ILLUSTRATIVE_PRICES = (50.0, 150.0, 400.0)
ILLUSTRATIVE_ALLOCATION_PRICE = 150.0


def find_repository_root(start: Path) -> Path:
    """Return the repository root that contains the source-data directory."""
    root = start.resolve()
    while root != root.parent and not (root / "data_source").exists():
        root = root.parent
    if not (root / "data_source").exists():
        raise FileNotFoundError("Could not locate the repository data_source directory.")
    return root


def summarise(draws: np.ndarray) -> dict[str, float]:
    """Summarise a one-dimensional Monte Carlo distribution."""
    values = np.asarray(draws, dtype="float64")
    return {
        "mean": float(np.nanmean(values)),
        "p05": float(np.nanpercentile(values, 5)),
        "p50": float(np.nanpercentile(values, 50)),
        "p95": float(np.nanpercentile(values, 95)),
    }


def gini(values: pd.Series | np.ndarray) -> float:
    """Calculate the Gini coefficient after dropping missing values."""
    x = np.sort(np.asarray(values, dtype="float64"))
    x = x[~np.isnan(x)]
    if x.size == 0 or x.sum() == 0:
        return float("nan")
    n = x.size
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def lorenz_points(values: pd.Series | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return cumulative population and value shares for a Lorenz curve."""
    x = np.sort(np.asarray(values, dtype="float64"))
    x = x[~np.isnan(x)]
    return np.linspace(0, 1, x.size + 1), np.concatenate([[0], np.cumsum(x) / x.sum()])


def get_socioeconomic_data(data_dir: Path, territories: pd.DataFrame) -> pd.DataFrame:
    """Map published BCW socioeconomic fields to the harmonised accounting units."""
    bcw = pd.read_csv(data_dir / "raw" / "bcw" / "output" / "country_level_bcw.csv")
    bcw["ISO"] = bcw["ISO"].astype(str)
    code_to_unit: dict[str, str] = {}
    for _, row in territories.dropna(subset=["bcw_codes"]).iterrows():
        for code in str(row["bcw_codes"]).split(";"):
            code_to_unit[code] = row["iso3"]
    bcw["unit"] = bcw["ISO"].map(code_to_unit)
    return (
        bcw.dropna(subset=["unit"])
        .sort_values("CO2_emissions_2023", ascending=False)
        .groupby("unit")[["CO2_emissions_2023", "Debt (2015 US$)"]]
        .first()
        .rename(
            columns={
                "CO2_emissions_2023": "co2_emissions_tco2_2023",
                "Debt (2015 US$)": "debt_usd2015",
            }
        )
    )


def load_data(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load country data and aligned uncertainty draws used by the manuscript plots."""
    output_dir = root / "output"
    data_dir = root / "data_source"
    gcw = pd.read_csv(output_dir / "country_level_gcw.csv")
    ncw = pd.read_csv(output_dir / "country_level_ncw.csv")
    territories = pd.read_csv(data_dir / "summary" / "territories.csv")
    rates = pd.read_csv(data_dir / "summary" / "biome_rates.csv").set_index("pan_biome")
    area_biome = pd.read_csv(data_dir / "summary" / "forest_area_by_biome.csv")
    gcw_archive = np.load(output_dir / "draws" / "gcw_draws.npz", allow_pickle=True)
    ncw_archive = np.load(output_dir / "draws" / "ncw_draws.npz", allow_pickle=True)
    units = ncw_archive["iso3"].astype(str)
    gcw_draws = ncw_archive["gcw_usd2015_yr"].astype("float64")
    bcw_draws = ncw_archive["bcw_usd2015_yr"].astype("float64")
    ncw_draws = ncw_archive["ncw_usd2015_yr"].astype("float64")
    gscc = gcw_archive["gscc"].astype("float64")

    socioeconomic = get_socioeconomic_data(data_dir, territories)
    base = (
        ncw.drop(columns=[column for column in ("continent", "groups", "population", "gdp") if column in ncw])
        .merge(territories[["iso3", "continent", "groups", "population", "gdp"]], on="iso3", how="left")
        .merge(socioeconomic, left_on="iso3", right_index=True, how="left")
    )
    base["debt_share_of_gdp"] = 100 * base["debt_usd2015"] / base["gdp"]
    return base, gcw, rates, area_biome, units, gcw_draws, bcw_draws, ncw_draws, gscc


def calculate_losses(
    root: Path,
    area_biome: pd.DataFrame,
    rates: pd.DataFrame,
    gscc: np.ndarray,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.DataFrame]:
    """Estimate annual lost capacity from FRA deforestation with biome-weighted rates.

    The calculation matches R3 in ``04_analyses_R1_R4.ipynb``. It treats missing
    FRA reports as missing data, never as zero deforestation.
    """
    fra_zip = root / "data_source" / "raw" / "fra" / "fra2025_bulk_WO.zip"
    with zipfile.ZipFile(fra_zip) as archive:
        filename = next(name for name in archive.namelist() if "1d_deforestation" in name)
        deforestation = pd.read_csv(archive.open(filename))

    deforestation = deforestation.dropna(subset=["iso3"]).copy()
    for column in ("2010-2015", "2015-2020"):
        deforestation[column] = pd.to_numeric(deforestation[column], errors="coerce")
    deforestation["defor_kha_yr"] = deforestation[["2010-2015", "2015-2020"]].mean(axis=1)
    deforestation = deforestation[["iso3", "name", "defor_kha_yr"]]

    shares = (
        area_biome.query("variant == 'excl_mangroves'")
        .pivot_table(index="iso3", columns="pan_biome", values="area_ha", aggfunc="sum")
        .fillna(0.0)
    )
    shares = shares.div(shares.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    deforestation_ha = (deforestation.set_index("iso3")["defor_kha_yr"] * 1000).reindex(shares.index)
    reported = deforestation_ha.notna().to_numpy()
    area_by_biome = shares.mul(deforestation_ha.fillna(0.0), axis=0).to_numpy()

    rng = np.random.default_rng(20260920)
    rate_draws = np.vstack(
        [
            np.clip(
                rng.normal(
                    rates.loc[biome, "rate_tc_ha_yr_mean"],
                    rates.loc[biome, "rate_tc_ha_yr_sd"],
                    gscc.size,
                ),
                0,
                None,
            )
            for biome in shares.columns
        ]
    )
    loss_tco2 = (area_by_biome @ rate_draws) * CARBON_TO_CO2
    loss_usd = loss_tco2 * gscc
    loss = pd.DataFrame(
        {
            "iso3": shares.index,
            "loss_tco2_mean": loss_tco2.mean(axis=1),
            "loss_usd_mean": loss_usd.mean(axis=1),
            "loss_usd_p05": np.percentile(loss_usd, 5, axis=1),
            "loss_usd_p95": np.percentile(loss_usd, 95, axis=1),
            "reported_deforestation": reported,
        }
    )
    loss.loc[~loss["reported_deforestation"], ["loss_tco2_mean", "loss_usd_mean", "loss_usd_p05", "loss_usd_p95"]] = np.nan
    return loss, loss_tco2, loss_usd, deforestation


def make_tables(
    tables_dir: Path,
    base: pd.DataFrame,
    gcw: pd.DataFrame,
    rates: pd.DataFrame,
    area_biome: pd.DataFrame,
    units: np.ndarray,
    gcw_draws: np.ndarray,
    bcw_draws: np.ndarray,
    ncw_draws: np.ndarray,
    gscc: np.ndarray,
    loss: pd.DataFrame,
    loss_tco2: np.ndarray,
    loss_usd: np.ndarray,
    deforestation: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build four manuscript tables and return prepared country-level data."""
    world_rows = []
    for label, draws in (("Green carbon wealth", gcw_draws), ("Blue carbon wealth", bcw_draws), ("Natural carbon wealth", ncw_draws)):
        world_rows.append({"component": label, **summarise(np.nansum(draws, axis=0))})
    table_1 = pd.DataFrame(world_rows)
    table_1[["mean", "p05", "p50", "p95"]] /= 1e12
    table_1 = table_1.rename(columns={column: f"value_{column}_trillion_usd2015_yr" for column in ("mean", "p05", "p50", "p95")})
    table_1.to_csv(tables_dir / "Table1_global_carbon_wealth.csv", index=False)

    r1 = base.dropna(subset=["gcw_usd2015_yr_mean"]).copy()
    r1["gcw_share_of_gdp_pct"] = 100 * r1["gcw_usd2015_yr_mean"] / r1["gdp"]
    composition = base.dropna(subset=["ncw_usd2015_yr_mean"]).copy()
    composition = composition[composition["has_gcw"] & composition["has_bcw"]].copy()
    composition["forest_share_pct"] = 100 * composition["gcw_usd2015_yr_mean"] / composition["ncw_usd2015_yr_mean"]
    composition["profile"] = np.select(
        [composition["forest_share_pct"] >= PROFILE_THRESHOLD, composition["forest_share_pct"] <= 100 - PROFILE_THRESHOLD],
        ["Green-dominant", "Blue-dominant"],
        default="Mixed",
    )
    emissions = base.set_index("iso3")["co2_emissions_tco2_2023"].reindex(units).to_numpy()
    balance = pd.DataFrame(
        {
            "iso3": units,
            "net_gcw_tco2_yr": (gcw_draws / gscc - emissions[:, None]).mean(axis=1),
            "net_ncw_tco2_yr": (ncw_draws / gscc - emissions[:, None]).mean(axis=1),
        }
    ).merge(base[["iso3", "groups"]], on="iso3", how="left")
    balance = balance.dropna(subset=["net_gcw_tco2_yr", "net_ncw_tco2_yr"])

    group_rows = []
    for group in GROUP_ORDER:
        group_draws = gcw_draws[(base.set_index("iso3")["groups"].reindex(units) == group).to_numpy()]
        group_rows.append(
            {
                "group": group,
                "gcw_trillion_usd2015_yr": np.nansum(group_draws, axis=0).mean() / 1e12,
                "gcw_share_world_pct": 100 * np.nansum(group_draws, axis=0).mean() / np.nansum(gcw_draws, axis=0).mean(),
                "median_gcw_share_of_gdp_pct": r1.loc[r1["groups"] == group, "gcw_share_of_gdp_pct"].median(),
                "green_dominant_units": int(((composition["groups"] == group) & (composition["profile"] == "Green-dominant")).sum()),
                "blue_dominant_units": int(((composition["groups"] == group) & (composition["profile"] == "Blue-dominant")).sum()),
                "net_sink_forest_pct": 100 * (balance.loc[balance["groups"] == group, "net_gcw_tco2_yr"] > 0).mean(),
                "net_sink_forest_ocean_pct": 100 * (balance.loc[balance["groups"] == group, "net_ncw_tco2_yr"] > 0).mean(),
            }
        )
    table_2 = pd.DataFrame(group_rows)
    table_2.to_csv(tables_dir / "Table2_group_profiles_and_balances.csv", index=False)

    r3 = base[["iso3", "name", "groups", "gdp", "gcw_usd2015_yr_mean"]].merge(loss, on="iso3", how="left")
    r3["erosion_pct_of_gcw"] = 100 * r3["loss_usd_mean"] / r3["gcw_usd2015_yr_mean"]
    r3["loss_pct_of_gdp"] = 100 * r3["loss_usd_mean"] / r3["gdp"]
    deforestation_by_group = (
        r3[["iso3", "groups"]]
        .merge(deforestation[["iso3", "defor_kha_yr"]], on="iso3", how="left")
        .groupby("groups")["defor_kha_yr"]
        .sum()
        .reindex(GROUP_ORDER)
        / 1000
    )
    table_3 = (
        r3.groupby("groups", dropna=False)
        .agg(
            reporting_units=("loss_usd_mean", lambda value: int(value.notna().sum())),
            lost_capacity_mtco2_yr=("loss_tco2_mean", lambda value: value.sum() / 1e6),
            lost_value_billion_usd2015_yr=("loss_usd_mean", lambda value: value.sum() / 1e9),
            median_erosion_pct_of_gcw=("erosion_pct_of_gcw", "median"),
        )
        .reindex(GROUP_ORDER)
        .reset_index()
    )
    table_3.insert(2, "deforestation_million_ha_yr", table_3["groups"].map(deforestation_by_group))
    table_3.to_csv(tables_dir / "Table3_erosion_by_group.csv", index=False)
    r3.to_csv(tables_dir / "Supplementary_country_level_erosion.csv", index=False)

    lost_tco2 = np.nansum(loss_tco2, axis=0).mean()
    lost_value = np.nansum(loss_usd, axis=0).mean()
    scenario_rows = [
        {
            "illustrative_price_usd2015_tco2": price,
            "annual_compensation_billion_usd2015": lost_tco2 * price / 1e9,
            "compensation_to_welfare_loss_ratio": lost_tco2 * price / lost_value,
        }
        for price in ILLUSTRATIVE_PRICES
    ]
    allocation = r3.dropna(subset=["loss_tco2_mean", "gdp"]).copy()
    allocation["domestic_cost"] = allocation["loss_tco2_mean"] * ILLUSTRATIVE_ALLOCATION_PRICE
    allocation["shared_cost"] = allocation["domestic_cost"].sum() * allocation["gdp"] / allocation["gdp"].sum()
    allocation["domestic_cost_pct_of_gdp"] = 100 * allocation["domestic_cost"] / allocation["gdp"]
    allocation_by_group = allocation.groupby("groups")[["domestic_cost", "shared_cost"]].sum().reindex(GROUP_ORDER)
    table_4 = pd.DataFrame(scenario_rows)
    table_4["allocation_price_usd2015_tco2"] = ILLUSTRATIVE_ALLOCATION_PRICE
    for group in GROUP_ORDER:
        table_4[f"domestic_cost_{group}_billion_usd2015"] = allocation_by_group.loc[group, "domestic_cost"] / 1e9
        table_4[f"shared_cost_{group}_billion_usd2015"] = allocation_by_group.loc[group, "shared_cost"] / 1e9
    table_4.to_csv(tables_dir / "Table4_illustrative_compensation_scenarios.csv", index=False)
    return r1, composition, balance, r3, allocation_by_group


def make_figures(
    figures_dir: Path,
    r1: pd.DataFrame,
    composition: pd.DataFrame,
    base: pd.DataFrame,
    units: np.ndarray,
    gcw_draws: np.ndarray,
    bcw_draws: np.ndarray,
    ncw_draws: np.ndarray,
    gscc: np.ndarray,
    r3: pd.DataFrame,
    allocation_by_group: pd.DataFrame,
) -> None:
    """Render the four selected draft manuscript figures."""
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.22})

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2), layout="constrained")
    scatter_data = r1.dropna(subset=["gdp"]).query("gdp > 0 and gcw_usd2015_yr_mean > 0")
    for group, data in scatter_data.groupby("groups"):
        axes[0].scatter(data["gdp"], data["gcw_usd2015_yr_mean"], s=16, alpha=0.78, label=group, color=GROUP_COLORS.get(group, "#808080"))
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("GDP (2015 US$)")
    axes[0].set_ylabel("GCW (2015 US$ per year)")
    axes[0].set_title("Ecological endowment and economic size")
    axes[0].legend(fontsize=7, frameon=False)
    x_gcw, y_gcw = lorenz_points(r1["gcw_usd2015_yr_mean"])
    x_bcw, y_bcw = lorenz_points(base["bcw_usd2015_yr_mean"].dropna())
    axes[1].plot(x_gcw, y_gcw, label=f"GCW (Gini {gini(r1['gcw_usd2015_yr_mean']):.2f})", color="#2E7D32")
    axes[1].plot(x_bcw, y_bcw, label=f"BCW (Gini {gini(base['bcw_usd2015_yr_mean'].dropna()):.2f})", color="#1565C0")
    axes[1].plot([0, 1], [0, 1], "k--", lw=0.8, label="Equality")
    axes[1].set_xlabel("Cumulative share of countries")
    axes[1].set_ylabel("Cumulative share of wealth")
    axes[1].set_title("Concentration of carbon wealth")
    axes[1].legend(fontsize=7, frameon=False)
    figure.savefig(figures_dir / "Figure1_forest_service_and_concentration.png", dpi=300, bbox_inches="tight")
    plt.close(figure)

    figure, axes = plt.subplots(2, 1, figsize=(9.8, 7.2), height_ratios=[1, 1.6], layout="constrained")
    group_components = composition.groupby("groups")[["gcw_usd2015_yr_mean", "bcw_usd2015_yr_mean"]].sum().reindex(GROUP_ORDER) / 1e12
    axes[0].barh(group_components.index, group_components["gcw_usd2015_yr_mean"], color="#7FBF7B", label="Green carbon")
    axes[0].barh(group_components.index, group_components["bcw_usd2015_yr_mean"], left=group_components["gcw_usd2015_yr_mean"], color="#6BAED6", label="Blue carbon")
    axes[0].set_xlabel("Trillion 2015 US$ per year")
    axes[0].set_title("Composition of natural carbon wealth by country group")
    axes[0].legend(frameon=False, ncol=2, fontsize=8)

    emissions = base.set_index("iso3")["co2_emissions_tco2_2023"].reindex(units).to_numpy()
    panel = base[["iso3", "co2_emissions_tco2_2023"]].merge(
        pd.DataFrame(
            {
                "iso3": units,
                "green_tco2": (gcw_draws / gscc).mean(axis=1),
                "blue_tco2": (bcw_draws / gscc).mean(axis=1),
            }
        ),
        on="iso3",
        how="inner",
    ).dropna()
    panel["total_tco2"] = panel["green_tco2"] + panel["blue_tco2"]
    left = panel.nlargest(10, "co2_emissions_tco2_2023")
    right = panel.loc[~panel["iso3"].isin(left["iso3"])].nlargest(10, "total_tco2").sort_values("total_tco2")
    selected = pd.concat([left, right], ignore_index=True)
    world_emissions = np.nansum(emissions)
    world_sequestration = panel["total_tco2"].sum()
    positions = np.arange(len(selected))
    axes[1].bar(positions, 100 * selected["co2_emissions_tco2_2023"] / world_emissions, color="#D6607D", label="CO2 emissions")
    axes[1].bar(positions, -100 * selected["green_tco2"] / world_sequestration, color="#7FBF7B", label="Green sequestration")
    axes[1].bar(positions, -100 * selected["blue_tco2"] / world_sequestration, bottom=-100 * selected["green_tco2"] / world_sequestration, color="#6BAED6", hatch="///", label="Blue sequestration")
    axes[1].axhline(0, color="#4D4D4D", lw=0.8)
    axes[1].axvline(9.5, color="#8C8C8C", lw=0.8, ls=":")
    axes[1].set_xticks(positions, selected["iso3"])
    axes[1].set_ylabel("Share of global annual flux (%)")
    axes[1].set_title("Major emitters and major sinks are largely distinct")
    axes[1].legend(frameon=False, ncol=3, fontsize=8, loc="lower center")
    figure.savefig(figures_dir / "Figure2_blue_carbon_and_net_balance.png", dpi=300, bbox_inches="tight")
    plt.close(figure)

    typology = r3.dropna(subset=["gcw_usd2015_yr_mean", "erosion_pct_of_gcw"]).query("gcw_usd2015_yr_mean > 0 and erosion_pct_of_gcw > 0").copy()
    median_gcw = typology["gcw_usd2015_yr_mean"].median()
    median_erosion = typology["erosion_pct_of_gcw"].median()
    figure, axis = plt.subplots(figsize=(6.2, 4.8), layout="constrained")
    for group, data in typology.groupby("groups"):
        axis.scatter(data["gcw_usd2015_yr_mean"] / 1e9, data["erosion_pct_of_gcw"], s=22, alpha=0.8, color=GROUP_COLORS.get(group, "#808080"), label=group)
    for _, row in typology.nlargest(8, "loss_usd_mean").iterrows():
        axis.annotate(row["iso3"], (row["gcw_usd2015_yr_mean"] / 1e9, row["erosion_pct_of_gcw"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    axis.axvline(median_gcw / 1e9, color="#4D4D4D", ls="--", lw=0.8)
    axis.axhline(median_erosion, color="#4D4D4D", ls="--", lw=0.8)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("GCW (billion 2015 US$ per year)")
    axis.set_ylabel("Annual capacity loss (% of national GCW)")
    axis.set_title("Service magnitude and erosion intensity")
    axis.legend(fontsize=7, frameon=False)
    figure.savefig(figures_dir / "Figure3_erosion_of_forest_service.png", dpi=300, bbox_inches="tight")
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
    positions = np.arange(len(allocation_by_group))
    axis.bar(positions - 0.2, allocation_by_group["domestic_cost"] / 1e9, 0.4, label="Domestic compensation")
    axis.bar(positions + 0.2, allocation_by_group["shared_cost"] / 1e9, 0.4, label="GDP-proportional shared effort")
    axis.set_xticks(positions, allocation_by_group.index, rotation=18, ha="right")
    axis.set_ylabel("Billion 2015 US$ per year")
    axis.set_title("Who loses the sink and who pays for compensation")
    axis.legend(fontsize=8, frameon=False)
    figure.savefig(figures_dir / "Figure4_compensation_burden.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    """Build manuscript artefacts without modifying existing notebook outputs."""
    root = find_repository_root(Path.cwd())
    tables_dir = root / "output" / "tables" / "manuscript"
    figures_dir = root / "output" / "figures" / "manuscript"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    base, gcw, rates, area_biome, units, gcw_draws, bcw_draws, ncw_draws, gscc = load_data(root)
    loss, loss_tco2, loss_usd, deforestation = calculate_losses(root, area_biome, rates, gscc)
    r1, composition, _, r3, allocation_by_group = make_tables(
        tables_dir,
        base,
        gcw,
        rates,
        area_biome,
        units,
        gcw_draws,
        bcw_draws,
        ncw_draws,
        gscc,
        loss,
        loss_tco2,
        loss_usd,
        deforestation,
    )
    make_figures(figures_dir, r1, composition, base, units, gcw_draws, bcw_draws, ncw_draws, gscc, r3, allocation_by_group)
    print(f"Wrote tables to {tables_dir}")
    print(f"Wrote figures to {figures_dir}")


if __name__ == "__main__":
    main()
