"""Integration and output integrity checks across processed data, tables, figures, and manuscript artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_source_coverage_and_zero_synthetic_fill():
    cov_path = ROOT / "data" / "source_coverage_matrix.csv"
    assert cov_path.exists()
    cov = pd.read_csv(cov_path)
    assert len(cov) >= 30
    assert (cov["duplicate_count"] == 0).all()
    assert (cov["zero_invalid_price_count"] == 0).all()


def test_processed_primary_panel_integrity():
    btc_path = ROOT / "data" / "processed" / "btc_jisdor_sync_primary.csv"
    assert btc_path.exists()
    btc = pd.read_csv(btc_path)
    assert len(btc) >= 1400
    assert btc["date"].is_unique
    assert btc["jisdor_idr_usd"].notna().all()
    # Exact algebraic decomposition
    max_diff = np.max(np.abs(btc["b_total_bps"] - (btc["b_crypto_bps"] + btc["b_stablecoin_fx_bps"])))
    assert max_diff < 1e-8
    # Primary tolerance strictly <= 300 sec (5m bar matching)
    assert btc["indodax_lag_sec"].max() <= 300.0
    assert btc["binance_lag_sec"].max() <= 300.0


def test_generated_tables_figures_and_manuscript():
    tdir = ROOT / "results" / "tables"
    mdir = ROOT / "results" / "models"
    assert (tdir / "table1_descriptive_statistics.csv").exists()
    assert (tdir / "table3_cointegration_and_reconciliation.csv").exists()
    assert (tdir / "table4_bootstrap_rank_tests.csv").exists()
    assert (mdir / "variance_decomposition.json").exists()
    assert (mdir / "intraday_and_tar_results.json").exists()

    tar = json.loads((mdir / "intraday_and_tar_results.json").read_text())
    assert tar["tar_daily_b_crypto"]["sup_wald"] >= 0.0
    assert tar["tar_daily_b_total"]["sup_wald"] >= 0.0

    fig_dir = ROOT / "manuscript" / "figures"
    tab_dir = ROOT / "manuscript" / "tables"
    assert len(list(fig_dir.glob("*.pdf"))) == 8
    assert len(list(tab_dir.glob("*.tex"))) == 8

    pdf_path = ROOT / "manuscript" / "main.pdf"
    if pdf_path.exists():
        assert pdf_path.stat().st_size > 50_000
