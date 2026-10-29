"""Exploratory spatial analysis for the 2026-10-23 Results refresh.

The script compares first-order land contiguity with symmetric k-nearest
neighbours (k=5) for three country-level indicators. It is an exploratory
diagnostic, not a causal identification strategy or a final manuscript choice.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda import Moran
from libpysal.weights import KNN, Queen, W
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from spreg import ML_Error, ML_Lag


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "outputs" / "validation"
SEED = 20261019
PERMUTATIONS = 9_999
K_NEIGHBOURS = 5


def _parts(geom):
    return list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]


def _unit_geometries() -> tuple[gpd.GeoDataFrame, list[str]]:
    """Map Natural Earth 50m polygons to the study's territorial units.

    Several small overseas territories are multipart pieces of a sovereign
    polygon in Natural Earth 50m. They are split using their published
    geographic position so that the paper's country/territory units are not
    silently merged. Gibraltar has no polygon in this source and is excluded.
    """
    path = ROOT / "data" / "raw" / "geospatial" / "boundaries" / "ne_50m_admin_0_countries.zip"
    ne = gpd.read_file(f"zip://{path}")
    gcw = pd.read_csv(ROOT / "data" / "outputs" / "accounts" / "country_level_gcw.csv")
    wanted = set(gcw["iso3"].astype(str))

    by_code: dict[str, list] = {}
    for _, row in ne.iterrows():
        code = str(row["ISO_A3"])
        if code == "-99":
            code = str(row["ADM0_A3"])
        if code in wanted and code not in {"FRA", "NOR"}:
            by_code.setdefault(code, []).append(row.geometry)

    def add(code: str, geoms: list) -> None:
        if geoms:
            by_code.setdefault(code, []).extend(geoms)

    # France: Natural Earth 50m stores the Guiana, Guadeloupe, Martinique,
    # Mayotte and Réunion land pieces inside its France multipolygon.
    france = ne.loc[ne["ADM0_A3"].eq("FRA"), "geometry"].iloc[0]
    for part in _parts(france):
        p = part.representative_point()
        x, y = p.x, p.y
        if x < -45 and -10 < y < 10:
            code = "GUF"
        elif -62.5 < x < -60 and 13 < y < 15.2:
            code = "MTQ"
        elif -63 < x < -60 and 15.2 < y < 18:
            code = "GLP"
        elif 44 < x < 46 and -14 < y < -11:
            code = "MYT"
        elif 54 < x < 57 and -22 < y < -20:
            code = "REU"
        else:
            code = "FRA"
        add(code, [part])

    # Norway: Natural Earth includes Svalbard and Jan Mayen in Norway.
    norway = ne.loc[ne["ADM0_A3"].eq("NOR"), "geometry"].iloc[0]
    for part in _parts(norway):
        p = part.representative_point()
        if p.y >= 74 or (p.x < -6 and 70 < p.y < 72):
            add("SJM", [part])
        else:
            add("NOR", [part])

    # Bonaire, Sint Eustatius and Saba are Caribbean pieces of the Netherlands
    # in this Natural Earth release.
    netherlands = ne.loc[ne["ADM0_A3"].eq("NLD"), "geometry"].iloc[0]
    for part in _parts(netherlands):
        if part.representative_point().x < 0:
            add("BES", [part])
        else:
            add("NLD", [part])

    # Tokelau is included as a small island in the New Zealand multipolygon.
    new_zealand = ne.loc[ne["ADM0_A3"].eq("NZL"), "geometry"].iloc[0]
    for part in _parts(new_zealand):
        p = part.representative_point()
        if -174 < p.x < -170 and -11 < p.y < -7:
            add("TKL", [part])
        else:
            add("NZL", [part])

    rows = []
    for code, geometries in by_code.items():
        if code not in wanted:
            continue
        geom = unary_union(geometries)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if not geom.is_empty:
            rows.append({"iso3": code, "geometry": geom})
    result = gpd.GeoDataFrame(rows, geometry="geometry", crs=ne.crs)
    missing = sorted(wanted - set(result["iso3"]))
    return result.sort_values("iso3").reset_index(drop=True), missing


def _weight_subsample(full: W, ids: list[str]) -> W:
    idset = set(ids)
    neighbours = {
        key: [n for n in full.neighbors[key] if n in idset]
        for key in ids
    }
    w = W(neighbours, id_order=ids, silence_warnings=True)
    w.transform = "r"
    return w


def _build_weights(gdf: gpd.GeoDataFrame) -> dict[str, W]:
    ids = gdf["iso3"].tolist()
    queen = Queen.from_dataframe(gdf, ids=ids, use_index=False)
    queen.transform = "r"
    # Equal-area projected representative points reduce the latitude distortion
    # of Euclidean nearest-neighbour distances compared with longitude/latitude.
    projected = gdf.to_crs("EPSG:6933")
    points = projected.geometry.representative_point()
    xy = np.column_stack([points.x.to_numpy(), points.y.to_numpy()])
    knn = KNN.from_array(xy, k=K_NEIGHBOURS, ids=ids)
    knn.symmetrize(inplace=True)
    knn.transform = "r"
    return {"queen_contiguity": queen, "symmetric_knn5": knn}


def _moran(y: np.ndarray, w: W, seed: int) -> dict[str, float]:
    np.random.seed(seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = Moran(y, w, permutations=PERMUTATIONS, two_tailed=True)
    return {
        "moran_i": float(m.I),
        "expected_i": float(m.EI),
        "z_randomisation": float(m.z_rand),
        "p_randomisation": float(m.p_rand),
        # esda's p_sim is a one-sided pseudo-p value. The two-sided value below
        # counts simulated statistics at least as far from EI as the observed I.
        "p_permutation_two_sided": float(
            (1 + np.count_nonzero(np.abs(m.sim - m.EI) >= abs(m.I - m.EI)))
            / (len(m.sim) + 1)
        ),
        "permutations": PERMUTATIONS,
    }


def _model_rows(y: np.ndarray, x: np.ndarray, w: W, names: list[str], yname: str, weight: str, n: int) -> list[dict]:
    rows = []
    for kind, estimator in (("spatial_lag", ML_Lag), ("spatial_error", ML_Error)):
        try:
            model = estimator(
                y=y,
                x=x,
                w=w,
                name_y=yname,
                name_x=names,
                method="ord",
                spat_diag=False,
                vm=True,
            )
            estimates = []
            for i, beta in enumerate(np.asarray(model.betas).reshape(-1)):
                label = ["constant", *names]
                if kind == "spatial_lag":
                    label.append("rho")
                else:
                    label.append("lambda")
                name = label[i] if i < len(label) else f"term_{i}"
                se = float(model.std_err[i]) if i < len(model.std_err) else float("nan")
                z, p = model.z_stat[i] if i < len(model.z_stat) else (float("nan"), float("nan"))
                estimates.append((name, float(beta), se, float(z), float(p)))
            for name, coef, se, z, p in estimates:
                rows.append({
                    "outcome": yname,
                    "weight": weight,
                    "model": kind,
                    "term": name,
                    "coefficient": coef,
                    "std_error": se,
                    "z": z,
                    "p_value": p,
                    "n": n,
                    "aic": float(model.aic),
                    "log_likelihood": float(model.logll),
                    "model_status": "ok",
                })
        except Exception as exc:  # retain a transparent diagnostic row on failure
            rows.append({
                "outcome": yname,
                "weight": weight,
                "model": kind,
                "term": "",
                "coefficient": np.nan,
                "std_error": np.nan,
                "z": np.nan,
                "p_value": np.nan,
                "n": n,
                "aic": np.nan,
                "log_likelihood": np.nan,
                "model_status": f"failed: {type(exc).__name__}: {exc}",
            })
    return rows


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    gdf, missing_geometry = _unit_geometries()
    gcf = pd.read_csv(ROOT / "data" / "outputs" / "accounts" / "country_level_gcw.csv")
    erosion = pd.read_csv(ROOT / "results" / "tables" / "manuscript" / "Supplementary_country_level_erosion.csv")
    area = pd.read_csv(ROOT / "data" / "outputs" / "forest_account" / "forest_area_by_biome.csv")
    area = area.loc[area["variant"].eq("documented_overlap_removed")].copy()
    area_table = area.pivot_table(index="iso3", columns="biome", values="area_ha", aggfunc="sum", fill_value=0)
    area_table["forest_area_ha"] = area_table.sum(axis=1)
    for biome in ("tropical", "subtropical"):
        if biome not in area_table:
            area_table[biome] = 0.0
    area_table["warm_biome_share"] = np.where(
        area_table["forest_area_ha"].gt(0),
        (area_table["tropical"] + area_table["subtropical"]) / area_table["forest_area_ha"],
        np.nan,
    )
    d = gcf.merge(erosion[["iso3", "loss_tco2_mean", "reported_deforestation", "erosion_pct_of_gcw"]], on="iso3", how="left")
    d = d.merge(area_table[["forest_area_ha", "warm_biome_share"]], left_on="iso3", right_index=True, how="left")
    d = d.merge(gdf[["iso3"]], on="iso3", how="inner").set_index("iso3").sort_index()
    gdf = gdf.set_index("iso3").loc[d.index].reset_index()

    d["lost_capacity_mtco2_yr"] = d["loss_tco2_mean"] / 1e6
    d["gcw_gdp_pct"] = d["gcw_share_of_gdp"] * 100.0
    d["ln_gdp_per_capita"] = np.log(d["gdp"] / d["population"])
    d["ln_forest_area_mha"] = np.log1p(d["forest_area_ha"] / 1e6)
    outcomes = {
        "lost_capacity_mtco2_yr": "log_lost_capacity_mtco2_yr",
        "erosion_pct_of_gcw": "log_erosion_pct_of_gcw",
        "gcw_gdp_pct": "log_gcw_gdp_pct",
    }
    xnames = ["ln_gdp_per_capita", "ln_forest_area_mha", "warm_biome_share"]
    full_weights = _build_weights(gdf)
    moran_rows = []
    model_rows = []
    sample_rows = []
    ols_residual_rows = []

    for outcome, label in outcomes.items():
        cols = [outcome]
        if outcome != "gcw_gdp_pct":
            cols += ["reported_deforestation"]
        sample = d.loc[:, [*cols, *xnames]].replace([np.inf, -np.inf], np.nan).dropna()
        if outcome != "gcw_gdp_pct":
            sample = sample.loc[sample["reported_deforestation"].astype(bool)]
        # The annual loss outcome has reported zeros. Keep them as zeros and
        # apply log1p; do not turn non-reporting into zero.
        y = np.log1p(sample[outcome].to_numpy(dtype=float)).reshape(-1, 1)
        x = sample[xnames].to_numpy(dtype=float)
        ids = sample.index.tolist()
        sample_rows.append({
            "outcome": outcome,
            "n": len(sample),
            "geometry_units": len(d),
            "nonreporting_as_missing": outcome != "gcw_gdp_pct",
            "zero_values": int(sample[outcome].eq(0).sum()),
            "y_transform": "log1p",
            "predictors": ";".join(xnames),
        })
        ols = sm.OLS(y, sm.add_constant(x, has_constant="add")).fit(cov_type="HC3")
        for i, beta in enumerate(ols.params):
            term = ["constant", *xnames][i]
            model_rows.append({
                "outcome": outcome,
                "weight": "no_spatial_baseline",
                "model": "ols_hc3",
                "term": term,
                "coefficient": float(beta),
                "std_error": float(ols.bse[i]),
                "z": float(ols.tvalues[i]),
                "p_value": float(ols.pvalues[i]),
                "n": len(sample),
                "aic": float(ols.aic),
                "log_likelihood": float(ols.llf),
                "model_status": "ok",
            })
        for wi, (weight, full_w) in enumerate(full_weights.items()):
            w = _weight_subsample(full_w, ids)
            moran_rows.append({
                "outcome": outcome,
                "weight": weight,
                "n": len(sample),
                "islands": len(w.islands),
                "components": len(set(w.component_labels)) if hasattr(w, "component_labels") else np.nan,
                **_moran(y.ravel(), w, SEED + wi + list(outcomes).index(outcome) * 10),
            })
            ols_residual_rows.append({
                "outcome": outcome,
                "weight": weight,
                "n": len(sample),
                "islands": len(w.islands),
                **_moran(np.asarray(ols.resid).ravel(), w, SEED + 100 + wi + list(outcomes).index(outcome) * 10),
            })
            model_rows.extend(_model_rows(y, x, w, xnames, outcome, weight, len(sample)))

    pd.DataFrame(moran_rows).to_csv(OUT / "spatial_moran_comparison.csv", index=False)
    pd.DataFrame(model_rows).to_csv(OUT / "spatial_models_comparison.csv", index=False)
    pd.DataFrame(sample_rows).to_csv(OUT / "spatial_sample_audit.csv", index=False)
    pd.DataFrame(ols_residual_rows).to_csv(OUT / "spatial_ols_residual_moran.csv", index=False)
    diagnostics = {
        "date": "2026-10-23",
        "boundary_source": "Natural Earth 50m admin-0 country polygons",
        "units_with_geometry": int(len(d)),
        "units_without_geometry": missing_geometry,
        "queen": {
            "n": len(full_weights["queen_contiguity"].id_order),
            "islands": list(full_weights["queen_contiguity"].islands),
            "n_islands": len(full_weights["queen_contiguity"].islands),
            "n_components": len(set(full_weights["queen_contiguity"].component_labels)),
        },
        "knn": {"k": K_NEIGHBOURS, "symmetrized": True, "distance_crs": "EPSG:6933"},
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "predictors": xnames,
        "transform": "log1p outcome; numeric predictors in native transformed units",
        "caveats": [
            "Exploratory association only; spatial lag/error coefficients are not causal effects.",
            "Deforestation outcomes are complete cases among reported units; non-reporting is not coded as zero.",
            "Geometry-source mismatches and special-unit splits are documented; Gibraltar is not represented as a polygon in this Natural Earth release.",
            "The same parsimonious predictor set is used for comparison, not claimed as a final specification.",
        ],
        "territory_crosswalk": {
            "FRA": "Natural Earth ADM0_A3 key; overseas polygons split to French Guiana, Guadeloupe, Martinique, Mayotte and Réunion by location.",
            "NOR": "Natural Earth ADM0_A3 key; Svalbard and Jan Mayen polygons split to SJM by location.",
            "BES": "Bonaire, Sint Eustatius and Saba polygons split from Netherlands multipolygon.",
            "TKL": "Tokelau polygon split from New Zealand multipolygon.",
            "GIB": "No polygon in Natural Earth 50m; excluded from spatial analysis.",
        },
    }
    (OUT / "spatial_analysis_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    return diagnostics


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
