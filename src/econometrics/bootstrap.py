"""Null-imposed restricted VECM i.i.d. residual bootstrap for Johansen rank tests."""
from __future__ import annotations

import math
from typing import Dict, Any, List
import numpy as np
from statsmodels.tsa.vector_ar.vecm import coint_johansen


def _fast_johansen_trace_maxeig(Y: np.ndarray, det_order: int = 0, k_ar_diff: int = 1) -> tuple[float, float]:
    """Compute Johansen r=0 trace and max-eigenvalue statistics cleanly."""
    res = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
    return float(res.lr1[0]), float(res.lr2[0])


def null_imposed_vecm_residual_bootstrap(
    Y: np.ndarray,
    det_order: int = 0,
    k_ar_diff: int = 1,
    n_boot: int = 9999,
    seed: int = 20261113,
) -> Dict[str, Any]:
    """Null-imposed restricted VECM i.i.d. residual bootstrap (Cavaliere, Rahbek & Taylor 2012 style).

    Null hypothesis: H0: rank(Pi) = 0 (no cointegration, Pi = 0).
    Restricted DGP under H0:
        dY_t = mu_0 + sum_{i=1}^{k_ar_diff} Gamma_{0,i} dY_{t-i} + u_t
    Innovations u_t are centered and resampled i.i.d. as whole T-dimensional vectors
    with replacement, preserving exact contemporaneous cross-market covariance Sigma_u.
    Initial differences are fixed at the observed pre-sample values.
    Every bootstrap draw is re-estimated with the exact same (det_order, k_ar_diff).
    """
    Y = np.asarray(Y, dtype=float)
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    N, n = Y.shape
    p = k_ar_diff  # number of lagged differences in VECM
    k = p + 1      # VAR order in levels

    trace_obs, max_obs = _fast_johansen_trace_maxeig(Y, det_order=det_order, k_ar_diff=k_ar_diff)

    dY = np.diff(Y, axis=0)  # shape (N-1, n)
    T_eff = len(dY) - p
    if T_eff < 10:
        raise ValueError(f"Insufficient effective observations T_eff={T_eff} for bootstrap")

    # Build restricted VAR(p) design matrix under H0: Pi = 0
    dep = dY[p:]  # (T_eff, n)
    cols = []
    if det_order >= 0:
        cols.append(np.ones(T_eff))
    for i in range(1, p + 1):
        cols.append(dY[p - i : len(dY) - i])
    X = np.column_stack(cols) if cols else np.empty((T_eff, 0))

    B_hat, _, _, _ = np.linalg.lstsq(X, dep, rcond=None)
    resid = dep - X @ B_hat
    resid_centered = resid - resid.mean(axis=0, keepdims=True)

    # Extract fitted intercept and Gamma matrices
    col_ptr = 0
    mu_hat = np.zeros(n)
    if det_order >= 0:
        mu_hat = B_hat[0, :]
        col_ptr = 1
    gammas = []
    for i in range(p):
        gammas.append(B_hat[col_ptr + i * n : col_ptr + (i + 1) * n, :])

    rng = np.random.default_rng(seed)
    trace_boot = np.empty(n_boot, dtype=float)
    max_boot = np.empty(n_boot, dtype=float)
    n_failed = 0
    valid_count = 0

    init_Y = Y[: k]  # first k level rows (k-1 initial differences)
    init_dY = dY[: p]

    for b in range(n_boot):
        idx = rng.integers(0, T_eff, size=T_eff)
        u_star = resid_centered[idx, :]

        dY_star = np.empty((len(dY), n), dtype=float)
        if p > 0:
            dY_star[:p, :] = init_dY
        for t in range(p, len(dY)):
            val = mu_hat.copy()
            for i in range(1, p + 1):
                val += dY_star[t - i, :] @ gammas[i - 1]
            dY_star[t, :] = val + u_star[t - p, :]

        Y_star = np.empty((N, n), dtype=float)
        Y_star[0, :] = init_Y[0, :]
        Y_star[1:, :] = Y_star[0, :] + np.cumsum(dY_star, axis=0)

        try:
            tr_b, mx_b = _fast_johansen_trace_maxeig(Y_star, det_order=det_order, k_ar_diff=k_ar_diff)
            if np.isfinite(tr_b) and np.isfinite(mx_b):
                trace_boot[valid_count] = tr_b
                max_boot[valid_count] = mx_b
                valid_count += 1
            else:
                n_failed += 1
        except Exception:
            n_failed += 1

    tr_arr = trace_boot[:valid_count]
    mx_arr = max_boot[:valid_count]

    p_trace = (1.0 + float(np.sum(tr_arr >= trace_obs))) / (valid_count + 1.0)
    p_max = (1.0 + float(np.sum(mx_arr >= max_obs))) / (valid_count + 1.0)
    mc_se_trace = math.sqrt(p_trace * (1.0 - p_trace) / valid_count)
    mc_se_max = math.sqrt(p_max * (1.0 - p_max) / valid_count)

    return {
        "method": "null_imposed_restricted_vecm_iid_residual_bootstrap",
        "null_hypothesis": "H0: rank(Pi) = 0",
        "n_levels": int(N),
        "T_eff": int(T_eff),
        "n_vars": int(n),
        "det_order": int(det_order),
        "k_ar_diff": int(k_ar_diff),
        "n_boot_requested": int(n_boot),
        "n_boot_valid": int(valid_count),
        "n_failed": int(n_failed),
        "seed": int(seed),
        "trace_obs": float(trace_obs),
        "trace_boot_pval": float(p_trace),
        "trace_mc_se": float(mc_se_trace),
        "trace_boot_cv90": float(np.quantile(tr_arr, 0.90)),
        "trace_boot_cv95": float(np.quantile(tr_arr, 0.95)),
        "trace_boot_cv99": float(np.quantile(tr_arr, 0.99)),
        "maxeig_obs": float(max_obs),
        "maxeig_boot_pval": float(p_max),
        "maxeig_mc_se": float(mc_se_max),
        "maxeig_boot_cv90": float(np.quantile(mx_arr, 0.90)),
        "maxeig_boot_cv95": float(np.quantile(mx_arr, 0.95)),
        "maxeig_boot_cv99": float(np.quantile(mx_arr, 0.99)),
    }


def evaluate_bootstrap_size_and_power(
    sample_sizes: List[int] = (25, 100, 500),
    n_mc: int = 200,
    n_boot: int = 299,
    seed: int = 20261113,
) -> List[Dict[str, Any]]:
    """Controlled DGP Monte Carlo validation of empirical size (rank=0) and power (rank=1)."""
    rng = np.random.default_rng(seed)
    results = []
    # Contemporaneous correlated innovations matching crypto cross-market correlation ~0.95
    cov = np.array([[0.0009, 0.00085], [0.00085, 0.0009]])
    L = np.linalg.cholesky(cov)

    for T in sample_sizes:
        for true_rank in (0, 1):
            rej_asymp_5 = 0
            rej_ra_5 = 0
            rej_boot_5 = 0
            for m in range(n_mc):
                burn = 50
                tot = T + burn
                eps = rng.standard_normal((tot, 2)) @ L.T
                Y = np.zeros((tot, 2))
                for t in range(1, tot):
                    if true_rank == 0:
                        Y[t] = Y[t - 1] + eps[t]
                    else:
                        # Cointegrated with beta=(1,-1) and alpha=(-0.35, 0.0)
                        ect = Y[t - 1, 0] - Y[t - 1, 1]
                        Y[t, 0] = Y[t - 1, 0] - 0.35 * ect + eps[t, 0]
                        Y[t, 1] = Y[t - 1, 1] + eps[t, 1]
                Y_samp = Y[burn:]
                res = coint_johansen(Y_samp, det_order=0, k_ar_diff=1)
                tr_orig = float(res.lr1[0])
                cv_95 = float(res.cvt[0, 1])
                T_eff = T - 2
                ra_factor = (T_eff - 4) / T_eff
                if tr_orig > cv_95:
                    rej_asymp_5 += 1
                if ra_factor * tr_orig > cv_95:
                    rej_ra_5 += 1
                bres = null_imposed_vecm_residual_bootstrap(
                    Y_samp, det_order=0, k_ar_diff=1, n_boot=n_boot, seed=seed + m + T * 1000 + true_rank * 100000
                )
                if bres["trace_boot_pval"] < 0.05:
                    rej_boot_5 += 1

            results.append(
                {
                    "T": int(T),
                    "true_rank": int(true_rank),
                    "metric": "empirical_size" if true_rank == 0 else "empirical_power",
                    "n_mc": int(n_mc),
                    "n_boot": int(n_boot),
                    "rej_rate_asymptotic_5pct": round(rej_asymp_5 / n_mc, 4),
                    "rej_rate_reinsel_ahn_5pct": round(rej_ra_5 / n_mc, 4),
                    "rej_rate_bootstrap_5pct": round(rej_boot_5 / n_mc, 4),
                }
            )
    return results
