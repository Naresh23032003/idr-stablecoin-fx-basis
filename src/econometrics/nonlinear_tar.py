"""Symmetric 3-regime Band-TAR and sup-Wald threshold linearity bootstrap."""
from __future__ import annotations

import math
from typing import Dict, Any
import numpy as np


def _fit_band_tar_fixed(b: np.ndarray, tau: float, p_lags: int = 1) -> Dict[str, Any]:
    """Fit symmetric 3-regime TAR:
    dB_t = c_in + rho_in * B_{t-1} + ...   if |B_{t-1}| <= tau
         = rho_out * (B_{t-1} - sign(B_{t-1}) * tau) + ...  if |B_{t-1}| > tau
    Returns SSR and regime parameters.
    """
    db = np.diff(b)
    b_lag = b[:-1]
    T = len(db) - p_lags
    dep = db[p_lags:]
    bl = b_lag[p_lags:]

    inside = np.abs(bl) <= tau
    outside_pos = bl > tau
    outside_neg = bl < -tau

    # Nesting linear AR(p+1) strictly inside symmetric Band-TAR:
    # Include indicators for inside, outside_pos, outside_neg so a + rho*bl is an exact subspace.
    z_in = np.where(inside, bl, 0.0)
    z_out = np.where(outside_pos, bl - tau, np.where(outside_neg, bl + tau, 0.0))

    cols = [
        inside.astype(float),
        z_in,
        outside_pos.astype(float),
        outside_neg.astype(float),
        z_out,
    ]
    for j in range(1, p_lags + 1):
        cols.append(db[p_lags - j : len(db) - j])
    X = np.column_stack(cols)
    coef, _, _, _ = np.linalg.lstsq(X, dep, rcond=None)
    resid = dep - X @ coef
    ssr = float(np.sum(resid**2))

    # Linear restricted model (single AR(p_lags+1)) strictly nested in X
    X_lin_cols = [np.ones(T), bl]
    for j in range(1, p_lags + 1):
        X_lin_cols.append(db[p_lags - j : len(db) - j])
    X_lin = np.column_stack(X_lin_cols)
    coef_lin, _, _, _ = np.linalg.lstsq(X_lin, dep, rcond=None)
    resid_lin = dep - X_lin @ coef_lin
    ssr_lin = float(np.sum(resid_lin**2))

    df_diff = max(1, X.shape[1] - X_lin.shape[1])
    df_denom = max(1, T - X.shape[1])
    wald = max(0.0, ((ssr_lin - ssr) / df_diff) / max(1e-18, ssr / df_denom))

    return {
        "ssr": ssr,
        "ssr_lin": ssr_lin,
        "wald": float(wald * df_diff),
        "n_eff": int(T),
        "n_in": int(inside.sum()),
        "n_out": int((~inside).sum()),
        "n_out_pos": int(outside_pos.sum()),
        "n_out_neg": int(outside_neg.sum()),
        "c_in": float(coef[0]),
        "rho_in": float(coef[1]),
        "c_out_pos": float(coef[2]),
        "c_out_neg": float(coef[3]),
        "rho_out": float(coef[4]),
        "resid_lin": resid_lin,
        "coef_lin": coef_lin,
    }


def estimate_band_tar(
    basis_bps: np.ndarray,
    p_lags: int = 1,
    trim: float = 0.15,
    grid_points: int = 60,
    n_boot: int = 499,
    seed: int = 20261113,
) -> Dict[str, Any]:
    """Grid search over symmetric threshold tau with residual bootstrap sup-Wald test."""
    b = np.asarray(basis_bps, dtype=float)
    b = b[np.isfinite(b)]
    if len(b) < 200:
        return {
            "status": "SKIPPED_UNDERPOWERED",
            "n_obs": int(len(b)),
            "reason": "Sample size below pre-registered minimum (200) for identifiable 3-regime TAR.",
        }

    abs_b = np.abs(b[p_lags:-1])
    q_low = np.quantile(abs_b, trim)
    q_high = np.quantile(abs_b, 1.0 - trim)
    taus = np.linspace(q_low, q_high, grid_points)

    best = None
    best_tau = None
    for tau in taus:
        fit = _fit_band_tar_fixed(b, float(tau), p_lags=p_lags)
        if fit["n_in"] < 20 or fit["n_out_pos"] < 10 or fit["n_out_neg"] < 10:
            continue
        if best is None or fit["wald"] > best["wald"]:
            best = fit
            best_tau = float(tau)

    if best is None:
        return {"status": "NO_VALID_THRESHOLD_GRID", "n_obs": int(len(b))}

    sup_wald_obs = best["wald"]
    # Null residual bootstrap under linear AR model
    rng = np.random.default_rng(seed)
    resid_lin = best["resid_lin"] - best["resid_lin"].mean()
    coef_lin = best["coef_lin"]
    db = np.diff(b)
    n_eff = best["n_eff"]

    exceed = 0
    for _ in range(n_boot):
        u_star = resid_lin[rng.integers(0, n_eff, size=n_eff)]
        b_star = np.empty(len(b), dtype=float)
        b_star[: p_lags + 1] = b[: p_lags + 1]
        for t in range(p_lags + 1, len(b)):
            db_lags = [b_star[t - j] - b_star[t - j - 1] for j in range(1, p_lags + 1)]
            val = coef_lin[0] + coef_lin[1] * b_star[t - 1]
            for j, dl in enumerate(db_lags):
                val += coef_lin[2 + j] * dl
            b_star[t] = b_star[t - 1] + val + u_star[t - (p_lags + 1)]

        max_w = 0.0
        for tau in taus[::2]:  # stride 2 inside bootstrap for speed while keeping grid span
            f_b = _fit_band_tar_fixed(b_star, float(tau), p_lags=p_lags)
            if f_b["n_in"] >= 15 and f_b["n_out_pos"] >= 8 and f_b["n_out_neg"] >= 8 and f_b["wald"] > max_w:
                max_w = f_b["wald"]
        if max_w >= sup_wald_obs:
            exceed += 1

    p_boot = (1.0 + exceed) / (n_boot + 1.0)
    rho_out = best["rho_out"]
    root_out = 1.0 + rho_out
    hl_out = float(-math.log(2.0) / math.log(abs(root_out))) if 0 < abs(root_out) < 1 else float("nan")

    return {
        "status": "ESTIMATED",
        "n_obs": int(len(b)),
        "n_eff": int(best["n_eff"]),
        "p_lags": int(p_lags),
        "tau_hat_bps": float(best_tau),
        "n_in_band": int(best["n_in"]),
        "n_out_band": int(best["n_out"]),
        "pct_in_band": round(100.0 * best["n_in"] / best["n_eff"], 2),
        "rho_in": float(best["rho_in"]),
        "rho_out": float(rho_out),
        "root_out": float(root_out),
        "half_life_out_bars": hl_out,
        "sup_wald": float(sup_wald_obs),
        "boot_replications": int(n_boot),
        "sup_wald_boot_pval": float(p_boot),
        "threshold_statistically_significant_5pct": bool(p_boot < 0.05),
    }
