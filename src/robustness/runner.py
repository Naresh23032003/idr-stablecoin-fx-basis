"""Robustness and falsification test suite (Parts H11 & H12)."""
from __future__ import annotations

from typing import Dict, Any, List
import numpy as np
import pandas as pd

from src.econometrics.cointegration import engle_granger_test, fixed_vector_basis_test, johansen_with_finite_sample
from src.econometrics.ecm import estimate_bivariate_vecm, estimate_return_passthrough
from src.econometrics.structural_breaks import chow_break_test


def run_synchronization_sensitivity(btc_df: pd.DataFrame) -> pd.DataFrame:
    """Test sensitivity across -15m (ex-ante), 0m (primary), +5m, +15m, 23:59 UTC close, and t+1 JISDOR lead."""
    specs = [
        ("Primary_0m_JISDOR", "indodax_close", "binance_close", "usdtidr_close", "jisdor_idr_usd"),
        ("ExAnte_Minus15m_JISDOR", "indodax_close_m15", "binance_close_m15", "usdtidr_close_m15", "jisdor_idr_usd"),
        ("Post_Plus5m_JISDOR", "indodax_close_p5", "binance_close_p5", "usdtidr_close_p5", "jisdor_idr_usd"),
        ("Post_Plus15m_JISDOR", "indodax_close_p15", "binance_close_p15", "usdtidr_close_p15", "jisdor_idr_usd"),
        ("NextDay_JISDOR_Lead", "indodax_close", "binance_close", "usdtidr_close", "jisdor_next_day_idr_usd"),
        ("Mismatched_2359UTC_Close", "indodax_1d_close", "binance_1d_close", "usdtidr_1d_close", "jisdor_idr_usd"),
        ("SpotFX_Yahoo_0m", "indodax_close", "binance_close", "usdtidr_close", "spot_idr_usd"),
        ("ECBFX_Frankfurter_0m", "indodax_close", "binance_close", "usdtidr_close", "ecb_idr_usd"),
    ]
    rows: List[Dict[str, Any]] = []
    for label, pi, pb, pu, ps in specs:
        if any(c not in btc_df.columns for c in [pi, pb, pu, ps]):
            continue
        sub = btc_df[[pi, pb, pu, ps]].dropna()
        if len(sub) < 30:
            continue
        ln_i = np.log(sub[pi].values)
        ln_b = np.log(sub[pb].values)
        ln_u = np.log(sub[pu].values)
        ln_s = np.log(sub[ps].values)

        b_tot = 10_000.0 * (ln_i - ln_b - ln_s)
        b_cry = 10_000.0 * (ln_i - ln_b - ln_u)
        b_sf = 10_000.0 * (ln_u - ln_s)

        eg = engle_granger_test(ln_i, ln_b + ln_s)
        fv = fixed_vector_basis_test(ln_i, ln_b + ln_s)
        joh = johansen_with_finite_sample(np.column_stack([ln_i, ln_b + ln_s]), det_order=0, k_ar_diff=1)
        rows.append(
            {
                "specification": label,
                "n_obs": int(len(sub)),
                "mean_b_total_bps": round(float(np.mean(b_tot)), 2),
                "sd_b_total_bps": round(float(np.std(b_tot, ddof=1)), 2),
                "mean_b_crypto_bps": round(float(np.mean(b_cry)), 2),
                "sd_b_crypto_bps": round(float(np.std(b_cry, ddof=1)), 2),
                "mean_b_sf_bps": round(float(np.mean(b_sf)), 2),
                "sd_b_sf_bps": round(float(np.std(b_sf, ddof=1)), 2),
                "eg_t_stat": round(eg["eg_t_stat"], 3),
                "eg_pval": round(eg["eg_pvalue_mackinnon"], 5),
                "fixed_adf_stat": round(fv["fixed_adf_stat"], 3),
                "fixed_adf_pval": round(fv["fixed_adf_pval"], 5),
                "joh_trace_ra": round(joh["trace_r0_ra"], 2),
                "joh_reject_5pct": joh["reject_r0_5pct_ra"],
            }
        )
    return pd.DataFrame(rows)


def run_falsification_tests(btc_df: pd.DataFrame, xrp_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Falsification checks:
    1. Unadjusted log P_IDR vs log P_USDT (omitted FX benchmark).
    2. Non-USD placebo FX benchmark (EUR/USD instead of USD/IDR).
    3. Cross-asset mismatch placebo (BTC/IDR vs XRP/USDT * JISDOR).
    4. Deliberate 30-day timestamp mismatch (spread dispersion explodes vs synced 80.8 bps).
    5. Placebo structural break date in calm subsample (2023-06-15).
    """
    rows: List[Dict[str, Any]] = []
    sub = btc_df[["date", "indodax_close", "binance_close", "usdtidr_close", "jisdor_idr_usd", "eur_usd", "b_crypto_bps"]].dropna()
    ln_i = np.log(sub["indodax_close"].values)
    ln_b = np.log(sub["binance_close"].values)
    ln_s = np.log(sub["jisdor_idr_usd"].values)
    ln_eur = np.log(sub["eur_usd"].values)

    # Falsification 1: Unadjusted P_IDR vs P_USDT (omitted FX)
    eg_unadj = engle_granger_test(ln_i, ln_b)
    joh_unadj = johansen_with_finite_sample(np.column_stack([ln_i, ln_b]), det_order=0, k_ar_diff=1)
    rows.append({
        "test": "Omitted_FX_Unadjusted_BTC_IDR_vs_USDT",
        "expected_outcome": "Fail cointegration (spurious segmentation)",
        "n_obs": eg_unadj["n_obs"],
        "spread_sd_bps": round(float(np.std(10_000.0 * (ln_i - ln_b), ddof=1)), 2),
        "eg_t_stat": round(eg_unadj["eg_t_stat"], 3),
        "eg_pval": round(eg_unadj["eg_pvalue_mackinnon"], 5),
        "joh_trace_ra": round(joh_unadj["trace_r0_ra"], 2),
        "joh_cv95_inf": round(joh_unadj["trace_cv95_inf"], 2),
        "rejected_no_coint_5pct": joh_unadj["reject_r0_5pct_ra"],
    })

    # Falsification 2: Wrong FX benchmark (EUR/USD instead of USD/IDR)
    eg_eur = engle_granger_test(ln_i, ln_b + ln_eur)
    joh_eur = johansen_with_finite_sample(np.column_stack([ln_i, ln_b + ln_eur]), det_order=0, k_ar_diff=1)
    rows.append({
        "test": "Placebo_Wrong_FX_EURUSD",
        "expected_outcome": "Fail cointegration (still omits IDR trend)",
        "n_obs": eg_eur["n_obs"],
        "spread_sd_bps": round(float(np.std(10_000.0 * (ln_i - (ln_b + ln_eur)), ddof=1)), 2),
        "eg_t_stat": round(eg_eur["eg_t_stat"], 3),
        "eg_pval": round(eg_eur["eg_pvalue_mackinnon"], 5),
        "joh_trace_ra": round(joh_eur["trace_r0_ra"], 2),
        "joh_cv95_inf": round(joh_eur["trace_cv95_inf"], 2),
        "rejected_no_coint_5pct": joh_eur["reject_r0_5pct_ra"],
    })

    # Falsification 3: Cross-asset mismatch placebo (BTC/IDR vs XRP/USDT * JISDOR)
    if xrp_df is not None and not xrp_df.empty:
        xm = sub[["date", "indodax_close", "jisdor_idr_usd"]].merge(
            xrp_df[["date", "binance_close"]].rename(columns={"binance_close": "xrp_usdt"}),
            on="date",
            how="inner",
        ).dropna()
        ln_btc_i = np.log(xm["indodax_close"].values)
        ln_xrp_g = np.log(xm["xrp_usdt"].values) + np.log(xm["jisdor_idr_usd"].values)
        eg_ca = engle_granger_test(ln_btc_i, ln_xrp_g)
        joh_ca = johansen_with_finite_sample(np.column_stack([ln_btc_i, ln_xrp_g]), det_order=0, k_ar_diff=1)
        rows.append({
            "test": "Placebo_CrossAsset_BTCIDR_vs_XRP_JISDOR",
            "expected_outcome": "Fail cointegration (different underlying assets)",
            "n_obs": eg_ca["n_obs"],
            "spread_sd_bps": round(float(np.std(10_000.0 * (ln_btc_i - ln_xrp_g), ddof=1)), 2),
            "eg_t_stat": round(eg_ca["eg_t_stat"], 3),
            "eg_pval": round(eg_ca["eg_pvalue_mackinnon"], 5),
            "joh_trace_ra": round(joh_ca["trace_r0_ra"], 2),
            "joh_cv95_inf": round(joh_ca["trace_cv95_inf"], 2),
            "rejected_no_coint_5pct": joh_ca["reject_r0_5pct_ra"],
        })

    # Falsification 4: Deliberate 30-day mismatched global price
    shift_k = 30
    eg_mis = engle_granger_test(ln_i[shift_k:], ln_b[:-shift_k] + ln_s[shift_k:])
    joh_mis = johansen_with_finite_sample(np.column_stack([ln_i[shift_k:], ln_b[:-shift_k] + ln_s[shift_k:]]), det_order=0, k_ar_diff=1)
    rows.append({
        "test": "Deliberate_30d_Time_Mismatch_BTC",
        "expected_outcome": "Spread SD explodes (>2,000 bps); I(1) lag retains cointegration",
        "n_obs": eg_mis["n_obs"],
        "spread_sd_bps": round(float(np.std(10_000.0 * (ln_i[shift_k:] - (ln_b[:-shift_k] + ln_s[shift_k:])), ddof=1)), 2),
        "eg_t_stat": round(eg_mis["eg_t_stat"], 3),
        "eg_pval": round(eg_mis["eg_pvalue_mackinnon"], 5),
        "joh_trace_ra": round(joh_mis["trace_r0_ra"], 2),
        "joh_cv95_inf": round(joh_mis["trace_cv95_inf"], 2),
        "rejected_no_coint_5pct": joh_mis["reject_r0_5pct_ra"],
    })

    # Falsification 5: Placebo break date in calm mid-2023 (2023-06-15)
    calm = sub[(sub["date"] >= "2023-01-01") & (sub["date"] <= "2023-12-31")].reset_index(drop=True)
    if len(calm) > 40:
        bidx = int((calm["date"] >= "2023-06-15").idxmax())
        ch = chow_break_test(calm["b_crypto_bps"].values, bidx)
        rows.append({
            "test": "Placebo_Break_2023_06_15_CalmSubsample",
            "expected_outcome": "No spurious Chow break (p > 0.05)",
            "n_obs": ch.get("n_obs", 0),
            "spread_sd_bps": round(float(calm["b_crypto_bps"].std(ddof=1)), 2),
            "eg_t_stat": round(ch.get("f_stat", float("nan")), 3),
            "eg_pval": round(ch.get("pvalue", float("nan")), 5),
            "joh_trace_ra": None,
            "joh_cv95_inf": None,
            "rejected_no_coint_5pct": bool(ch.get("pvalue", 1.0) < 0.05),
        })

    return pd.DataFrame(rows)


def run_lag_and_deterministic_sensitivity(btc_df: pd.DataFrame) -> pd.DataFrame:
    """Test Johansen & VECM stability across VAR lag orders k=2..6 and deterministic specs ('ci', 'co', 'lo')."""
    ln_i = np.log(btc_df["indodax_close"].values)
    ln_g = np.log(btc_df["binance_close"].values) + np.log(btc_df["jisdor_idr_usd"].values)
    Y = np.column_stack([ln_i, ln_g])
    rows = []
    for det_label, det_order in [("ci", 0), ("co", 0), ("lo", 1)]:
        for k_diff in (1, 2, 3, 4, 5):
            j = johansen_with_finite_sample(Y, det_order=det_order, k_ar_diff=k_diff, deterministic=det_label)
            vecm_det = "ci" if det_label == "ci" else ("co" if det_label == "co" else "lo")
            v = estimate_bivariate_vecm(ln_i, ln_g, k_ar_diff=k_diff, det_order=vecm_det, sampling_unit="days")
            rows.append({
                "deterministic_spec": det_label,
                "det_order": det_order,
                "k_ar_diff": k_diff,
                "var_lag_k": k_diff + 1,
                "T_eff": j["T_eff"],
                "trace_r0_ra": round(j["trace_r0_ra"], 2),
                "trace_cv95_inf": round(j["trace_cv95_inf"], 2),
                "reject_5pct": j["reject_r0_5pct_ra"],
                "alpha_local_hac": round(v["alpha_local_hac"], 4),
                "alpha_local_pval": round(v["alpha_local_hac_pval"], 5),
                "alpha_global_pval": round(v["alpha_global_hac_pval"], 5),
            })
    return pd.DataFrame(rows)
