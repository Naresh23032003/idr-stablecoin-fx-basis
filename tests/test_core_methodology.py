"""Unit and integration tests for units, timestamps, basis identity, and fee arithmetic."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.variables.basis import compute_basis_decomposition, verify_units_and_bounds, verify_variance_identity
from src.fees.fee_schedule import HISTORICAL_REGIMES, compute_regime_costs, lookup_costs_for_dates
from src.processing.jisdor_calendar import build_jisdor_schedule_calendar
from src.synchronization.aligner import _asof_window_match


ROOT = Path(__file__).resolve().parents[1]


def test_unit_inversion_rejected():
    p_idr = pd.Series([1_500_000_000.0, 1_510_000_000.0])
    p_usdt = pd.Series([82_000.0, 82_500.0])
    # Inverted USDT/IDR (USD per IDR ~ 0.000055 instead of ~18,200)
    u_inv = pd.Series([1.0 / 18200.0, 1.0 / 18200.0])
    s_fx = pd.Series([18_150.0, 18_180.0])
    with pytest.raises(ValueError, match="inversion"):
        verify_units_and_bounds(p_idr, p_usdt, u_inv, s_fx, asset="BTC")


def test_non_positive_price_rejected():
    p_idr = pd.Series([1_500_000_000.0, 0.0])
    p_usdt = pd.Series([82_000.0, 82_500.0])
    u_idr = pd.Series([18_200.0, 18_210.0])
    s_fx = pd.Series([18_150.0, 18_180.0])
    with pytest.raises(ValueError, match="Non-positive"):
        verify_units_and_bounds(p_idr, p_usdt, u_idr, s_fx, asset="BTC")


def test_basis_identity_and_variance_identity():
    rng = np.random.default_rng(42)
    n = 100
    p_usdt = 80_000.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    s_fx = 16_000.0 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    u_idr = s_fx * np.exp(rng.normal(0.003, 0.001, n))
    p_idr = p_usdt * u_idr * np.exp(rng.normal(-0.001, 0.003, n))
    df = pd.DataFrame({
        "indodax_close": p_idr,
        "binance_close": p_usdt,
        "indodax_usdt_idr": u_idr,
        "jisdor_idr_usd": s_fx,
        "cb_usdtusd_close": np.full(n, 0.9995),
    })
    res = compute_basis_decomposition(
        df,
        p_idr_col="indodax_close",
        p_usdt_col="binance_close",
        u_idr_col="indodax_usdt_idr",
        s_fx_col="jisdor_idr_usd",
        usdt_usd_col="cb_usdtusd_close",
    )
    diff = np.abs(res["b_total_bps"] - (res["b_crypto_bps"] + res["b_stablecoin_fx_bps"]))
    assert float(diff.max()) < 1e-9
    v = verify_variance_identity(res["b_total_bps"], res["b_crypto_bps"], res["b_stablecoin_fx_bps"])
    assert v["variance_identity_abs_diff"] < 1e-6


def test_jisdor_historical_schedule_transitions():
    cal = build_jisdor_schedule_calendar(ROOT / "config" / "sampling.yaml", "2021-04-01", "2026-04-05")
    r_apr2 = cal.loc[cal["date"] == "2021-04-02"].iloc[0]
    r_apr5 = cal.loc[cal["date"] == "2021-04-05"].iloc[0]
    r_2025 = cal.loc[cal["date"] == "2025-08-01"].iloc[0]
    r_2026_0331 = cal.loc[cal["date"] == "2026-03-31"].iloc[0]
    r_2026_0401 = cal.loc[cal["date"] == "2026-04-01"].iloc[0]

    assert r_apr2["pub_time_utc"] == "03:00:00"
    assert r_apr5["pub_time_utc"] == "08:15:00"
    assert r_2025["pub_time_utc"] == "09:15:00"
    assert r_2026_0331["pub_time_utc"] == "09:15:00"
    assert r_2026_0401["pub_time_utc"] == "08:15:00"


def test_asof_window_matching_and_tolerance():
    targets = pd.DataFrame({"pub_ts_utc": pd.to_datetime(["2026-10-12T08:15:00Z", "2026-10-13T08:15:00Z"], utc=True)})
    market = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(["2026-10-12T08:15:00Z", "2026-10-12T08:20:00Z", "2026-10-13T08:25:00Z"], utc=True),
        "close": [100.0, 101.0, 102.0],
        "volume": [1.0, 1.0, 1.0],
    })
    m = _asof_window_match(targets, market, "pub_ts_utc", "test", offset_minutes=0, tolerance_minutes=5)
    assert m.loc[0, "test_close"] == 100.0
    assert m.loc[0, "test_lag_sec"] == 0.0
    # 08:25 is 10m after 08:15 -> exceeds 5m tolerance -> NaN
    assert pd.isna(m.loc[1, "test_close"])


def test_fee_arithmetic_oct_2026_matches_published_indodax_pro():
    r6 = [r for r in HISTORICAL_REGIMES if r.regime_id == "R6_CFX_CUT_OCT2026"][0]
    c = compute_regime_costs(r6)
    # Indodax published Oct 2026 Pro IDR schedule: Buy 10.555/20.555 bps; Sell 31.555/41.555 bps
    assert np.isclose(c["buy_idr_maker_bps"], 10.555, atol=1e-6)
    assert np.isclose(c["buy_idr_taker_bps"], 20.555, atol=1e-6)
    assert np.isclose(c["sell_idr_maker_bps"], 31.555, atol=1e-6)
    assert np.isclose(c["sell_idr_taker_bps"], 41.555, atol=1e-6)
    assert np.isclose(c["route_a_domestic_2leg_maker_bps"], 42.110, atol=1e-6)
    assert np.isclose(c["route_a_domestic_2leg_taker_bps"], 62.110, atol=1e-6)
    assert np.isclose(c["route_b_cross_3leg_taker_bps"], 72.110, atol=1e-6)


def test_fee_regime_date_lookup_no_gaps():
    dates = pd.Series(["2021-06-01", "2022-05-01", "2023-09-01", "2024-11-01", "2025-08-01", "2026-03-01", "2026-10-15"])
    res = lookup_costs_for_dates(dates)
    assert len(res) == len(dates)
    assert list(res["fee_regime_id"]) == [
        "R1_PRE_TAX_2021",
        "R2A_PMK68_0_30",
        "R2B_INDODAX_PRO_CUT",
        "R3_CFX_LAUNCH_PMK68",
        "R4_PMK50_2025",
        "R5_CFX_CUT_MAR2026",
        "R6_CFX_CUT_OCT2026",
    ]
