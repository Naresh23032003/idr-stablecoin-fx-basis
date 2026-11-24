"""Structural break, regime comparison, and regulatory event diagnostics."""
from __future__ import annotations

from typing import Dict, Any, List
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def evaluate_event_windows(
    df: pd.DataFrame,
    date_col: str,
    val_col: str,
    events: List[Dict[str, str]],
    window_days: int = 30,
) -> pd.DataFrame:
    """Compare pre/post distributions around regulatory & market events with Mann-Whitney U and Welch t-test."""
    d = df.copy()
    d["_dt"] = pd.to_datetime(d[date_col])
    rows = []
    for ev in events:
        ev_dt = pd.Timestamp(ev["date"])
        pre = d[(d["_dt"] >= ev_dt - pd.Timedelta(days=window_days)) & (d["_dt"] < ev_dt)][val_col].dropna()
        post = d[(d["_dt"] >= ev_dt) & (d["_dt"] < ev_dt + pd.Timedelta(days=window_days))][val_col].dropna()
        if len(pre) < 5 or len(post) < 5:
            rows.append(
                {
                    "event_date": ev["date"],
                    "label": ev["label"],
                    "n_pre": int(len(pre)),
                    "n_post": int(len(post)),
                    "status": "INSUFFICIENT_OBS",
                }
            )
            continue
        t_stat, t_p = stats.ttest_ind(post, pre, equal_var=False)
        u_stat, u_p = stats.mannwhitneyu(post, pre, alternative="two-sided")
        rows.append(
            {
                "event_date": ev["date"],
                "label": ev["label"],
                "window_days": int(window_days),
                "n_pre": int(len(pre)),
                "n_post": int(len(post)),
                "mean_pre_bps": float(pre.mean()),
                "mean_post_bps": float(post.mean()),
                "diff_mean_bps": float(post.mean() - pre.mean()),
                "sd_pre_bps": float(pre.std(ddof=1)),
                "sd_post_bps": float(post.std(ddof=1)),
                "median_pre_bps": float(pre.median()),
                "median_post_bps": float(post.median()),
                "welch_t_stat": float(t_stat),
                "welch_pval": float(t_p),
                "mw_u_pval": float(u_p),
                "status": "ESTIMATED",
            }
        )
    return pd.DataFrame(rows)


def chow_break_test(y: np.ndarray, break_idx: int) -> Dict[str, Any]:
    """Chow F-test for shift in mean/AR(1) persistence at break_idx."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    y_dep = y[1:]
    X = np.column_stack([np.ones(len(y_dep)), y[:-1]])
    b_idx = break_idx - 1
    if b_idx < 10 or (len(y_dep) - b_idx) < 10:
        return {"status": "INSUFFICIENT_OBS"}
    m_full = sm.OLS(y_dep, X).fit()
    m1 = sm.OLS(y_dep[:b_idx], X[:b_idx]).fit()
    m2 = sm.OLS(y_dep[b_idx:], X[b_idx:]).fit()
    ssr_p = m_full.ssr
    ssr_12 = m1.ssr + m2.ssr
    k = X.shape[1]
    n = len(y_dep)
    f_stat = ((ssr_p - ssr_12) / k) / (ssr_12 / (n - 2 * k))
    p_val = float(1.0 - stats.f.cdf(f_stat, k, n - 2 * k))
    return {"status": "OK", "f_stat": float(f_stat), "pvalue": p_val, "n_obs": int(n)}


DEFAULT_INSTITUTIONAL_REGIMES = [
    ("R1_PreTax_2021_2022", "2021-01-04", "2022-04-30"),
    ("R2A_PMK68_2022_2023", "2022-05-01", "2023-08-22"),
    ("R2B_ProCut_2023_2024", "2023-08-23", "2024-10-31"),
    ("R3_CFX_OJK_2024_2025", "2024-11-01", "2025-07-31"),
    ("R4_PMK50_2025_2026", "2025-08-01", "2026-02-28"),
    ("R5_R6_CFX_Cuts_2026", "2026-03-01", "2026-11-12"),
]


def estimate_regime_stability_and_wald(
    btc_df: pd.DataFrame,
    regimes: List[tuple[str, str, str]] | None = None,
    k_ar_diff: int = 1,
    det_order: str = "co",
    hac_lags: int = 5,
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Estimate subsample cointegration/VECM across institutional regimes and run a pooled HAC Wald test.

    Pooled HAC interaction Wald test specification:
      Conditional on the full-sample VECM cointegrating error z_{t-1} = beta_hat' Y_{t-1}
      (estimated on Y_t = [ln P_IDR, ln(P_USDT * S_JISDOR)]' with k_ar_diff=1, deterministic='co'),
      we estimate the local return equation:
          d(ln P_IDR)_t = c_0 + alpha_0 * z_{t-1} + gamma_1 * d(ln P_IDR)_{t-1} + gamma_2 * d(ln P_global)_{t-1}
                          + sum_{r=2}^{R} [delta_r * I(t in r) + theta_r * (z_{t-1} * I(t in r))] + u_t
      using Newey-West HAC covariance (maxlags = hac_lags) and test the joint restriction:
          H0: theta_2 = theta_3 = ... = theta_R = 0   (df = R - 1 = 5 for R = 6 regimes).

    Scope limitation: This tests equality of the local error-correction coefficient alpha_local
    across regimes conditional on the full-sample cointegrating vector beta_hat. It does NOT
    test comprehensive structural stability of the full VECM (beta, Gamma_j, mu_0, Sigma_u).
    """
    from statsmodels.tsa.vector_ar.vecm import VECM
    from src.econometrics.cointegration import johansen_with_finite_sample
    from src.econometrics.ecm import estimate_bivariate_vecm

    reg_list = regimes if regimes is not None else DEFAULT_INSTITUTIONAL_REGIMES
    stab_rows: List[Dict[str, Any]] = []
    for rname, d0, d1 in reg_list:
        sub = btc_df[(btc_df["date"] >= d0) & (btc_df["date"] <= d1)]
        Y_fx = np.column_stack([sub["ln_p_idr"].values, sub["ln_p_global_fx"].values])
        j = johansen_with_finite_sample(Y_fx, det_order=0, k_ar_diff=k_ar_diff)
        v = estimate_bivariate_vecm(
            sub["ln_p_idr"].values,
            sub["ln_p_global_fx"].values,
            k_ar_diff=k_ar_diff,
            det_order=det_order,
            hac_lags=hac_lags,
        )
        stab_rows.append(
            {
                "regime": rname,
                "start_date": d0,
                "end_date": d1,
                "n_days": int(len(sub)),
                "mean_b_total": round(float(sub["b_total_bps"].mean()), 2),
                "mean_b_crypto": round(float(sub["b_crypto_bps"].mean()), 2),
                "mean_b_sfx": round(float(sub["b_stablecoin_fx_bps"].mean()), 2),
                "beta_norm": round(float(v["beta_normalized"]), 4),
                "joh_trace_ra": round(float(j["trace_r0_ra"]), 2),
                "reject_r0_5pct": bool(j["reject_r0_5pct_ra"]),
                "alpha_local_hac": round(float(v["alpha_local_hac"]), 3),
                "se_local": round(float(v["alpha_local_hac_se"]), 3),
                "ci95_low": round(float(v["alpha_local_ci95_low"]), 3),
                "ci95_high": round(float(v["alpha_local_ci95_high"]), 3),
                "p_local": round(float(v["alpha_local_hac_pval"]), 4),
                "alpha_global_hac": round(float(v["alpha_global_hac"]), 3),
                "p_global": round(float(v["alpha_global_hac_pval"]), 4),
            }
        )

    Y_full = np.column_stack([btc_df["ln_p_idr"].values, btc_df["ln_p_global_fx"].values])
    v_full = VECM(Y_full, k_ar_diff=k_ar_diff, coint_rank=1, deterministic=det_order).fit()
    ect = Y_full @ v_full.beta[:, 0]
    dY = np.diff(Y_full, axis=0)
    p = k_ar_diff
    df_w = pd.DataFrame(
        {
            "date": btc_df["date"].values[p + 1 :],
            "dl": dY[p:, 0],
            "ect_lag": ect[p:-1],
        }
    )
    X_cols: Dict[str, np.ndarray] = {
        "const": np.ones(len(df_w)),
        "ect_lag": df_w["ect_lag"].values,
    }
    for j_lag in range(1, p + 1):
        X_cols[f"dl_lag{j_lag}"] = dY[p - j_lag : len(dY) - j_lag, 0]
        X_cols[f"dg_lag{j_lag}"] = dY[p - j_lag : len(dY) - j_lag, 1]

    inter_names: List[str] = []
    for idx_r, (_, d0, d1) in enumerate(reg_list[1:], start=1):
        mask_r = ((df_w["date"] >= d0) & (df_w["date"] <= d1)).astype(float).values
        X_cols[f"d_{idx_r}"] = mask_r
        X_cols[f"ect_x_{idx_r}"] = df_w["ect_lag"].values * mask_r
        inter_names.append(f"ect_x_{idx_r}")

    X_w = pd.DataFrame(X_cols)
    m_w = sm.OLS(df_w["dl"].values, X_w).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    R = np.zeros((len(inter_names), len(m_w.params)), dtype=float)
    for i, nm in enumerate(inter_names):
        R[i, m_w.params.index.get_loc(nm)] = 1.0
    wt = m_w.wald_test(R, scalar=True)
    wald_info = {
        "test": "Pooled_HAC_Wald_Equality_of_alpha_local_across_6_regimes",
        "scope_note": "Tests equality of local adjustment coefficient alpha_local across 6 regimes conditional on full-sample beta_hat; does not test full-VECM stability.",
        "T_eff": int(len(df_w)),
        "k_ar_diff": int(k_ar_diff),
        "deterministic_spec": det_order,
        "cov_type": "HAC",
        "hac_maxlags": int(hac_lags),
        "n_regimes": int(len(reg_list)),
        "df": int(R.shape[0]),
        "wald_chi2": round(float(wt.statistic), 3),
        "pvalue": round(float(wt.pvalue), 5),
        "reject_stability_5pct": bool(wt.pvalue < 0.05),
    }
    return pd.DataFrame(stab_rows), wald_info
