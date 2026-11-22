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
