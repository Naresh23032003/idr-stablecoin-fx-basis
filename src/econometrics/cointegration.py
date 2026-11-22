"""Cointegration suite: Engle-Granger, fixed-(1,-1) basis tests, and Johansen with Reinsel-Ahn / Cheung-Lai."""
from __future__ import annotations

from typing import Dict, Any
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint, kpss
from statsmodels.tsa.vector_ar.vecm import coint_johansen


def engle_granger_test(y: np.ndarray, x: np.ndarray, trend: str = "c", maxlag: int | None = None) -> Dict[str, Any]:
    """Engle-Granger two-step residual cointegration test with OLS slope and HAC SE."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]

    X = sm.add_constant(x)
    ols = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    t_stat, p_val, crit = coint(y, x, trend=trend, maxlag=maxlag, autolag="AIC")
    return {
        "n_obs": int(len(y)),
        "eg_alpha_hat": float(ols.params[0]),
        "eg_beta_hat": float(ols.params[1]),
        "eg_beta_hac_se": float(ols.bse[1]),
        "eg_t_stat": float(t_stat),
        "eg_pvalue_mackinnon": float(p_val),
        "eg_cv_1pct": float(crit[0]),
        "eg_cv_5pct": float(crit[1]),
        "eg_cv_10pct": float(crit[2]),
    }


def fixed_vector_basis_test(y: np.ndarray, x: np.ndarray, maxlag: int = 12) -> Dict[str, Any]:
    """Test stationarity of pre-imposed (1, -1) spread y - x (distinct from estimated-beta EG)."""
    spread = np.asarray(y, dtype=float) - np.asarray(x, dtype=float)
    spread = spread[np.isfinite(spread)]
    adf = adfuller(spread, maxlag=min(maxlag, max(1, len(spread) // 4)), regression="c", autolag="AIC")
    kp = kpss(spread, regression="c", nlags="auto")
    return {
        "n_obs": int(len(spread)),
        "fixed_adf_stat": float(adf[0]),
        "fixed_adf_pval": float(adf[1]),
        "fixed_adf_lags": int(adf[2]),
        "fixed_kpss_stat": float(kp[0]),
        "fixed_kpss_pval": float(kp[1]),
    }


def johansen_with_finite_sample(
    Y: np.ndarray,
    det_order: int = 0,
    k_ar_diff: int = 1,
) -> Dict[str, Any]:
    """Johansen trace & max-eig with Reinsel-Ahn (1992) and Cheung-Lai (1993) corrections.

    Args:
        Y: Array of shape (N, n) in levels.
        det_order: 0 = unrestricted constant in VECM (restricted trend = none).
        k_ar_diff: Number of lagged differences in VECM (so VAR level order k = k_ar_diff + 1).
    """
    Y = np.asarray(Y, dtype=float)
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    N, n = Y.shape
    k = k_ar_diff + 1  # VAR order in levels
    T_eff = N - k      # Effective observations in VECM regression

    res = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
    j_trace_orig = float(res.lr1[0])
    j_max_orig = float(res.lr2[0])
    cv_trace_inf = [float(x) for x in res.cvt[0]]  # [90%, 95%, 99%]
    cv_max_inf = [float(x) for x in res.cvm[0]]

    # Exact Reinsel-Ahn (1992) & Cheung-Lai (1993) scaling factors
    ra_factor = (T_eff - n * k) / T_eff
    cl_factor = T_eff / (T_eff - n * k)

    j_trace_ra = ra_factor * j_trace_orig
    j_max_ra = ra_factor * j_max_orig
    cv_trace_cl = [cl_factor * c for c in cv_trace_inf]
    cv_max_cl = [cl_factor * c for c in cv_max_inf]

    # Normalized cointegrating vector (first column normalized on variable 0)
    beta_raw = res.evec[:, 0]
    beta_norm = beta_raw / beta_raw[0] if abs(beta_raw[0]) > 1e-12 else beta_raw

    return {
        "n_levels": int(N),
        "n_vars": int(n),
        "var_lag_k": int(k),
        "k_ar_diff": int(k_ar_diff),
        "T_eff": int(T_eff),
        "det_order": int(det_order),
        "ra_factor": float(ra_factor),
        "cl_factor": float(cl_factor),
        "trace_r0_orig": j_trace_orig,
        "trace_r0_ra": float(j_trace_ra),
        "trace_cv90_inf": cv_trace_inf[0],
        "trace_cv95_inf": cv_trace_inf[1],
        "trace_cv99_inf": cv_trace_inf[2],
        "trace_cv95_cl": float(cv_trace_cl[1]),
        "maxeig_r0_orig": j_max_orig,
        "maxeig_r0_ra": float(j_max_ra),
        "maxeig_cv90_inf": cv_max_inf[0],
        "maxeig_cv95_inf": cv_max_inf[1],
        "maxeig_cv99_inf": cv_max_inf[2],
        "maxeig_cv95_cl": float(cv_max_cl[1]),
        "trace_r1_orig": float(res.lr1[1]) if n >= 2 else None,
        "trace_r1_ra": float(ra_factor * res.lr1[1]) if n >= 2 else None,
        "trace_r1_cv95_inf": float(res.cvt[1, 1]) if n >= 2 else None,
        "beta_1_norm": float(-beta_norm[1]) if n >= 2 else None,
        "reject_r0_5pct_ra": bool(j_trace_ra > cv_trace_inf[1]),
        "reject_r0_10pct_ra": bool(j_trace_ra > cv_trace_inf[0]),
    }
