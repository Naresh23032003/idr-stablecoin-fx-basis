"""Unit and simulation tests for econometrics, Johansen scaling, and bootstrap validity."""
from __future__ import annotations

import numpy as np
import pytest

from src.econometrics.unit_root import run_unit_root_suite
from src.econometrics.cointegration import engle_granger_test, fixed_vector_basis_test, johansen_with_finite_sample
from src.econometrics.bootstrap import (
    null_imposed_vecm_residual_bootstrap,
    sequential_vecm_block_wild_bootstrap,
    evaluate_bootstrap_size_and_power,
)
from src.econometrics.ecm import estimate_bivariate_vecm, compute_vecm_eigenmode_decomposition


def test_johansen_reinsel_ahn_and_cheung_lai_scaling():
    rng = np.random.default_rng(123)
    N = 100
    y1 = np.cumsum(rng.normal(0, 0.01, N))
    y2 = y1 + rng.normal(0, 0.005, N)
    Y = np.column_stack([y1, y2])

    res = johansen_with_finite_sample(Y, det_order=0, k_ar_diff=1)
    # n=2, k=2 => nk=4, T_eff = N - 2 = 98
    assert res["T_eff"] == 98
    assert np.isclose(res["ra_factor"], (98 - 4) / 98, atol=1e-9)
    assert np.isclose(res["cl_factor"], 98 / (98 - 4), atol=1e-9)
    assert res["trace_r0_ra"] < res["trace_r0_orig"]
    assert res["trace_cv95_cl"] > res["trace_cv95_inf"]
    # Equivalence: J_RA / CV_inf == J_orig / CV_CL
    assert np.isclose(res["trace_r0_ra"] / res["trace_cv95_inf"], res["trace_r0_orig"] / res["trace_cv95_cl"], atol=1e-9)


def test_engle_granger_vs_fixed_vector():
    rng = np.random.default_rng(99)
    N = 250
    x = np.cumsum(rng.normal(0, 0.02, N))
    y = 1.0 * x + rng.normal(0, 0.005, N)
    eg = engle_granger_test(y, x)
    fv = fixed_vector_basis_test(y, x)
    assert eg["eg_pvalue_mackinnon"] < 0.01
    assert fv["fixed_adf_pval"] < 0.01


def test_bootstrap_reproducibility_and_controlled_dgp():
    rng = np.random.default_rng(77)
    N = 80
    x = np.cumsum(rng.normal(0, 0.01, N))
    y = np.cumsum(rng.normal(0, 0.01, N))
    Y = np.column_stack([y, x])

    b1 = null_imposed_vecm_residual_bootstrap(Y, det_order=0, k_ar_diff=1, n_boot=199, seed=20261113)
    b2 = null_imposed_vecm_residual_bootstrap(Y, det_order=0, k_ar_diff=1, n_boot=199, seed=20261113)
    assert b1["trace_boot_pval"] == b2["trace_boot_pval"]
    assert b1["n_failed"] == 0
    assert b1["method"] == "null_imposed_restricted_vecm_block_wild_bootstrap"

    # Quick DGP size/power sanity check (small n_mc for fast pytest)
    sp = evaluate_bootstrap_size_and_power(sample_sizes=[100], n_mc=30, n_boot=99, seed=20261113)
    size_row = [r for r in sp if r["true_rank"] == 0][0]
    power_row = [r for r in sp if r["true_rank"] == 1][0]
    # Under H0 size should be near 0.05 (allow Monte Carlo slack with n_mc=30)
    assert size_row["rej_rate_bootstrap_5pct"] <= 0.20
    # Under H1 (rank=1, alpha=-0.35, T=100, GARCH(1,1)+AR(1)), power should be substantial
    assert power_row["rej_rate_bootstrap_5pct"] >= 0.60


def test_unit_root_suite_stationary_vs_random_walk():
    rng = np.random.default_rng(20261113)
    stat_series = rng.normal(0, 1, 300)
    rw_series = np.cumsum(rng.normal(0, 1, 300))
    u_s = run_unit_root_suite(stat_series, "stationary")
    u_r = run_unit_root_suite(rw_series, "rw")
    assert u_s["adf_c_pval"] < 0.01
    assert u_r["adf_c_pval"] > 0.10
    assert u_r["kpss_c_pval"] < 0.05


def test_sequential_bootstrap_and_deterministic_specs():
    rng = np.random.default_rng(20261113)
    N = 150
    x = np.cumsum(rng.normal(0, 0.01, N))
    y = x + 0.05 + rng.normal(0, 0.005, N)
    Y = np.column_stack([y, x])

    seq = sequential_vecm_block_wild_bootstrap(Y, det_order=0, k_ar_diff=1, n_boot=99, seed=11)
    assert len(seq) == 2
    assert seq[0]["null_rank"] == 0 and seq[0]["trace_boot_pval"] <= 0.05
    assert seq[1]["null_rank"] == 1 and seq[1]["trace_boot_pval"] > 0.05

    j_co = johansen_with_finite_sample(Y, det_order=0, k_ar_diff=1, deterministic="co")
    j_ci = johansen_with_finite_sample(Y, det_order=0, k_ar_diff=1, deterministic="ci")
    assert j_co["deterministic_spec"] == "co"
    assert j_ci["deterministic_spec"] == "ci"
    assert j_co["reject_r0_5pct_ra"] and j_ci["reject_r0_5pct_ra"]

    v_co = estimate_bivariate_vecm(y, x, k_ar_diff=1, det_order="co")
    v_ci = estimate_bivariate_vecm(y, x, k_ar_diff=1, det_order="ci")
    assert v_co["deterministic_spec"] == "co" and v_ci["deterministic_spec"] == "ci"
    assert v_co["half_life_native_units"] > 0 and v_co["half_life_irf_local_units"] >= 0


def test_eigenmode_decomposition_spectral_identity():
    from statsmodels.tsa.vector_ar.vecm import VECM
    rng = np.random.default_rng(20261113)
    N = 200
    x = np.cumsum(rng.normal(0, 0.01, N))
    y = x + 0.02 + rng.normal(0, 0.005, N)
    Y = np.column_stack([y, x])
    res = VECM(Y, k_ar_diff=2, coint_rank=1, deterministic="co").fit()
    ed = compute_vecm_eigenmode_decomposition(res, res.beta[:, 0], check_h=25)
    assert np.isclose(ed["sum_shares_local"], 1.0, atol=1e-10)
    assert np.isclose(ed["sum_shares_gen"], 1.0, atol=1e-10)
    assert ed["max_irf_reconstruction_err"] < 1e-11


def test_regime_stability_wald_independent_reconstruction():
    """Independently reconstruct the 6-regime pooled HAC interaction Wald test from processed data."""
    import json
    from pathlib import Path
    import pandas as pd
    import statsmodels.api as sm
    from statsmodels.tsa.vector_ar.vecm import VECM
    from src.econometrics.structural_breaks import (
        DEFAULT_INSTITUTIONAL_REGIMES,
        estimate_regime_stability_and_wald,
    )

    root = Path(__file__).resolve().parents[1]
    btc = pd.read_csv(root / "data/processed/btc_jisdor_sync_primary.csv")
    stab_df, wald_fn = estimate_regime_stability_and_wald(btc, k_ar_diff=1, det_order="co", hac_lags=5)
    assert len(stab_df) == 6

    # Independent reconstruction
    Y = np.column_stack([btc["ln_p_idr"].values, btc["ln_p_global_fx"].values])
    v = VECM(Y, k_ar_diff=1, coint_rank=1, deterministic="co").fit()
    ect = Y @ v.beta[:, 0]
    dY = np.diff(Y, axis=0)
    dates = btc["date"].values[2:]
    X_dict = {
        "const": np.ones(len(dates)),
        "ect_lag": ect[1:-1],
        "dl_lag1": dY[:-1, 0],
        "dg_lag1": dY[:-1, 1],
    }
    inter = []
    for i, (_, d0, d1) in enumerate(DEFAULT_INSTITUTIONAL_REGIMES[1:], start=1):
        m = ((dates >= d0) & (dates <= d1)).astype(float)
        X_dict[f"d_{i}"] = m
        X_dict[f"ect_x_{i}"] = ect[1:-1] * m
        inter.append(f"ect_x_{i}")
    X_df = pd.DataFrame(X_dict)
    ols = sm.OLS(dY[1:, 0], X_df).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    R = np.zeros((len(inter), len(ols.params)))
    for i, nm in enumerate(inter):
        R[i, ols.params.index.get_loc(nm)] = 1.0
    wt = ols.wald_test(R, scalar=True)

    assert wald_fn["df"] == 5
    assert np.isclose(wald_fn["wald_chi2"], float(wt.statistic), atol=1e-3)
    assert np.isclose(wald_fn["pvalue"], float(wt.pvalue), atol=1e-4)
    saved_path = root / "results/diagnostics/structural_stability_wald.json"
    if saved_path.exists():
        saved = json.loads(saved_path.read_text())
        assert np.isclose(saved["wald_chi2"], wald_fn["wald_chi2"], atol=1e-3)
        assert np.isclose(saved["pvalue"], wald_fn["pvalue"], atol=1e-4)
