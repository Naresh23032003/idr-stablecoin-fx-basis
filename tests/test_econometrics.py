"""Unit and simulation tests for econometrics, Johansen scaling, and bootstrap validity."""
from __future__ import annotations

import numpy as np
import pytest

from src.econometrics.unit_root import run_unit_root_suite
from src.econometrics.cointegration import engle_granger_test, fixed_vector_basis_test, johansen_with_finite_sample
from src.econometrics.bootstrap import null_imposed_vecm_residual_bootstrap, evaluate_bootstrap_size_and_power


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
