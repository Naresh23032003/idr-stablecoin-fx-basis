"""Vector Error Correction Model (VECM), 3-variable intraday VECM, full-system half-life, and return pass-through."""
from __future__ import annotations

import math
from itertools import permutations
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen


def compute_vecm_system_half_life(res, beta_vec: np.ndarray, max_h: int = 200) -> Dict[str, Any]:
    """Compute persistence and half-life from the full estimated VECM dynamics.

    Reports three complementary measures in native sampling units:
    1. Companion-matrix asymptotic half-life from the largest non-unit eigenvalue
       modulus |lambda_max| of the levels VAR(p+1) companion matrix: -ln(2)/ln(|lambda_max|).
    2. Scalar error-correction persistence 1 + beta' * alpha (exact when k_ar_diff = 0):
       -ln(2)/ln(|1 + beta' * alpha|).
    3. Exact impulse-response half-life of the cointegrating error z_t = beta' Y_t
       following a unit shock to the local price (e_1) and a generalized shock
       d_gen = Sigma * beta / (beta' * Sigma * beta).
    """
    A = res.var_rep  # shape (k_ar, n, n) where k_ar = k_ar_diff + 1
    k_ar, n, _ = A.shape
    F = np.zeros((n * k_ar, n * k_ar), dtype=float)
    for i in range(k_ar):
        F[:n, i * n : (i + 1) * n] = A[i]
    if k_ar > 1:
        F[n:, :-n] = np.eye(n * (k_ar - 1))

    eigvals = np.linalg.eigvals(F)
    r = int(res.coint_rank)
    n_unit = n - r
    idx_by_unit = np.argsort(np.abs(eigvals - 1.0))
    non_unit_eigs = eigvals[idx_by_unit[n_unit:]]
    sorted_mods = np.sort(np.abs(non_unit_eigs))[::-1] if len(non_unit_eigs) > 0 else np.array([])
    max_non_unit_mod = float(sorted_mods[0]) if len(sorted_mods) > 0 else float("nan")
    top3_mods = [round(float(x), 5) for x in sorted_mods[:3]]
    if 0.0 < max_non_unit_mod < 1.0:
        hl_companion = float(-math.log(2.0) / math.log(max_non_unit_mod))
    else:
        hl_companion = float("nan")

    alpha_vec = res.alpha[:, 0]
    scalar_root = float(1.0 + float(beta_vec @ alpha_vec))
    if 0.0 < abs(scalar_root) < 1.0:
        hl_scalar = float(-math.log(2.0) / math.log(abs(scalar_root)))
    else:
        hl_scalar = float("nan")

    Sigma = np.cov(res.resid, rowvar=False)
    e1 = np.zeros(n, dtype=float)
    e1[0] = 1.0
    denom_gen = float(beta_vec @ Sigma @ beta_vec)
    d_gen = (Sigma @ beta_vec) / denom_gen if denom_gen > 0 else e1

    def _irf_hl(d0: np.ndarray) -> float:
        state = np.zeros(n * k_ar, dtype=float)
        state[:n] = d0
        z_path = [float(beta_vec @ state[:n])]
        for _ in range(max_h):
            state = F @ state
            z_path.append(float(beta_vec @ state[:n]))
        z_arr = np.asarray(z_path, dtype=float)
        z0 = abs(z_arr[0])
        if z0 <= 0.0:
            return float("nan")
        above = np.where(np.abs(z_arr) >= 0.5 * z0)[0]
        if len(above) == 0:
            return 0.0
        last_above = int(above[-1])
        if last_above >= max_h:
            return float("nan")
        y0 = abs(z_arr[last_above])
        y1 = abs(z_arr[last_above + 1])
        frac = (y0 - 0.5 * z0) / (y0 - y1) if y0 != y1 else 0.0
        return float(last_above + frac)

    return {
        "scalar_root_1_plus_ba": scalar_root,
        "half_life_scalar": hl_scalar,
        "max_non_unit_eig": max_non_unit_mod,
        "top3_non_unit_eigs": top3_mods,
        "half_life_companion": hl_companion,
        "half_life_irf_local": _irf_hl(e1),
        "half_life_irf_gen": _irf_hl(d_gen),
        "is_monotone_damping": bool(0.0 < scalar_root < 1.0),
    }


def estimate_bivariate_vecm(
    y_local: np.ndarray,
    y_global: np.ndarray,
    k_ar_diff: int = 1,
    det_order: str = "co",
    hac_lags: int = 5,
    sampling_unit: str = "days",
) -> Dict[str, Any]:
    """Estimate bivariate VECM, weak-exogeneity tests, residual diagnostics, and full-system half-life.

    Never converts daily coefficients into intraday hours.
    """
    Y = np.column_stack([np.asarray(y_local, dtype=float), np.asarray(y_global, dtype=float)])
    Y = Y[np.all(np.isfinite(Y), axis=1)]

    vecm = VECM(Y, k_ar_diff=k_ar_diff, coint_rank=1, deterministic=det_order)
    res = vecm.fit()

    alpha_local = float(res.alpha[0, 0])
    alpha_global = float(res.alpha[1, 0])
    se_local = float(res.stderr_alpha[0, 0])
    se_global = float(res.stderr_alpha[1, 0])

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

    # Full-system VECM half-life in NATIVE sampling units
    hl_info = compute_vecm_system_half_life(res, beta_vec)

    # Residual diagnostics on local equation
    lb = acorr_ljungbox(ols_l.resid, lags=[min(10, max(2, len(ols_l.resid) // 5))], return_df=True)
    arch_stat, arch_p, _, _ = het_arch(ols_l.resid, nlags=min(5, max(1, len(ols_l.resid) // 10)))

    # Residual correlation across markets & Price Discovery (Gonzalo-Granger using ML alpha & Hasbrouck IS bounds)
    Sigma = np.cov(res.resid, rowvar=False)
    corr_u = float(Sigma[0, 1] / np.sqrt(Sigma[0, 0] * Sigma[1, 1]))
    abs_sum_a = abs(alpha_local) + abs(alpha_global)
    gg_global = float(abs(alpha_local) / abs_sum_a) if abs_sum_a > 0 else float("nan")
    gg_local = float(abs(alpha_global) / abs_sum_a) if abs_sum_a > 0 else float("nan")
    psi = np.array([alpha_global, -alpha_local], dtype=float)
    denom_is = float(psi @ Sigma @ psi)
    if denom_is > 0:
        F1 = np.linalg.cholesky(Sigma)
        p1 = psi @ F1
        is_g_1 = float((p1[1] ** 2) / denom_is)
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
        "scalar_root_1_plus_ba": hl_info["scalar_root_1_plus_ba"],
        "max_non_unit_eig": hl_info["max_non_unit_eig"],
        "half_life_native_units": hl_info["half_life_companion"],
        "half_life_scalar_units": hl_info["half_life_scalar"],
        "half_life_irf_local_units": hl_info["half_life_irf_local"],
        "half_life_irf_gen_units": hl_info["half_life_irf_gen"],
        "is_monotone_damping": hl_info["is_monotone_damping"],
        "adj_r2_local": float(ols_l.rsquared_adj),
        "adj_r2_global": float(ols_g.rsquared_adj),
        "resid_corr_cross_market": corr_u,
        "gg_share_global": gg_global,
        "gg_share_local": gg_local,
        "gg_basis": "ML_alpha",
        "hasbrouck_is_global_low": is_global_low,
        "hasbrouck_is_global_high": is_global_high,
        "hasbrouck_is_global_mid": is_global_mid,
        "is_identification_status": is_ident_status,
        "ljung_box_pval_local": float(lb["lb_pvalue"].iloc[0]),
        "arch_lm_pval_local": float(arch_p),
    }


def estimate_trivariate_vecm(
    y1: np.ndarray,
    y2: np.ndarray,
    y3: np.ndarray,
    names: List[str] = ("Indodax_BTCIDR", "Binance_BTCUSDT", "Indodax_USDTIDR"),
    k_ar_diff: int = 5,
    det_order: str = "co",
    hac_lags: int = 12,
    sampling_unit: str = "5m_bars",
) -> Dict[str, Any]:
    """Estimate 3-variable VECM separating local BTC/IDR, global BTC/USDT, and local/ref USDT/IDR.

    Avoids embedding domestic USDT/IDR into a synthetic global BTC/IDR series.
    Computes Johansen rank tests (r=0,1,2), ML and HAC adjustment coefficients,
    adjustment-burden shares, exact Granger permanent-impact matrix Psi(1),
    6-permutation Cholesky Hasbrouck IS bounds for the permanent component of y1,
    and full-system companion/scalar/IRF half-lives.
    """
    Y = np.column_stack([np.asarray(y1, dtype=float), np.asarray(y2, dtype=float), np.asarray(y3, dtype=float)])
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    n = 3

    joh = coint_johansen(Y, det_order=0, k_ar_diff=k_ar_diff)
    vecm = VECM(Y, k_ar_diff=k_ar_diff, coint_rank=1, deterministic=det_order)
    res = vecm.fit()

    beta = res.beta[:, 0]  # normalized with beta[0] = 1
    alpha_ml = res.alpha[:, 0]
    se_ml = res.stderr_alpha[:, 0]
    pval_ml = res.pvalues_alpha[:, 0]

    ect = Y @ beta
    dY = np.diff(Y, axis=0)
    p = k_ar_diff
    ect_lag = ect[p:-1]
    cols = [ect_lag, np.ones(len(ect_lag))]
    for j in range(1, p + 1):
        for m in range(n):
            cols.append(dY[p - j : len(dY) - j, m])
    X = np.column_stack(cols)

    alpha_hac, se_hac, pval_hac, lb_pvals, arch_pvals = [], [], [], [], []
    for m in range(n):
        ols_m = sm.OLS(dY[p:, m], X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
        alpha_hac.append(float(ols_m.params[0]))
        se_hac.append(float(ols_m.bse[0]))
        pval_hac.append(float(ols_m.pvalues[0]))
        lb = acorr_ljungbox(ols_m.resid, lags=[min(10, max(2, len(ols_m.resid) // 5))], return_df=True)
        _, arch_p, _, _ = het_arch(ols_m.resid, nlags=min(5, max(1, len(ols_m.resid) // 10)))
        lb_pvals.append(float(lb["lb_pvalue"].iloc[0]))
        arch_pvals.append(float(arch_p))

    hl_info = compute_vecm_system_half_life(res, beta)

    Sigma = np.cov(res.resid, rowvar=False)
    D = np.sqrt(np.diag(Sigma))
    Corr = Sigma / np.outer(D, D)

    # Granger permanent-impact matrix Psi(1) = beta_perp (alpha_perp' Gamma beta_perp)^{-1} alpha_perp'
    Gamma = np.eye(n)
    for j in range(p):
        Gamma -= res.gamma[:, j * n : (j + 1) * n]
    _, _, Vt_b = np.linalg.svd(beta.reshape(1, -1))
    beta_perp = Vt_b[1:].T  # (3, 2)
    _, _, Vt_a = np.linalg.svd(alpha_ml.reshape(1, -1))
    alpha_perp = Vt_a[1:].T  # (3, 2)
    Psi1 = beta_perp @ np.linalg.inv(alpha_perp.T @ Gamma @ beta_perp) @ alpha_perp.T

    # 6-permutation Cholesky Hasbrouck IS for the permanent component of y1 (row 0 of Psi1)
    psi_row0 = Psi1[0, :]
    tot_var0 = float(psi_row0 @ Sigma @ psi_row0)
    is_by_mkt: Dict[int, List[float]] = {i: [] for i in range(n)}
    for perm in permutations(range(n)):
        P = np.zeros((n, n), dtype=float)
        for new_i, old_i in enumerate(perm):
            P[new_i, old_i] = 1.0
        Sigma_p = P @ Sigma @ P.T
        F_chol = np.linalg.cholesky(Sigma_p)
        psi_p = psi_row0 @ P.T
        contrib = (psi_p @ F_chol) ** 2 / tot_var0
        for new_i, old_i in enumerate(perm):
            is_by_mkt[old_i].append(float(contrib[new_i]))

    abs_sum_ml = float(np.sum(np.abs(alpha_ml)))
    adj_share_ml = [float(abs(a) / abs_sum_ml) for a in alpha_ml]

    return {
        "names": list(names),
        "n_levels": int(len(Y)),
        "T_eff": int(len(ect_lag)),
        "k_ar_diff": int(k_ar_diff),
        "sampling_unit": sampling_unit,
        "joh_trace": [float(x) for x in joh.lr1],
        "joh_cvt95": [float(x) for x in joh.cvt[:, 1]],
        "beta": [float(x) for x in beta],
        "alpha_ml": [float(x) for x in alpha_ml],
        "se_ml": [float(x) for x in se_ml],
        "pval_ml": [float(x) for x in pval_ml],
        "alpha_hac": alpha_hac,
        "se_hac": se_hac,
        "pval_hac": pval_hac,
        "adj_share_ml_pct": [round(100.0 * x, 2) for x in adj_share_ml],
        "psi1_row0": [float(x) for x in psi_row0],
        "resid_corr_matrix": Corr.tolist(),
        "hasbrouck_is_y1_bounds": {
            names[i]: {
                "low": float(min(is_by_mkt[i])),
                "high": float(max(is_by_mkt[i])),
                "mean": float(np.mean(is_by_mkt[i])),
            }
            for i in range(n)
        },
        "scalar_root_1_plus_ba": hl_info["scalar_root_1_plus_ba"],
        "max_non_unit_eig": hl_info["max_non_unit_eig"],
        "top3_non_unit_eigs": hl_info["top3_non_unit_eigs"],
        "half_life_companion": hl_info["half_life_companion"],
        "half_life_scalar": hl_info["half_life_scalar"],
        "half_life_irf_local": hl_info["half_life_irf_local"],
        "half_life_irf_gen": hl_info["half_life_irf_gen"],
        "ljung_box_pvals": lb_pvals,
        "arch_lm_pvals": arch_pvals,
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

    X1 = sm.add_constant(df[["r_usdt", "r_u"]])
    m1 = sm.OLS(df["r_idr"], X1).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

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
