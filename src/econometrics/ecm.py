"""Vector Error Correction Model (VECM), univariate ECM, weak exogeneity, and return pass-through."""
from __future__ import annotations

import math
from typing import Dict, Any
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.vector_ar.vecm import VECM


def estimate_bivariate_vecm(
    y_local: np.ndarray,
    y_global: np.ndarray,
    k_ar_diff: int = 1,
    det_order: str = "co",
    hac_lags: int = 5,
    sampling_unit: str = "days",
) -> Dict[str, Any]:
    """Estimate bivariate VECM, weak-exogeneity tests, residual diagnostics, and native-unit half-life.

    Never converts daily coefficients into intraday hours!
    """
    Y = np.column_stack([np.asarray(y_local, dtype=float), np.asarray(y_global, dtype=float)])
    Y = Y[np.all(np.isfinite(Y), axis=1)]

    vecm = VECM(Y, k_ar_diff=k_ar_diff, coint_rank=1, deterministic=det_order)
    res = vecm.fit()

    alpha_local = float(res.alpha[0, 0])
    alpha_global = float(res.alpha[1, 0])
    se_local = float(res.stderr_alpha[0, 0])
    se_global = float(res.stderr_alpha[1, 0])

    # Weak exogeneity tests (conditional ML z/Wald p-value on H0: alpha_i = 0, plus HAC below)
    we_local_pval = float(res.pvalues_alpha[0, 0])
    we_global_pval = float(res.pvalues_alpha[1, 0])

    # Error-correction OLS with HAC SE on estimated cointegrating error ect_{t-1}
    beta_vec = res.beta[:, 0]  # normalized with beta[0] = 1
    ect = Y @ beta_vec
    dY = np.diff(Y, axis=0)
    p = k_ar_diff
    dep_l = dY[p:, 0]
    dep_g = dY[p:, 1]
    ect_lag = ect[p:-1]
    cols = [ect_lag, np.ones(len(dep_l))]
    for j in range(1, p + 1):
        cols.append(dY[p - j : len(dY) - j, 0])
        cols.append(dY[p - j : len(dY) - j, 1])
    X = np.column_stack(cols)
    ols_l = sm.OLS(dep_l, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    ols_g = sm.OLS(dep_g, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

    a_l_hac = float(ols_l.params[0])
    se_l_hac = float(ols_l.bse[0])
    p_l_hac = float(ols_l.pvalues[0])

    a_g_hac = float(ols_g.params[0])
    se_g_hac = float(ols_g.bse[0])
    p_g_hac = float(ols_g.pvalues[0])

    # Half-life in NATIVE sampling units only
    root_local = 1.0 + a_l_hac
    if 0.0 < root_local < 1.0:
        half_life_native = float(-math.log(2.0) / math.log(root_local))
        is_monotone_stable = True
    elif -1.0 < root_local < 0.0:
        half_life_native = float(-math.log(2.0) / math.log(abs(root_local)))
        is_monotone_stable = False  # oscillatory damping
    else:
        half_life_native = float("nan")
        is_monotone_stable = False

    # Residual diagnostics on local equation
    lb = acorr_ljungbox(ols_l.resid, lags=[min(10, max(2, len(ols_l.resid) // 5))], return_df=True)
    arch_stat, arch_p, _, _ = het_arch(ols_l.resid, nlags=min(5, max(1, len(ols_l.resid) // 10)))

    # Residual correlation across markets & Price Discovery (Gonzalo-Granger & Hasbrouck IS bounds)
    Sigma = np.cov(res.resid, rowvar=False)
    corr_u = float(Sigma[0, 1] / np.sqrt(Sigma[0, 0] * Sigma[1, 1]))
    # Gonzalo-Granger permanent factor weights (orthogonal to alpha): psi_raw = [alpha_global, -alpha_local]
    # Note: both rows of Psi(1) = beta_perp (alpha_perp^T Gamma beta_perp)^{-1} alpha_perp^T have the same ratio alpha_perp^T
    abs_sum_a = abs(alpha_local) + abs(alpha_global)
    gg_global = float(abs(alpha_local) / abs_sum_a) if abs_sum_a > 0 else float("nan")
    gg_local = float(abs(alpha_global) / abs_sum_a) if abs_sum_a > 0 else float("nan")
    psi = np.array([alpha_global, -alpha_local], dtype=float)
    denom_is = float(psi @ Sigma @ psi)
    if denom_is > 0:
        # Ordering 1: [local, global]
        F1 = np.linalg.cholesky(Sigma)
        p1 = psi @ F1
        is_g_1 = float((p1[1] ** 2) / denom_is)
        # Ordering 2: [global, local]
        perm = np.array([[0, 1], [1, 0]], dtype=float)
        Sigma_p = perm @ Sigma @ perm.T
        F2 = np.linalg.cholesky(Sigma_p)
        p2 = (psi @ perm.T) @ F2
        is_g_2 = float((p2[0] ** 2) / denom_is)
        is_global_low = float(min(is_g_1, is_g_2))
        is_global_high = float(max(is_g_1, is_g_2))
        is_global_mid = float(0.5 * (is_global_low + is_global_high))
    else:
        is_global_low = is_global_high = is_global_mid = float("nan")
    is_ident_status = "HIGH_CONTEMPORANEOUS_CORR_BOUNDS_WIDE" if abs(corr_u) > 0.90 else "INFORMATIVE_CHOLESKY_BOUNDS"

    return {
        "n_levels": int(len(Y)),
        "T_eff": int(len(dep_l)),
        "k_ar_diff": int(k_ar_diff),
        "sampling_unit": sampling_unit,
        "beta_normalized": float(-beta_vec[1]),
        "alpha_local_ml": alpha_local,
        "alpha_local_ml_se": se_local,
        "alpha_global_ml": alpha_global,
        "alpha_global_ml_se": se_global,
        "weak_exog_local_pval": we_local_pval,
        "weak_exog_global_pval": we_global_pval,
        "alpha_local_hac": a_l_hac,
        "alpha_local_hac_se": se_l_hac,
        "alpha_local_hac_t": float(ols_l.tvalues[0]),
        "alpha_local_hac_pval": p_l_hac,
        "alpha_local_ci95_low": float(a_l_hac - 1.96 * se_l_hac),
        "alpha_local_ci95_high": float(a_l_hac + 1.96 * se_l_hac),
        "alpha_global_hac": a_g_hac,
        "alpha_global_hac_se": se_g_hac,
        "alpha_global_hac_t": float(ols_g.tvalues[0]),
        "alpha_global_hac_pval": p_g_hac,
        "implied_ar_root_local": float(root_local),
        "half_life_native_units": half_life_native,
        "is_monotone_damping": is_monotone_stable,
        "adj_r2_local": float(ols_l.rsquared_adj),
        "adj_r2_global": float(ols_g.rsquared_adj),
        "resid_corr_cross_market": corr_u,
        "gg_share_global": gg_global,
        "gg_share_local": gg_local,
        "hasbrouck_is_global_low": is_global_low,
        "hasbrouck_is_global_high": is_global_high,
        "hasbrouck_is_global_mid": is_global_mid,
        "is_identification_status": is_ident_status,
        "ljung_box_pval_local": float(lb["lb_pvalue"].iloc[0]),
        "arch_lm_pval_local": float(arch_p),
    }


def estimate_return_passthrough(
    p_idr: np.ndarray,
    p_usdt: np.ndarray,
    u_idr: np.ndarray,
    s_fx: np.ndarray | None = None,
    hac_lags: int = 5,
) -> Dict[str, Any]:
    """Estimate contemporaneous and 1-lag return pass-through regressions with HAC SE."""
    r_idr = np.diff(np.log(np.asarray(p_idr, dtype=float)))
    r_usdt = np.diff(np.log(np.asarray(p_usdt, dtype=float)))
    r_u = np.diff(np.log(np.asarray(u_idr, dtype=float)))

    df = pd.DataFrame({"r_idr": r_idr, "r_usdt": r_usdt, "r_u": r_u})
    if s_fx is not None:
        df["r_fx"] = np.diff(np.log(np.asarray(s_fx, dtype=float)))
    df["r_usdt_lag1"] = df["r_usdt"].shift(1)
    df["r_u_lag1"] = df["r_u"].shift(1)
    df = df.dropna().reset_index(drop=True)

    # Model 1: r_idr ~ const + r_usdt + r_u
    X1 = sm.add_constant(df[["r_usdt", "r_u"]])
    m1 = sm.OLS(df["r_idr"], X1).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

    # Model 2: add 1 lag
    X2 = sm.add_constant(df[["r_usdt", "r_usdt_lag1", "r_u", "r_u_lag1"]])
    m2 = sm.OLS(df["r_idr"], X2).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

    out = {
        "n_obs": int(len(df)),
        "m1_const": float(m1.params["const"]),
        "m1_beta_global_crypto": float(m1.params["r_usdt"]),
        "m1_beta_global_crypto_se": float(m1.bse["r_usdt"]),
        "m1_beta_usdt_idr": float(m1.params["r_u"]),
        "m1_beta_usdt_idr_se": float(m1.bse["r_u"]),
        "m1_adj_r2": float(m1.rsquared_adj),
        "m2_beta_global_crypto_t0": float(m2.params["r_usdt"]),
        "m2_beta_global_crypto_t1": float(m2.params["r_usdt_lag1"]),
        "m2_beta_global_crypto_t1_pval": float(m2.pvalues["r_usdt_lag1"]),
        "m2_beta_usdt_idr_t0": float(m2.params["r_u"]),
        "m2_beta_usdt_idr_t1": float(m2.params["r_u_lag1"]),
        "m2_adj_r2": float(m2.rsquared_adj),
    }

    if "r_fx" in df.columns:
        df["r_sf_wedge"] = df["r_u"] - df["r_fx"]
        X3 = sm.add_constant(df[["r_usdt", "r_fx", "r_sf_wedge"]])
        m3 = sm.OLS(df["r_idr"], X3).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
        out.update(
            {
                "m3_beta_global_crypto": float(m3.params["r_usdt"]),
                "m3_beta_global_crypto_se": float(m3.bse["r_usdt"]),
                "m3_beta_fx_jisdor": float(m3.params["r_fx"]),
                "m3_beta_fx_jisdor_se": float(m3.bse["r_fx"]),
                "m3_beta_fx_jisdor_pval": float(m3.pvalues["r_fx"]),
                "m3_beta_sf_wedge": float(m3.params["r_sf_wedge"]),
                "m3_beta_sf_wedge_se": float(m3.bse["r_sf_wedge"]),
                "m3_beta_sf_wedge_pval": float(m3.pvalues["r_sf_wedge"]),
                "m3_adj_r2": float(m3.rsquared_adj),
            }
        )
    return out
