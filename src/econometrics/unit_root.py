"""Unit-root and stationarity test suite (ADF, Phillips-Perron, KPSS, Zivot-Andrews)."""
from __future__ import annotations

from typing import Dict, Any
import numpy as np
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews
from arch.unitroot import PhillipsPerron


def run_unit_root_suite(series: np.ndarray, name: str, max_lags: int = 12) -> Dict[str, Any]:
    """Run ADF (c, ct), Phillips-Perron (c), KPSS (c, ct), and Zivot-Andrews (c)."""
    y = np.asarray(series, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    max_lag_eff = min(max_lags, max(1, int(np.floor(12.0 * (n / 100.0) ** 0.25))))

    adf_c = adfuller(y, maxlag=max_lag_eff, regression="c", autolag="AIC")
    adf_ct = adfuller(y, maxlag=max_lag_eff, regression="ct", autolag="AIC")
    pp_c = PhillipsPerron(y, trend="c")
    kpss_c = kpss(y, regression="c", nlags="auto")
    kpss_ct = kpss(y, regression="ct", nlags="auto")

    za_stat, za_p, za_cv, za_lag, za_idx = (np.nan, np.nan, {}, np.nan, np.nan)
    if n >= 40:
        try:
            za = zivot_andrews(y, trim=0.15, maxlag=min(8, max_lag_eff), regression="c", autolag="AIC")
            za_stat, za_p, za_cv, za_lag, za_idx = za
        except Exception:
            pass

    return {
        "series": name,
        "n_obs": int(n),
        "adf_c_stat": float(adf_c[0]),
        "adf_c_pval": float(adf_c[1]),
        "adf_c_lags": int(adf_c[2]),
        "adf_c_cv5": float(adf_c[4]["5%"]),
        "adf_ct_stat": float(adf_ct[0]),
        "adf_ct_pval": float(adf_ct[1]),
        "adf_ct_lags": int(adf_ct[2]),
        "pp_c_stat": float(pp_c.stat),
        "pp_c_pval": float(pp_c.pvalue),
        "pp_c_lags": int(pp_c.lags),
        "kpss_c_stat": float(kpss_c[0]),
        "kpss_c_pval": float(kpss_c[1]),
        "kpss_c_lags": int(kpss_c[2]),
        "kpss_c_cv5": float(kpss_c[3]["5%"]),
        "kpss_ct_stat": float(kpss_ct[0]),
        "kpss_ct_pval": float(kpss_ct[1]),
        "za_c_stat": float(za_stat) if np.isfinite(za_stat) else None,
        "za_c_pval": float(za_p) if np.isfinite(za_p) else None,
        "za_break_idx": int(za_idx) if np.isfinite(za_idx) else None,
    }
