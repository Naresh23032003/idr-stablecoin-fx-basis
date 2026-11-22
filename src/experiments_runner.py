"""Master experiment runner executing all registered econometric, cost, robustness, and validation studies."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import yaml

from src.econometrics.bootstrap import (
    evaluate_bootstrap_size_and_power,
    null_imposed_vecm_residual_bootstrap,
)
from src.econometrics.cointegration import (
    engle_granger_test,
    fixed_vector_basis_test,
    johansen_with_finite_sample,
)
from src.econometrics.ecm import estimate_bivariate_vecm, estimate_return_passthrough
from src.econometrics.nonlinear_tar import estimate_band_tar
from src.econometrics.structural_breaks import evaluate_event_windows
from src.econometrics.unit_root import run_unit_root_suite
from src.fees.fee_schedule import build_historical_fee_table, lookup_costs_for_dates
from src.fees.orderbook_economics import analyze_saved_orderbook_snapshots
from src.robustness.runner import (
    run_falsification_tests,
    run_lag_and_deterministic_sensitivity,
    run_synchronization_sensitivity,
)
from src.variables.basis import verify_variance_identity


def _basis_summary_row(df: pd.DataFrame, col: str, label: str, sample_name: str, band_maker: float, band_taker: float) -> Dict[str, Any]:
    s = df[col].dropna()
    q25, q50, q75 = np.quantile(s, [0.25, 0.50, 0.75])
    mean = float(s.mean())
    se = float(s.std(ddof=1) / np.sqrt(len(s)))
    return {
        "sample": sample_name,
        "series": label,
        "n_obs": int(len(s)),
        "mean_bps": round(mean, 2),
        "ci95_low_bps": round(mean - 1.96 * se, 2),
        "ci95_high_bps": round(mean + 1.96 * se, 2),
        "sd_bps": round(float(s.std(ddof=1)), 2),
        "var_bps2": round(float(s.var(ddof=1)), 2),
        "median_bps": round(float(q50), 2),
        "iqr_bps": round(float(q75 - q25), 2),
        "min_bps": round(float(s.min()), 2),
        "max_bps": round(float(s.max()), 2),
        "pct_positive": round(100.0 * float((s > 0).mean()), 2),
        "pct_within_maker_band": round(100.0 * float((s.abs() <= band_maker).mean()), 2),
        "pct_within_taker_band": round(100.0 * float((s.abs() <= band_taker).mean()), 2),
    }


def run_all_experiments(root: Path, econ_cfg_path: Path) -> Dict[str, Any]:
    cfg = yaml.safe_load(econ_cfg_path.read_text())["econometrics"]
    seed = int(cfg["seed"])
    proc_dir = root / "data" / "processed"
    tables_dir = root / "results" / "tables"
    models_dir = root / "results" / "models"
    tables_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    btc = pd.read_csv(proc_dir / "btc_jisdor_sync_primary.csv")
    eth = pd.read_csv(proc_dir / "eth_jisdor_sync_primary.csv")
    xrp = pd.read_csv(proc_dir / "xrp_jisdor_sync_primary.csv")
    btc_cal = pd.read_csv(proc_dir / "btc_calendar_days_sensitivity.csv")

    # 1. Historical Fee & Execution Cost Reconstruction
    fee_df = build_historical_fee_table()
    fee_df.to_csv(tables_dir / "historical_fee_reconstruction.csv", index=False)

    ob_df = analyze_saved_orderbook_snapshots(root / "data" / "raw", fx_idr_per_usd=float(btc["jisdor_idr_usd"].iloc[-1]))
    ob_df.to_csv(tables_dir / "orderbook_microstructure_snapshot.csv", index=False)

    # Route-specific execution costs across regimes + USD notional slippage
    r6 = fee_df.iloc[-1]
    btc_indo_ob = ob_df[(ob_df["exchange"] == "Indodax") & (ob_df["pair"] == "BTCIDR")].iloc[0] if not ob_df.empty else {}
    usdt_indo_ob = ob_df[(ob_df["exchange"] == "Indodax") & (ob_df["pair"] == "USDTIDR")].iloc[0] if not ob_df.empty else {}
    btcusdt_indo_ob = ob_df[(ob_df["exchange"] == "Indodax") & (ob_df["pair"] == "BTCUSDT")].iloc[0] if not ob_df.empty else {}
    btc_bin_ob = ob_df[(ob_df["exchange"] == "Binance") & (ob_df["pair"] == "BTCUSDT")].iloc[0] if not ob_df.empty else {}

    route_rows = []
    for sz_tag in ["1k", "10k", "50k"]:
        slip_btc_indo = float(btc_indo_ob.get(f"slip_sell_{sz_tag}_bps", 0.0) or 0.0)
        slip_usdt_indo = float(usdt_indo_ob.get(f"slip_buy_{sz_tag}_bps", 0.0) or 0.0)
        slip_btc_bin = float(btc_bin_ob.get(f"slip_buy_{sz_tag}_bps", 0.0) or 0.0)
        slip_btcusdt_indo = float(btcusdt_indo_ob.get(f"slip_buy_{sz_tag}_bps", 0.0) or 0.0)
        # Route A: Domestic 2-leg
        route_rows.append({
            "route": "Route A: Domestic 2-Leg (Sell BTC/IDR + Buy USDT/IDR on Indodax)",
            "trade_size_usd": sz_tag,
            "statutory_fee_maker_bps": float(r6["route_a_domestic_2leg_maker_bps"]),
            "statutory_fee_taker_bps": float(r6["route_a_domestic_2leg_taker_bps"]),
            "snapshot_half_spread_slip_bps": round(slip_btc_indo + slip_usdt_indo, 2),
            "all_in_taker_plus_slip_bps": round(float(r6["route_a_domestic_2leg_taker_bps"]) + slip_btc_indo + slip_usdt_indo, 2),
            "notes": "Excludes on-chain settlement; slippage from Nov 2026 live depth snapshot",
        })
        # Route B: Cross-exchange 3-leg
        route_rows.append({
            "route": "Route B: Cross-Exchange 3-Leg (Indodax BTC/IDR + USDT/IDR + Binance BTC/USDT)",
            "trade_size_usd": sz_tag,
            "statutory_fee_maker_bps": float(r6["route_b_cross_3leg_maker_bps"]),
            "statutory_fee_taker_bps": float(r6["route_b_cross_3leg_taker_bps"]),
            "snapshot_half_spread_slip_bps": round(slip_btc_indo + slip_usdt_indo + slip_btc_bin, 2),
            "all_in_taker_plus_slip_bps": round(float(r6["route_b_cross_3leg_taker_bps"]) + slip_btc_indo + slip_usdt_indo + slip_btc_bin, 2),
            "notes": "Assumes pre-funded inventory or excludes variable network transfer fee & latency risk",
        })
        # Route C: Same-exchange Indodax BTC/USDT
        route_rows.append({
            "route": "Route C: Same-Exchange Indodax (BTC/IDR + USDT/IDR + Indodax BTC/USDT)",
            "trade_size_usd": sz_tag,
            "statutory_fee_maker_bps": float(r6["route_c_indodax_usdt_maker_bps"]),
            "statutory_fee_taker_bps": float(r6["route_c_indodax_usdt_taker_bps"]),
            "snapshot_half_spread_slip_bps": round(slip_btc_indo + slip_usdt_indo + slip_btcusdt_indo, 2),
            "all_in_taker_plus_slip_bps": round(float(r6["route_c_indodax_usdt_taker_bps"]) + slip_btc_indo + slip_usdt_indo + slip_btcusdt_indo, 2),
            "notes": "No external transfer needed, but Indodax BTC/USDT exhibits wide spread/thin depth",
        })
    pd.DataFrame(route_rows).to_csv(tables_dir / "route_specific_execution_costs.csv", index=False)

    # Map historical time-varying taker & maker bands onto BTC daily rows
    btc_costs = lookup_costs_for_dates(btc["date"])
    btc["cost_2leg_maker_bps"] = btc_costs["route_a_domestic_2leg_maker_bps"].values
    btc["cost_2leg_taker_bps"] = btc_costs["route_a_domestic_2leg_taker_bps"].values
    btc["cost_3leg_taker_bps"] = btc_costs["route_b_cross_3leg_taker_bps"].values

    # 2. Descriptive Statistics & Exact Variance Decomposition (BTC, ETH, XRP, Calendar/Weekend)
    desc_rows = []
    for name, df in [("BTC Primary (JISDOR Bus. Days)", btc), ("ETH Primary (JISDOR Bus. Days)", eth), ("XRP Primary (JISDOR Bus. Days)", xrp)]:
        bm = float(btc["cost_2leg_maker_bps"].mean())
        bt = float(btc["cost_2leg_taker_bps"].mean())
        desc_rows.append(_basis_summary_row(df, "b_total_bps", "B_total (vs JISDOR)", name, bm, bt))
        desc_rows.append(_basis_summary_row(df, "b_crypto_bps", "B_crypto (vs Indodax USDT)", name, bm, bt))
        desc_rows.append(_basis_summary_row(df, "b_stablecoin_fx_bps", "B_stablecoin_FX (USDT/IDR - JISDOR)", name, bm, bt))
        if "usd_usdt_wedge_bps" in df.columns and df["usd_usdt_wedge_bps"].notna().sum() > 10:
            desc_rows.append(_basis_summary_row(df, "usd_usdt_wedge_bps", "W_USD_USDT (Coinbase)", name, bm, bt))

    wknd = btc_cal[btc_cal["is_weekend"]].copy()
    desc_rows.append(_basis_summary_row(btc_cal, "b_total_bps", "B_total (Carry-Forward JISDOR)", "BTC All Calendar Days (Sensitivity)", 42.11, 62.11))
    desc_rows.append(_basis_summary_row(wknd, "b_total_bps", "B_total (Weekend Carry-Forward)", "BTC Weekends Only (FX Closed)", 42.11, 62.11))
    desc_rows.append(_basis_summary_row(wknd, "b_crypto_bps", "B_crypto (Weekends Only)", "BTC Weekends Only (FX Closed)", 42.11, 62.11))
    pd.DataFrame(desc_rows).to_csv(tables_dir / "table1_descriptive_statistics.csv", index=False)

    var_decomp = {
        "BTC": verify_variance_identity(btc["b_total_bps"], btc["b_crypto_bps"], btc["b_stablecoin_fx_bps"]),
        "ETH": verify_variance_identity(eth["b_total_bps"], eth["b_crypto_bps"], eth["b_stablecoin_fx_bps"]),
        "XRP": verify_variance_identity(xrp["b_total_bps"], xrp["b_crypto_bps"], xrp["b_stablecoin_fx_bps"]),
        "BTC_pct_crypto_inside_dynamic_2leg_taker_band": round(100.0 * float((btc["b_crypto_bps"].abs() <= btc["cost_2leg_taker_bps"]).mean()), 2),
        "BTC_pct_crypto_inside_dynamic_2leg_maker_band": round(100.0 * float((btc["b_crypto_bps"].abs() <= btc["cost_2leg_maker_bps"]).mean()), 2),
        "BTC_pct_crypto_inside_dynamic_3leg_taker_band": round(100.0 * float((btc["b_crypto_bps"].abs() <= btc["cost_3leg_taker_bps"]).mean()), 2),
    }
    (models_dir / "variance_decomposition.json").write_text(json.dumps(var_decomp, indent=2))

    # 3. Unit-Root & Stationarity Suite (H2)
    ur_rows = []
    for lbl, arr in [
        ("BTC ln P_IDR", btc["ln_p_idr"].values),
        ("BTC d(ln P_IDR)", np.diff(btc["ln_p_idr"].values)),
        ("BTC ln P_USDT", btc["ln_p_usdt"].values),
        ("BTC d(ln P_USDT)", np.diff(btc["ln_p_usdt"].values)),
        ("Indodax ln U_IDR (USDT/IDR)", btc["ln_u_idr"].values),
        ("Indodax d(ln U_IDR)", np.diff(btc["ln_u_idr"].values)),
        ("BI JISDOR ln S_FX", btc["ln_s_fx"].values),
        ("BI JISDOR d(ln S_FX)", np.diff(btc["ln_s_fx"].values)),
        ("BTC B_total (bps)", btc["b_total_bps"].values),
        ("BTC B_crypto (bps)", btc["b_crypto_bps"].values),
        ("BTC B_stablecoin_FX (bps)", btc["b_stablecoin_fx_bps"].values),
        ("ETH B_total (bps)", eth["b_total_bps"].values),
        ("ETH B_crypto (bps)", eth["b_crypto_bps"].values),
        ("XRP B_total (bps)", xrp["b_total_bps"].values),
        ("XRP B_crypto (bps)", xrp["b_crypto_bps"].values),
    ]:
        ur_rows.append(run_unit_root_suite(arr, lbl))
    pd.DataFrame(ur_rows).to_csv(tables_dir / "table2_unit_root_tests.csv", index=False)

    # 4. Cointegration & Bootstrap (H3, H4, H5)
    coint_specs = [
        ("BTC_Unadjusted (ln P_IDR vs ln P_USDT)", btc["ln_p_idr"].values, btc["ln_p_usdt"].values),
        ("BTC_JISDOR_Converted (ln P_IDR vs ln[P_USDT*JISDOR])", btc["ln_p_idr"].values, btc["ln_p_global_fx"].values),
        ("BTC_USDT_Converted (ln P_IDR vs ln[P_USDT*U_IDR])", btc["ln_p_idr"].values, btc["ln_p_global_usdt"].values),
        ("BTC_SpotFX_Converted (ln P_IDR vs ln[P_USDT*SpotFX])", btc["ln_p_idr"].values, btc["ln_p_usdt"].values + np.log(btc["spot_idr_usd"].values)),
        ("USDT_IDR_vs_JISDOR (ln U_IDR vs ln JISDOR)", btc["ln_u_idr"].values, btc["ln_s_fx"].values),
        ("ETH_Unadjusted (ln P_IDR vs ln P_USDT)", eth["ln_p_idr"].values, eth["ln_p_usdt"].values),
        ("ETH_JISDOR_Converted (ln P_IDR vs ln[P_USDT*JISDOR])", eth["ln_p_idr"].values, eth["ln_p_global_fx"].values),
        ("ETH_USDT_Converted (ln P_IDR vs ln[P_USDT*U_IDR])", eth["ln_p_idr"].values, eth["ln_p_global_usdt"].values),
        ("XRP_Unadjusted (ln P_IDR vs ln P_USDT)", xrp["ln_p_idr"].values, xrp["ln_p_usdt"].values),
        ("XRP_JISDOR_Converted (ln P_IDR vs ln[P_USDT*JISDOR])", xrp["ln_p_idr"].values, xrp["ln_p_global_fx"].values),
        ("XRP_USDT_Converted (ln P_IDR vs ln[P_USDT*U_IDR])", xrp["ln_p_idr"].values, xrp["ln_p_global_usdt"].values),
    ]
    coint_rows = []
    boot_rows = []
    for idx_s, (spec_name, y_s, x_s) in enumerate(coint_specs):
        mask = np.isfinite(y_s) & np.isfinite(x_s)
        y_c, x_c = y_s[mask], x_s[mask]
        eg = engle_granger_test(y_c, x_c)
        fv = fixed_vector_basis_test(y_c, x_c)
        Y_mat = np.column_stack([y_c, x_c])
        joh = johansen_with_finite_sample(Y_mat, det_order=0, k_ar_diff=1)
        boot = null_imposed_vecm_residual_bootstrap(Y_mat, det_order=0, k_ar_diff=1, n_boot=9999, seed=seed + idx_s)
        coint_rows.append({"specification": spec_name, **eg, **fv, **joh, "boot_trace_pval": boot["trace_boot_pval"], "boot_maxeig_pval": boot["maxeig_boot_pval"]})
        boot_rows.append({"specification": spec_name, **boot})

    pd.DataFrame(coint_rows).to_csv(tables_dir / "table3_cointegration_and_reconciliation.csv", index=False)
    pd.DataFrame(boot_rows).to_csv(tables_dir / "table4_bootstrap_rank_tests.csv", index=False)

    # Controlled DGP size & power validation for bootstrap (H5)
    dgp_val = evaluate_bootstrap_size_and_power(sample_sizes=[25, 100, 500], n_mc=150, n_boot=299, seed=seed)
    pd.DataFrame(dgp_val).to_csv(tables_dir / "table4b_bootstrap_dgp_validation.csv", index=False)

    # 5. VECM, Weak Exogeneity & Daily Return Pass-Through (H6, H7)
    vecm_rows = []
    for label, df in [
        ("BTC vs JISDOR-Global (Daily Bus. Days)", (btc["ln_p_idr"].values, btc["ln_p_global_fx"].values)),
        ("BTC vs Indodax-USDT-Global (Daily Bus. Days)", (btc["ln_p_idr"].values, btc["ln_p_global_usdt"].values)),
        ("Indodax USDT/IDR vs BI JISDOR (Daily Bus. Days)", (btc["ln_u_idr"].values, btc["ln_s_fx"].values)),
        ("ETH vs JISDOR-Global (Daily Bus. Days)", (eth["ln_p_idr"].values, eth["ln_p_global_fx"].values)),
        ("ETH vs Indodax-USDT-Global (Daily Bus. Days)", (eth["ln_p_idr"].values, eth["ln_p_global_usdt"].values)),
        ("XRP vs JISDOR-Global (Daily Bus. Days)", (xrp["ln_p_idr"].values, xrp["ln_p_global_fx"].values)),
        ("XRP vs Indodax-USDT-Global (Daily Bus. Days)", (xrp["ln_p_idr"].values, xrp["ln_p_global_usdt"].values)),
    ]:
        v = estimate_bivariate_vecm(df[0], df[1], k_ar_diff=1, det_order="co", hac_lags=5, sampling_unit="days")
        vecm_rows.append({"system": label, **v})
    pd.DataFrame(vecm_rows).to_csv(tables_dir / "table5_vecm_error_correction.csv", index=False)

    pt_rows = []
    for name, df in [("BTC", btc), ("ETH", eth), ("XRP", xrp)]:
        pt = estimate_return_passthrough(
            df["indodax_close"].values,
            df["binance_close"].values,
            df["usdtidr_close"].values,
            df["jisdor_idr_usd"].values,
            hac_lags=5,
        )
        pt_rows.append({"asset": name, **pt})
    pd.DataFrame(pt_rows).to_csv(tables_dir / "table6_return_passthrough.csv", index=False)

    # 6. High-Frequency 5-Minute 24/7 Analysis & Threshold TAR (H6, H9)
    p5_btc = pd.read_csv(proc_dir / "btc_5m_panel_2021_2026.csv.gz")
    p5_act = p5_btc[p5_btc["is_active_both_indo"]].reset_index(drop=True)

    hf_vecm_all = estimate_bivariate_vecm(
        np.log(p5_btc["indodax_btcidr"].values),
        np.log(p5_btc["binance_btcusdt"].values) + np.log(p5_btc["indodax_usdtidr"].values),
        k_ar_diff=5, det_order="co", hac_lags=12, sampling_unit="5m_bars",
    )
    hf_vecm_act = estimate_bivariate_vecm(
        np.log(p5_act["indodax_btcidr"].values),
        np.log(p5_act["binance_btcusdt"].values) + np.log(p5_act["indodax_usdtidr"].values),
        k_ar_diff=5, det_order="co", hac_lags=12, sampling_unit="5m_bars",
    )
    # Daily Band-TAR & 5-minute subsample TAR (last 6 months active vs daily full)
    tar_daily_crypto = estimate_band_tar(btc["b_crypto_bps"].values, p_lags=1, n_boot=499, seed=seed)
    tar_daily_total = estimate_band_tar(btc["b_total_bps"].values, p_lags=1, n_boot=499, seed=seed + 1)
    # 5-minute TAR on full 2026 active bars (or last 50,000 bars for clean runtime)
    p5_recent = p5_act.tail(25_000).reset_index(drop=True)
    tar_5m_recent = estimate_band_tar(p5_recent["b_crypto_bps"].values, p_lags=2, n_boot=299, seed=seed + 2)

    tar_summary = {
        "hf_vecm_all_5m": hf_vecm_all,
        "hf_vecm_active_5m": hf_vecm_act,
        "tar_daily_b_crypto": tar_daily_crypto,
        "tar_daily_b_total": tar_daily_total,
        "tar_5m_recent_25k_active": tar_5m_recent,
    }
    (models_dir / "intraday_and_tar_results.json").write_text(json.dumps(tar_summary, indent=2))

    # 7. Structural Breaks & Regulatory Events (H10)
    ev_crypto = evaluate_event_windows(btc, "date", "b_crypto_bps", cfg["structural_breaks"]["events"], window_days=30)
    ev_sf = evaluate_event_windows(btc, "date", "b_stablecoin_fx_bps", cfg["structural_breaks"]["events"], window_days=30)
    ev_crypto["basis_leg"] = "B_crypto"
    ev_sf["basis_leg"] = "B_stablecoin_FX"
    pd.concat([ev_crypto, ev_sf], ignore_index=True).to_csv(tables_dir / "table7_regulatory_event_windows.csv", index=False)

    # 8. Robustness & Falsification (H11, H12)
    sync_sens = run_synchronization_sensitivity(btc)
    sync_sens.to_csv(tables_dir / "table8_synchronization_sensitivity.csv", index=False)

    fals = run_falsification_tests(btc, xrp_df=xrp)
    fals.to_csv(tables_dir / "table9_falsification_tests.csv", index=False)

    lag_sens = run_lag_and_deterministic_sensitivity(btc)
    lag_sens.to_csv(tables_dir / "table10_lag_deterministic_sensitivity.csv", index=False)

    # Binance direct IDR vs Indodax comparison (Nov 2025 - Nov 2026)
    bin_indo_path = proc_dir / "binance_vs_indodax_idr_5m.csv.gz"
    if bin_indo_path.exists():
        bdi = pd.read_csv(bin_indo_path)
        bdi_summary = {
            "n_5m_bars": int(len(bdi)),
            "start": str(bdi["timestamp_utc"].min()),
            "end": str(bdi["timestamp_utc"].max()),
            "btcidr_indo_minus_bin_mean_bps": round(float(bdi["btcidr_indo_vs_bin_bps"].mean()), 2),
            "btcidr_indo_minus_bin_sd_bps": round(float(bdi["btcidr_indo_vs_bin_bps"].std(ddof=1)), 2),
            "usdtidr_indo_minus_bin_mean_bps": round(float(bdi["usdtidr_indo_vs_bin_bps"].mean()), 2),
            "usdtidr_indo_minus_bin_sd_bps": round(float(bdi["usdtidr_indo_vs_bin_bps"].std(ddof=1)), 2),
        }
        (models_dir / "binance_vs_indodax_idr_summary.json").write_text(json.dumps(bdi_summary, indent=2))

    # Write Experiment Registry (Part N)
    registry = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "experiments": [
            {"id": "EXP-01", "name": "Basis Decomposition & Variance Identity", "status": "COMPLETED", "output": "results/tables/table1_descriptive_statistics.csv"},
            {"id": "EXP-02", "name": "Unit-Root & Stationarity Suite (ADF/PP/KPSS/ZA)", "status": "COMPLETED", "output": "results/tables/table2_unit_root_tests.csv"},
            {"id": "EXP-03", "name": "Engle-Granger, Fixed-(1,-1) & Reinsel-Ahn/Cheung-Lai Johansen", "status": "COMPLETED", "output": "results/tables/table3_cointegration_and_reconciliation.csv"},
            {"id": "EXP-04", "name": "Null-Imposed VECM i.i.d. Residual Bootstrap (B=9,999) & DGP Validation", "status": "COMPLETED", "output": "results/tables/table4_bootstrap_rank_tests.csv"},
            {"id": "EXP-05", "name": "Bivariate VECM, Weak Exogeneity & Daily Return Pass-Through", "status": "COMPLETED", "output": "results/tables/table5_vecm_error_correction.csv"},
            {"id": "EXP-06", "name": "5-Minute Intraday VECM (All vs Active Volume) & Band-TAR", "status": "COMPLETED", "output": "results/models/intraday_and_tar_results.json"},
            {"id": "EXP-07", "name": "Historical Fee Reconstruction & Route-Specific Costs", "status": "COMPLETED", "output": "results/tables/route_specific_execution_costs.csv"},
            {"id": "EXP-08", "name": "Regulatory & Structural Break Event Windows", "status": "COMPLETED", "output": "results/tables/table7_regulatory_event_windows.csv"},
            {"id": "EXP-09", "name": "Synchronization Window, Lag & Spot-FX Robustness", "status": "COMPLETED", "output": "results/tables/table8_synchronization_sensitivity.csv"},
            {"id": "EXP-10", "name": "Falsification Suite (Omitted FX, EUR/USD Placebo, Mismatch, Placebo Break)", "status": "COMPLETED", "output": "results/tables/table9_falsification_tests.csv"},
        ],
    }
    (root / "experiments" / "experiment_registry.yaml").write_text(yaml.safe_dump(registry, sort_keys=False))
    return {"status": "COMPLETED", "var_decomp": var_decomp}
