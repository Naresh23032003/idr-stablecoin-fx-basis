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

    ms_dir = ROOT / "manuscript"
    fig_dir = ms_dir / "figures" if (ms_dir / "figures").exists() else ms_dir
    tab_dir = ms_dir / "tables" if (ms_dir / "tables").exists() else ms_dir
    assert len(list(fig_dir.glob("fig*.pdf"))) == 8
    assert len(list(tab_dir.glob("tab_*.tex"))) == 8

    pdf_path = ROOT / "manuscript" / "main.pdf"
    if pdf_path.exists():
        assert pdf_path.stat().st_size > 50_000


def test_processed_reproduction_mode_without_raw_dir(tmp_path):
    """Integration test: processed-data reproduction validates inputs without data/raw/ and fails early on missing files."""
    import shutil
    import pytest
    from src.pipeline import validate_processed_inputs, validate_raw_inputs
    from src.manuscript.latex_tables import generate_all_latex_tables

    # Build a clean workspace copy with NO data/raw/
    for rel in [
        "data/processed",
        "data/source_coverage_matrix.csv",
        "results/tables",
        "results/models",
    ]:
        src_p = ROOT / rel
        dst_p = tmp_path / rel
        if src_p.is_dir():
            shutil.copytree(src_p, dst_p)
        else:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_p, dst_p)

    assert not (tmp_path / "data" / "raw").exists()
    # Full-raw validation must fail early when data/raw/ is absent
    with pytest.raises(FileNotFoundError, match="Raw data directory not found"):
        validate_raw_inputs(tmp_path)

    # Processed-data validation must succeed without data/raw/
    validate_processed_inputs(tmp_path)
    tabs = generate_all_latex_tables(tmp_path)
    assert len(tabs) == 8

    # Removing a required processed file must fail early (never silently skip)
    (tmp_path / "data/processed/btc_jisdor_sync_primary.csv").unlink()
    with pytest.raises(FileNotFoundError, match="btc_jisdor_sync_primary.csv"):
        validate_processed_inputs(tmp_path)
