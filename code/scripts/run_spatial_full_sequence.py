"""Run the requested four-step cross-sectional spatial analysis sequence.

The script preserves the existing three outcomes, covariates, country samples,
and two weight matrices, then adds OLS LM diagnostics and nested SAR/SEM/SDM/
SDEM/GNS likelihood comparisons. All spatial coefficients are exploratory.
"""

from __future__ import annotations

import itertools
import json
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda import Moran
from libpysal.weights import KNN, Queen, W
from scipy.optimize import minimize
from scipy.stats import chi2, norm
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from spreg import LMtests, OLS as PySAL_OLS
from statsmodels.stats.multitest import multipletests
from statsmodels.tools.numdiff import approx_hess3


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "outputs" / "validation"
SEED = 20261019
PERMUTATIONS = 9_999
K_NEIGHBOURS = 5
ALPHA = 0.05
MODEL_FLAGS = {
    "OLS": (False, False, False),
    "SAR": (True, False, False),
    "SEM": (False, True, False),
    "SDM": (True, False, True),
    "SDEM": (False, True, True),
    "GNS": (True, True, True),
}


def _parts(geom):
    return list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]


def _unit_geometries() -> tuple[gpd.GeoDataFrame, list[str]]:
    """Map Natural Earth 50m polygons to the study's territorial units."""
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

    norway = ne.loc[ne["ADM0_A3"].eq("NOR"), "geometry"].iloc[0]
    for part in _parts(norway):
        p = part.representative_point()
        add("SJM" if p.y >= 74 or (p.x < -6 and 70 < p.y < 72) else "NOR", [part])

    netherlands = ne.loc[ne["ADM0_A3"].eq("NLD"), "geometry"].iloc[0]
    for part in _parts(netherlands):
        add("BES" if part.representative_point().x < 0 else "NLD", [part])

    new_zealand = ne.loc[ne["ADM0_A3"].eq("NZL"), "geometry"].iloc[0]
    for part in _parts(new_zealand):
        p = part.representative_point()
        add("TKL" if -174 < p.x < -170 and -11 < p.y < -7 else "NZL", [part])

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
    neighbours = {key: [n for n in full.neighbors[key] if n in idset] for key in ids}
    w = W(neighbours, id_order=ids, silence_warnings=True)
    w.transform = "r"
    return w


def _build_weights(gdf: gpd.GeoDataFrame) -> dict[str, W]:
    ids = gdf["iso3"].tolist()
    queen = Queen.from_dataframe(gdf, ids=ids, use_index=False)
    queen.transform = "r"
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
        "p_permutation_two_sided": float(
            (1 + np.count_nonzero(np.abs(m.sim - m.EI) >= abs(m.I - m.EI)))
            / (len(m.sim) + 1)
        ),
        "permutations": PERMUTATIONS,
    }


def _holm_by_group(frame: pd.DataFrame, p_column: str, group_columns: list[str]) -> pd.Series:
    adjusted = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, idx in frame.groupby(group_columns, dropna=False).groups.items():
        p = frame.loc[idx, p_column].to_numpy(dtype=float)
        ok = np.isfinite(p)
        if ok.any():
            adjusted.loc[np.asarray(idx)[ok]] = multipletests(p[ok], method="holm")[1]
    return adjusted


def _eigen_bounds(eigenvalues: np.ndarray) -> tuple[float, float]:
    real_eigs = eigenvalues.real[np.abs(eigenvalues.imag) < 1e-8]
    negative = real_eigs[real_eigs < -1e-8]
    positive = real_eigs[real_eigs > 1e-8]
    lower = (1.0 / negative.min() + 1e-6) if len(negative) else -5.0
    upper = (1.0 / positive.max() - 1e-6) if len(positive) else 5.0
    if lower >= upper:
        raise ValueError(f"Invalid spatial-parameter bounds: {lower}, {upper}")
    return float(lower), float(upper)


def _fit_spatial_mle(
    y: np.ndarray,
    x: np.ndarray,
    w: W,
    model_name: str,
    x_names: list[str],
) -> dict:
    """Concentrated Gaussian ML for OLS/SAR/SEM/SDM/SDEM/GNS.

    For the general model, e=(I-lambda W)[(I-rho W)y-Xb-WXtheta].
    The log likelihood includes both spatial Jacobians. Coefficients are
    profiled by least squares at each rho/lambda pair.
    """
    uses_rho, uses_lambda, uses_wx = MODEL_FLAGS[model_name]
    y = np.asarray(y, dtype=float).reshape(-1, 1)
    x = np.asarray(x, dtype=float)
    n = len(y)
    wd = w.sparse.toarray().astype(float)
    wy = wd @ y
    w2y = wd @ wy
    wx = wd @ x
    design = np.column_stack([np.ones(n), x, wx if uses_wx else np.empty((n, 0))])
    design_names = ["constant", *x_names]
    if uses_wx:
        design_names.extend(f"W_{name}" for name in x_names)
    wdesign = wd @ design
    eigenvalues = np.linalg.eigvals(wd)
    bound = _eigen_bounds(eigenvalues)
    active_names = (["rho"] if uses_rho else []) + (["lambda"] if uses_lambda else [])

    def unpack(params: np.ndarray) -> tuple[float, float]:
        cursor = 0
        rho = float(params[cursor]) if uses_rho else 0.0
        cursor += int(uses_rho)
        lam = float(params[cursor]) if uses_lambda else 0.0
        return rho, lam

    def log_jacobian(value: float) -> float:
        if abs(value) < 1e-14:
            return 0.0
        factors = 1.0 - value * eigenvalues
        if np.any(np.abs(factors) < 1e-12):
            return -np.inf
        return float(np.log(np.abs(factors)).sum())

    def profile(params: np.ndarray, return_parts: bool = False):
        rho, lam = unpack(params)
        # (I-lambda W)(I-rho W)y = y - (rho+lambda)Wy + rho*lambda*W^2y
        ystar = y - (rho + lam) * wy + rho * lam * w2y
        zstar = design - lam * wdesign
        beta, _, rank, _ = np.linalg.lstsq(zstar, ystar, rcond=None)
        if rank < zstar.shape[1]:
            return (np.inf, None) if return_parts else np.inf
        residual = ystar - zstar @ beta
        rss = max(float((residual.T @ residual).item()), 1e-14)
        sigma2 = rss / n
        ll = (
            log_jacobian(rho)
            + log_jacobian(lam)
            - (n / 2.0) * (np.log(2.0 * np.pi) + np.log(sigma2) + 1.0)
        )
        if not np.isfinite(ll):
            return (np.inf, None) if return_parts else np.inf
        if return_parts:
            return -float(ll), {
                "beta": beta.ravel(),
                "residual": residual.ravel(),
                "sigma2": sigma2,
                "log_likelihood": float(ll),
                "rho": rho,
                "lambda": lam,
            }
        return -float(ll)

    if not active_names:
        _, parts = profile(np.empty(0), return_parts=True)
        optimizer_success = True
        optimizer_message = "closed form OLS"
        spatial_params = np.empty(0)
    else:
        spatial_bounds = [bound] * len(active_names)
        starts = [tuple([0.0] * len(active_names))]
        if len(active_names) == 1:
            starts.extend((v,) for v in (-0.4, 0.35))
        else:
            starts.extend((r, l) for r, l in itertools.product((-0.35, 0.0, 0.35), repeat=2))
        fitted = []
        for start in starts:
            clipped = [min(max(v, lo + 1e-4), hi - 1e-4) for v, (lo, hi) in zip(start, spatial_bounds)]
            result = minimize(
                profile,
                x0=np.asarray(clipped),
                method="L-BFGS-B",
                jac="3-point",
                bounds=spatial_bounds,
                options={"ftol": 1e-12, "maxiter": 1200, "maxls": 40},
            )
            if np.isfinite(result.fun):
                fitted.append(result)
        if not fitted:
            raise RuntimeError(f"All ML starts failed for {model_name}")
        result = min(fitted, key=lambda item: item.fun)
        spatial_params = np.asarray(result.x, dtype=float)
        _, parts = profile(spatial_params, return_parts=True)
        optimizer_success = bool(result.success)
        optimizer_message = str(result.message)

    beta = parts["beta"]
    loglik = parts["log_likelihood"]
    n_parameters = len(beta) + len(spatial_params) + 1  # includes innovation variance
    aic = -2.0 * loglik + 2.0 * n_parameters
    bic = -2.0 * loglik + np.log(n) * n_parameters

    # Observed-information standard errors from the full Gaussian likelihood.
    # LR comparisons, rather than these Wald intervals, drive the nested tests.
    full_start = np.r_[beta, spatial_params, np.log(parts["sigma2"])]
    beta_n = len(beta)

    def full_nll(full_params: np.ndarray) -> float:
        b = full_params[:beta_n].reshape(-1, 1)
        cursor = beta_n
        rho = float(full_params[cursor]) if uses_rho else 0.0
        cursor += int(uses_rho)
        lam = float(full_params[cursor]) if uses_lambda else 0.0
        log_sigma2 = float(full_params[-1])
        if (uses_rho and not bound[0] < rho < bound[1]) or (uses_lambda and not bound[0] < lam < bound[1]):
            return 1e100
        resid = y - rho * wy - design @ b
        innovation = resid - lam * (wd @ resid)
        sigma2 = np.exp(log_sigma2)
        ll = log_jacobian(rho) + log_jacobian(lam) - 0.5 * n * (
            np.log(2.0 * np.pi) + log_sigma2
        ) - float((innovation.T @ innovation).item()) / (2.0 * sigma2)
        return -float(ll)

    try:
        hessian = approx_hess3(full_start, full_nll)
        covariance = np.linalg.inv(hessian)
        variances = np.diag(covariance)
        if np.any(variances < -1e-8):
            raise np.linalg.LinAlgError("negative observed-information variance")
        se_full = np.sqrt(np.maximum(variances, 0.0))
    except Exception:
        covariance = None
        se_full = np.full(len(full_start), np.nan)

    estimates = []
    for i, (term, value) in enumerate(zip(design_names, beta)):
        se = float(se_full[i]) if np.isfinite(se_full[i]) else np.nan
        z_value = float(value / se) if np.isfinite(se) and se > 0 else np.nan
        estimates.append({
            "term": term,
            "coefficient": float(value),
            "std_error_ml": se,
            "z_wald_ml": z_value,
            "p_wald_ml": float(2.0 * norm.sf(abs(z_value))) if np.isfinite(z_value) else np.nan,
        })
    spatial_cursor = beta_n
    for name in active_names:
        value = float(full_start[spatial_cursor])
        se = float(se_full[spatial_cursor]) if np.isfinite(se_full[spatial_cursor]) else np.nan
        z_value = float(value / se) if np.isfinite(se) and se > 0 else np.nan
        estimates.append({
            "term": name,
            "coefficient": value,
            "std_error_ml": se,
            "z_wald_ml": z_value,
            "p_wald_ml": float(2.0 * norm.sf(abs(z_value))) if np.isfinite(z_value) else np.nan,
        })
        spatial_cursor += 1

    return {
        "model": model_name,
        "n": n,
        "log_likelihood": float(loglik),
        "aic": float(aic),
        "bic": float(bic),
        "n_parameters": int(n_parameters),
        "rho": parts["rho"],
        "lambda": parts["lambda"],
        "sigma2": float(parts["sigma2"]),
        "optimizer_success": optimizer_success,
        "optimizer_message": optimizer_message,
        "covariance_status": "ok" if covariance is not None else "observed Hessian inversion failed",
        "estimates": estimates,
        "fitted": (y - parts["residual"].reshape(-1, 1)),
        "residual": parts["residual"],
        "innovation": (parts["residual"] - parts["lambda"] * (wd @ parts["residual"].reshape(-1, 1)).ravel()),
    }


def _lr_test(restricted: dict, unrestricted: dict) -> dict[str, float | str | int]:
    df = int(unrestricted["n_parameters"] - restricted["n_parameters"])
    raw = 2.0 * (float(unrestricted["log_likelihood"]) - float(restricted["log_likelihood"]))
    if raw < -1e-5 or df <= 0:
        return {"lr_statistic": float(raw), "df": df, "p_value": np.nan, "test_status": "nested-fit check failed"}
    statistic = max(raw, 0.0)
    return {
        "lr_statistic": float(statistic),
        "df": df,
        "p_value": float(chi2.sf(statistic, df)),
        "test_status": "ok",
    }


def _prepare_data() -> tuple[pd.DataFrame, gpd.GeoDataFrame, list[str]]:
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
    return d, gdf, missing_geometry


def _step1_moran(y, residuals, w, outcome, weight, n, seed_offset):
    return [
        {
            "outcome": outcome,
            "weight": weight,
            "measure": measure,
            "n": n,
            "islands": len(w.islands),
            "components": len(set(w.component_labels)),
            **_moran(values, w, SEED + seed_offset),
        }
        for measure, values in (("y_log1p", y.ravel()), ("ols_residual", residuals.ravel()))
    ]


def _step2_lm(y, x, w, outcome, weight, n):
    ols = PySAL_OLS(y, x, spat_diag=False, name_y=outcome)
    lm = LMtests(ols, w, tests=["lml", "rlml", "lme", "rlme", "sarma", "lmspdurbin"])
    diagnostics = {
        "LM_lag": lm.lml,
        "robust_LM_lag": lm.rlml,
        "LM_error": lm.lme,
        "robust_LM_error": lm.rlme,
        "LM_SARMA_joint": lm.sarma,
        "LM_SDM_joint": lm.lmspdurbin,
    }
    rows = []
    for test_name, (statistic, p_value) in diagnostics.items():
        rows.append({
            "outcome": outcome,
            "weight": weight,
            "n": n,
            "test": test_name,
            "statistic": float(statistic),
            "df": 1 if test_name not in {"LM_SARMA_joint", "LM_SDM_joint"} else (2 if test_name == "LM_SARMA_joint" else len(x[0]) + 1),
            "p_value": float(p_value),
        })
    return rows


def _self_test() -> dict:
    """Validate likelihood nesting on reproducible synthetic spatial data."""
    from libpysal.weights import lat2W
    from spreg import ML_Error as PySAL_ML_Error
    from spreg import ML_Lag as PySAL_ML_Lag

    rng = np.random.default_rng(20261019)
    w = lat2W(12, 12)
    w.transform = "r"
    wd = w.sparse.toarray()
    n = w.n
    x = rng.normal(size=(n, 3))
    names = ["x1", "x2", "x3"]
    beta = np.array([0.4, 0.6, -0.5, 0.3]).reshape(-1, 1)
    theta = np.array([0.55, -0.45, 0.40]).reshape(-1, 1)
    z = np.column_stack([np.ones(n), x])
    wx = wd @ x
    noise = rng.normal(size=(n, 1))

    def generate(rho: float, lam: float) -> np.ndarray:
        u = np.linalg.solve(np.eye(n) - lam * wd, noise)
        rhs = z @ beta + wx @ theta + u
        return np.linalg.solve(np.eye(n) - rho * wd, rhs)

    results = {}
    for label, rho, lam in (("SDM", 0.28, 0.0), ("SDEM", 0.0, 0.38), ("GNS", 0.28, 0.38)):
        y = generate(rho, lam)
        fits = {name: _fit_spatial_mle(y, x, w, name, names) for name in MODEL_FLAGS}
        if label == "SDM":
            test = _lr_test(fits["SAR"], fits["SDM"])
        elif label == "SDEM":
            test = _lr_test(fits["SEM"], fits["SDEM"])
        else:
            test = _lr_test(fits["SDM"], fits["GNS"])
        results[label] = {
            "target_comparison": test,
            "expected_unrestricted_model": label,
            "all_models_finite": all(np.isfinite(f["log_likelihood"]) for f in fits.values()),
            "all_spatial_fit_converged": all(f["optimizer_success"] for f in fits.values() if f["model"] != "OLS"),
        }
    if not all(v["all_models_finite"] and v["all_spatial_fit_converged"] for v in results.values()):
        raise AssertionError(f"Synthetic spatial likelihood check failed: {results}")
    if any(v["target_comparison"]["lr_statistic"] <= 0 for v in results.values()):
        raise AssertionError(f"Synthetic nested LR checks did not favor the generated model: {results}")
    validation_y = generate(0.28, 0.38)
    package_checks = []
    for name, estimator, kwargs, spatial_term in (
        ("SAR", PySAL_ML_Lag, {}, "rho"),
        ("SDM", PySAL_ML_Lag, {"slx_lags": 1}, "rho"),
        ("SEM", PySAL_ML_Error, {}, "lam"),
        ("SDEM", PySAL_ML_Error, {"slx_lags": 1}, "lam"),
    ):
        custom = _fit_spatial_mle(validation_y, x, w, name, names)
        reference = estimator(validation_y, x, w, method="ord", spat_diag=False, **kwargs)
        ll_diff = abs(custom["log_likelihood"] - float(reference.logll))
        spatial_diff = abs(custom["rho" if spatial_term == "rho" else "lambda"] - float(getattr(reference, spatial_term)))
        package_checks.append({"model": name, "abs_loglik_difference": ll_diff, "abs_spatial_parameter_difference": spatial_diff})
    if max(row["abs_loglik_difference"] for row in package_checks) > 1e-5 or max(
        row["abs_spatial_parameter_difference"] for row in package_checks
    ) > 1e-5:
        raise AssertionError(f"Custom restricted-model likelihood differs from PySAL: {package_checks}")
    results["restricted_model_reference_validation"] = {
        "reference": "PySAL spreg ML_Lag / ML_Error, method=ord",
        "models": package_checks,
        "passed_tolerance": 1e-5,
    }
    return results


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    d, gdf, missing_geometry = _prepare_data()
    outcomes = {
        "lost_capacity_mtco2_yr": "log_lost_capacity_mtco2_yr",
        "erosion_pct_of_gcw": "log_erosion_pct_of_gcw",
        "gcw_gdp_pct": "log_gcw_gdp_pct",
    }
    xnames = ["ln_gdp_per_capita", "ln_forest_area_mha", "warm_biome_share"]
    full_weights = _build_weights(gdf)
    moran_rows, lm_rows, coefficient_rows, legacy_model_rows, fit_rows, lr_rows, sample_rows = [], [], [], [], [], [], []
    for outcome_index, (outcome, _) in enumerate(outcomes.items()):
        cols = [outcome]
        if outcome != "gcw_gdp_pct":
            cols += ["reported_deforestation"]
        sample = d.loc[:, [*cols, *xnames]].replace([np.inf, -np.inf], np.nan).dropna()
        if outcome != "gcw_gdp_pct":
            sample = sample.loc[sample["reported_deforestation"].astype(bool)]
        y_raw = sample[outcome].to_numpy(dtype=float)
        y = np.log1p(y_raw).reshape(-1, 1)
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
        for weight_index, (weight_name, full_w) in enumerate(full_weights.items()):
            w = _weight_subsample(full_w, ids)
            ols_sm = sm.OLS(y, sm.add_constant(x, has_constant="add")).fit(cov_type="HC3")
            moran_rows.extend(_step1_moran(
                y, np.asarray(ols_sm.resid).reshape(-1, 1), w, outcome, weight_name, len(sample),
                weight_index + outcome_index * 10,
            ))
            lm_rows.extend(_step2_lm(y, x, w, outcome, weight_name, len(sample)))

            fits = {name: _fit_spatial_mle(y, x, w, name, xnames) for name in MODEL_FLAGS}
            for model_name, fit in fits.items():
                fit_rows.append({
                    "outcome": outcome,
                    "weight": weight_name,
                    "model": model_name,
                    "n": fit["n"],
                    "log_likelihood": fit["log_likelihood"],
                    "aic": fit["aic"],
                    "bic": fit["bic"],
                    "n_parameters": fit["n_parameters"],
                    "rho": fit["rho"],
                    "lambda": fit["lambda"],
                    "sigma2": fit["sigma2"],
                    "optimizer_success": fit["optimizer_success"],
                    "optimizer_message": fit["optimizer_message"],
                    "covariance_status": fit["covariance_status"],
                })
                for estimate in fit["estimates"]:
                    coefficient_rows.append({
                        "outcome": outcome,
                        "weight": weight_name,
                        "model": model_name,
                        "n": fit["n"],
                        **estimate,
                        "optimizer_success": fit["optimizer_success"],
                        "covariance_status": fit["covariance_status"],
                    })
                if model_name in {"OLS", "SAR", "SEM"}:
                    if model_name == "OLS":
                        estimates = [
                            {
                                "term": term,
                                "coefficient": float(ols_sm.params[i]),
                                "std_error": float(ols_sm.bse[i]),
                                "z": float(ols_sm.tvalues[i]),
                                "p_value": float(ols_sm.pvalues[i]),
                            }
                            for i, term in enumerate(["constant", *xnames])
                        ]
                    else:
                        estimates = [
                            {
                                "term": estimate["term"],
                                "coefficient": estimate["coefficient"],
                                "std_error": estimate["std_error_ml"],
                                "z": estimate["z_wald_ml"],
                                "p_value": estimate["p_wald_ml"],
                            }
                            for estimate in fit["estimates"]
                        ]
                    for estimate in estimates:
                        legacy_model_rows.append({
                            "outcome": outcome,
                            "weight": weight_name,
                            "model": model_name.lower() if model_name != "OLS" else "ols_hc3",
                            **estimate,
                            "n": fit["n"],
                            "aic": fit["aic"],
                            "log_likelihood": fit["log_likelihood"],
                            "model_status": "ok" if fit["optimizer_success"] else "optimizer warning",
                        })
            comparisons = (
                ("SDM_vs_SAR", "SAR", "SDM"),
                ("SDEM_vs_SEM", "SEM", "SDEM"),
                ("GNS_vs_SDM", "SDM", "GNS"),
            )
            for comparison, restricted_name, unrestricted_name in comparisons:
                lr = _lr_test(fits[restricted_name], fits[unrestricted_name])
                lr_rows.append({
                    "outcome": outcome,
                    "weight": weight_name,
                    "comparison": comparison,
                    "restricted_model": restricted_name,
                    "unrestricted_model": unrestricted_name,
                    "n": len(sample),
                    **lr,
                })

    moran = pd.DataFrame(moran_rows)
    moran["p_holm_all_six_per_measure"] = _holm_by_group(moran, "p_permutation_two_sided", ["measure"])
    lms = pd.DataFrame(lm_rows)
    lms["p_holm_across_six_cases"] = _holm_by_group(lms, "p_value", ["test"])
    lrs = pd.DataFrame(lr_rows)
    lrs["p_holm_across_six_cases"] = _holm_by_group(lrs, "p_value", ["comparison"])
    fits_df = pd.DataFrame(fit_rows)
    fits_df["aic_rank"] = fits_df.groupby(["outcome", "weight"])["aic"].rank(method="min").astype(int)
    fits_df["bic_rank"] = fits_df.groupby(["outcome", "weight"])["bic"].rank(method="min").astype(int)

    moran.to_csv(OUT / "spatial_sequence_step1_moran.csv", index=False)
    lms.to_csv(OUT / "spatial_sequence_step2_lm_tests.csv", index=False)
    lrs.to_csv(OUT / "spatial_sequence_step3_nested_tests.csv", index=False)
    fits_df.to_csv(OUT / "spatial_sequence_model_fit.csv", index=False)
    pd.DataFrame(coefficient_rows).to_csv(OUT / "spatial_sequence_model_coefficients.csv", index=False)
    pd.DataFrame(sample_rows).to_csv(OUT / "spatial_sequence_sample_audit.csv", index=False)

    # Keep legacy filenames current so existing inventory/build scripts use the refreshed diagnostics.
    moran.loc[moran["measure"].eq("y_log1p")].drop(columns=["measure", "p_holm_all_six_per_measure"]).to_csv(
        OUT / "spatial_moran_comparison.csv", index=False
    )
    moran.loc[moran["measure"].eq("ols_residual")].drop(columns=["measure", "p_holm_all_six_per_measure"]).to_csv(
        OUT / "spatial_ols_residual_moran.csv", index=False
    )
    pd.DataFrame(legacy_model_rows).to_csv(OUT / "spatial_models_comparison.csv", index=False)
    lms.to_csv(OUT / "spatial_lm_diagnostics.csv", index=False)

    diagnostics = {
        "date": "2026-10-23",
        "boundary_source": "Natural Earth 50m admin-0 country polygons",
        "units_with_geometry": int(len(d)),
        "units_without_geometry": missing_geometry,
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "weights": {
            "queen_contiguity": "row-standardised Queen contiguity; isolates retained as zero rows",
            "symmetric_knn5": "row-standardised symmetrised kNN-5 of representative points in EPSG:6933",
        },
        "outcomes": list(outcomes),
        "predictors": xnames,
        "y_transform": "log1p; the same complete-case sample is used across OLS and spatial models per outcome",
        "model_sequence": {
            "step1": "global Moran I on transformed y and OLS residuals; 9,999 permutations; Holm adjustment across the six cases for each measure",
            "step2": "LM-lag, robust LM-lag, LM-error, robust LM-error, joint SARMA and joint SDM tests on OLS residuals; Holm adjustment by test across six cases",
            "step3": "Gaussian ML LR comparisons: SDM vs SAR (theta=0), SDEM vs SEM (theta=0), GNS vs SDM (lambda=0); Holm adjustment by comparison across six cases",
            "step4": "AIC/BIC ranks are reported mechanically for human selection; the script does not declare a scientific winner or interpret coefficients causally",
        },
        "likelihood": "Concentrated Gaussian likelihood, with log|I-rho W| and log|I-lambda W| Jacobians; beta and WX coefficients profiled by least squares.",
        "caveats": [
            "Exploratory cross-sectional associations, not causal effects.",
            "Classic LM and Gaussian ML comparisons assume homoskedastic innovations; HC3 OLS standard errors do not change the LM test assumptions.",
            "Reported deforestation outcomes are complete cases among reporting units; non-reporting is not coded as zero.",
            "Queen isolates are retained; kNN connects islands to their nearest territories, which can be distant or separated by water.",
            "No final model is selected automatically; AIC/BIC ranks and nested test outcomes are reported as model-comparison evidence.",
        ],
        "territory_crosswalk": {
            "FRA": "Natural Earth ADM0_A3 key; overseas polygons split by location.",
            "NOR": "Svalbard and Jan Mayen split from Norway by location.",
            "BES": "Bonaire, Sint Eustatius and Saba split from the Netherlands multipolygon.",
            "TKL": "Tokelau split from New Zealand multipolygon.",
            "GIB": "No polygon in Natural Earth 50m; excluded.",
        },
    }
    (OUT / "spatial_sequence_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    queen_full = full_weights["queen_contiguity"]
    knn_full = full_weights["symmetric_knn5"]
    legacy_diagnostics = {
        "date": "2026-10-23",
        "boundary_source": "Natural Earth 50m admin-0 country polygons",
        "units_with_geometry": int(len(d)),
        "units_without_geometry": missing_geometry,
        "queen": {
            "n": len(queen_full.id_order),
            "islands": list(queen_full.islands),
            "n_islands": len(queen_full.islands),
            "n_components": len(set(queen_full.component_labels)),
        },
        "knn": {
            "k": K_NEIGHBOURS,
            "symmetrized": True,
            "distance_crs": "EPSG:6933",
            "n_islands": len(knn_full.islands),
            "n_components": len(set(knn_full.component_labels)),
        },
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "predictors": xnames,
        "transform": "log1p outcome; numeric predictors in native transformed units",
        "model_sequence": diagnostics["model_sequence"],
        "caveats": diagnostics["caveats"],
        "territory_crosswalk": diagnostics["territory_crosswalk"],
    }
    (OUT / "spatial_analysis_diagnostics.json").write_text(
        json.dumps(legacy_diagnostics, indent=2), encoding="utf-8"
    )
    return diagnostics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="run synthetic likelihood nesting checks only")
    args = parser.parse_args()
    if args.self_test:
        checks = _self_test()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "spatial_sequence_synthetic_self_test.json").write_text(
            json.dumps(checks, indent=2), encoding="utf-8"
        )
        print(json.dumps(checks, indent=2))
    else:
        print(json.dumps(run(), indent=2))
