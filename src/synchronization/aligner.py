"""Data cleaning, JISDOR time-alignment, quality diagnostics, and panel construction."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd

from src.acquisition.bi_jisdor import parse_bi_jisdor_excel
from src.acquisition.binance_vision import load_binance_klines_df
from src.acquisition.coinbase_kraken import load_coinbase_df, load_kraken_df
from src.acquisition.fx_spot import parse_frankfurter_fx, parse_yahoo_fx
from src.acquisition.indodax_history import load_indodax_df
from src.processing.jisdor_calendar import build_jisdor_schedule_calendar
from src.variables.basis import compute_basis_decomposition


def _quality_check_series(df: pd.DataFrame, ts_col: str, px_col: str, vol_col: str | None, name: str) -> Dict[str, Any]:
    if df.empty:
        return {"series": name, "rows": 0}
    ts = pd.to_datetime(df[ts_col], utc=True) if ts_col == "timestamp_utc" else pd.to_datetime(df[ts_col])
    px = pd.to_numeric(df[px_col], errors="coerce")
    ret = np.log(px).diff().dropna()
    out = {
        "series": name,
        "rows": int(len(df)),
        "start": ts.min().isoformat(),
        "end": ts.max().isoformat(),
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "non_positive_prices": int((px <= 0).sum()),
        "missing_prices": int(px.isna().sum()),
        "extreme_abs_log_ret_gt_15pct": int((ret.abs() > 0.15).sum()),
        "max_abs_log_ret": float(ret.abs().max()) if len(ret) else 0.0,
    }
    if vol_col and vol_col in df.columns:
        vol = pd.to_numeric(df[vol_col], errors="coerce").fillna(0.0)
        out["zero_volume_rows"] = int((vol == 0).sum())
        out["zero_volume_pct"] = round(100.0 * float((vol == 0).mean()), 4)
    return out


def _asof_window_match(
    targets: pd.DataFrame,
    market: pd.DataFrame,
    target_ts_col: str,
    prefix: str,
    offset_minutes: int = 0,
    tolerance_minutes: int = 5,
) -> pd.DataFrame:
    """Match each target timestamp + offset to first valid observation at or after target within tolerance."""
    t_df = targets[[target_ts_col]].copy()
    t_df["_query_ts"] = pd.to_datetime(t_df[target_ts_col], utc=True) + pd.Timedelta(minutes=offset_minutes)
    t_df = t_df.sort_values("_query_ts")

    m_df = market[["timestamp_utc", "close", "volume"]].copy().sort_values("timestamp_utc")
    m_df = m_df.rename(
        columns={
            "timestamp_utc": f"{prefix}_obs_ts_utc",
            "close": f"{prefix}_close",
            "volume": f"{prefix}_volume",
        }
    )

    merged = pd.merge_asof(
        t_df,
        m_df,
        left_on="_query_ts",
        right_on=f"{prefix}_obs_ts_utc",
        direction="forward",
        tolerance=pd.Timedelta(minutes=tolerance_minutes),
    )
    merged[f"{prefix}_lag_sec"] = (
        merged[f"{prefix}_obs_ts_utc"] - pd.to_datetime(merged[target_ts_col], utc=True)
    ).dt.total_seconds()
    return merged.sort_index()


def build_all_datasets(root: Path) -> Dict[str, Any]:
    raw_dir = root / "data" / "raw"
    proc_dir = root / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load official BI JISDOR
    j_files = sorted((raw_dir / "bi_jisdor").glob("bi_jisdor_*.xlsx"))
    jdf = parse_bi_jisdor_excel(j_files[-1])
    jisdor_dates = set(jdf["date"].tolist())

    # 2. Build JISDOR schedule calendar
    cal = build_jisdor_schedule_calendar(
        root / "config" / "sampling.yaml",
        start_date="2021-01-01",
        end_date="2026-11-12",
        jisdor_dates=jisdor_dates,
    )
    cal = cal.merge(jdf, on="date", how="left")
    # Also attach spot FX benchmarks (Yahoo IDR=X, EURUSD=X, Frankfurter ECB)
    y_idr_file = [p for p in sorted((raw_dir / "fx_spot").glob("yahoo_idr_x_*.json")) if not p.name.endswith("_meta.json")][-1]
    y_eur_file = [p for p in sorted((raw_dir / "fx_spot").glob("yahoo_eurusd_x_*.json")) if not p.name.endswith("_meta.json")][-1]
    fdf_file = [p for p in sorted((raw_dir / "fx_spot").glob("frankfurter_USD_IDR_*.json")) if not p.name.endswith("_meta.json")][-1]
    y_idr = parse_yahoo_fx(y_idr_file, "spot_idr_usd")
    y_eur = parse_yahoo_fx(y_eur_file, "eur_usd")
    fdf = parse_frankfurter_fx(fdf_file)

    cal = cal.merge(y_idr[["date", "spot_idr_usd"]], on="date", how="left")
    cal = cal.merge(y_eur[["date", "eur_usd"]], on="date", how="left")
    cal = cal.merge(fdf[["date", "ecb_idr_usd"]], on="date", how="left")
    cal["jisdor_idr_usd_cf"] = cal["jisdor_idr_usd"].ffill()
    cal["jisdor_next_day_idr_usd"] = cal["jisdor_idr_usd"].shift(-1)
    cal.to_csv(proc_dir / "jisdor_schedule_calendar.csv", index=False)

    # 3. Load crypto 5m & 1d series
    indo_btc_5m = load_indodax_df(raw_dir / "indodax", "BTCIDR", "5")
    indo_usdt_5m = load_indodax_df(raw_dir / "indodax", "USDTIDR", "5")
    indo_eth_5m = load_indodax_df(raw_dir / "indodax", "ETHIDR", "5")
    indo_xrp_5m = load_indodax_df(raw_dir / "indodax", "XRPIDR", "5")
    indo_btcusdt_5m = load_indodax_df(raw_dir / "indodax", "BTCUSDT", "5")

    bin_btc_5m = load_binance_klines_df(raw_dir / "binance", "BTCUSDT", "5m")
    bin_eth_5m = load_binance_klines_df(raw_dir / "binance", "ETHUSDT", "5m")
    bin_xrp_5m = load_binance_klines_df(raw_dir / "binance", "XRPUSDT", "5m")
    bin_usdc_5m = load_binance_klines_df(raw_dir / "binance", "USDCUSDT", "5m")
    bin_btcidr_5m = load_binance_klines_df(raw_dir / "binance", "BTCIDR", "5m")
    bin_usdtidr_5m = load_binance_klines_df(raw_dir / "binance", "USDTIDR", "5m")

    indo_btc_1d = load_indodax_df(raw_dir / "indodax", "BTCIDR", "1D")
    indo_usdt_1d = load_indodax_df(raw_dir / "indodax", "USDTIDR", "1D")
    bin_btc_1d = load_binance_klines_df(raw_dir / "binance", "BTCUSDT", "1d")

    cb_usdt_1h = load_coinbase_df(raw_dir / "coinbase", "USDT-USD", 3600)
    cb_usdt_1d = load_coinbase_df(raw_dir / "coinbase", "USDT-USD", 86400)
    cb_btc_1d = load_coinbase_df(raw_dir / "coinbase", "BTC-USD", 86400)
    kr_usdt_1d = load_kraken_df(raw_dir / "kraken", "USDTUSD", 1440)

    # Quality diagnostics (Part E6)
    diag = {
        "series_checks": [
            _quality_check_series(jdf, "date", "jisdor_idr_usd", None, "bi_jisdor"),
            _quality_check_series(indo_btc_5m, "timestamp_utc", "close", "volume", "indodax_btcidr_5m"),
            _quality_check_series(indo_usdt_5m, "timestamp_utc", "close", "volume", "indodax_usdtidr_5m"),
            _quality_check_series(indo_eth_5m, "timestamp_utc", "close", "volume", "indodax_ethidr_5m"),
            _quality_check_series(indo_xrp_5m, "timestamp_utc", "close", "volume", "indodax_xrpidr_5m"),
            _quality_check_series(indo_btcusdt_5m, "timestamp_utc", "close", "volume", "indodax_btcusdt_5m"),
            _quality_check_series(bin_btc_5m, "timestamp_utc", "close", "volume", "binance_btcusdt_5m"),
            _quality_check_series(bin_eth_5m, "timestamp_utc", "close", "volume", "binance_ethusdt_5m"),
            _quality_check_series(bin_xrp_5m, "timestamp_utc", "close", "volume", "binance_xrpusdt_5m"),
            _quality_check_series(cb_usdt_1h, "timestamp_utc", "close", "volume", "coinbase_usdt_usd_1h"),
        ]
    }

    # 4. Build synchronized JISDOR business-day datasets for BTC, ETH, XRP
    pub_days = cal[cal["is_jisdor_published"]].copy().reset_index(drop=True)
    pub_days["pub_ts_utc"] = pd.to_datetime(pub_days["pub_timestamp_utc"], utc=True)

    asset_specs = [
        ("BTC", indo_btc_5m, bin_btc_5m, "btc_jisdor_sync_primary.csv"),
        ("ETH", indo_eth_5m, bin_eth_5m, "eth_jisdor_sync_primary.csv"),
        ("XRP", indo_xrp_5m, bin_xrp_5m, "xrp_jisdor_sync_primary.csv"),
    ]

    for asset, indo_5m, bin_5m, out_name in asset_specs:
        base = pub_days.copy()
        # Primary 0m (first valid 5m bar at/after JISDOR fixing, tol <= 5m)
        m_indo = _asof_window_match(base, indo_5m, "pub_ts_utc", "indodax", offset_minutes=0, tolerance_minutes=5)
        m_usdt = _asof_window_match(base, indo_usdt_5m, "pub_ts_utc", "usdtidr", offset_minutes=0, tolerance_minutes=5)
        m_bin = _asof_window_match(base, bin_5m, "pub_ts_utc", "binance", offset_minutes=0, tolerance_minutes=5)
        m_cb = _asof_window_match(base, cb_usdt_1h, "pub_ts_utc", "cb_usdtusd", offset_minutes=-60, tolerance_minutes=120)

        for m, cols in [
            (m_indo, ["indodax_obs_ts_utc", "indodax_close", "indodax_volume", "indodax_lag_sec"]),
            (m_usdt, ["usdtidr_obs_ts_utc", "usdtidr_close", "usdtidr_volume", "usdtidr_lag_sec"]),
            (m_bin, ["binance_obs_ts_utc", "binance_close", "binance_volume", "binance_lag_sec"]),
            (m_cb, ["cb_usdtusd_close"]),
        ]:
            for c in cols:
                base[c] = m[c].values

        # Sensitivity alignment offsets for BTC (-15m, +5m, +15m, and 23:59 UTC close)
        if asset == "BTC":
            for off, tag in [(-15, "m15"), (5, "p5"), (15, "p15")]:
                mi = _asof_window_match(base, indo_5m, "pub_ts_utc", f"indo_{tag}", offset_minutes=off, tolerance_minutes=5)
                mu = _asof_window_match(base, indo_usdt_5m, "pub_ts_utc", f"usdt_{tag}", offset_minutes=off, tolerance_minutes=5)
                mb = _asof_window_match(base, bin_5m, "pub_ts_utc", f"bin_{tag}", offset_minutes=off, tolerance_minutes=5)
                base[f"indodax_close_{tag}"] = mi[f"indo_{tag}_close"].values
                base[f"usdtidr_close_{tag}"] = mu[f"usdt_{tag}_close"].values
                base[f"binance_close_{tag}"] = mb[f"bin_{tag}_close"].values

            # 23:59 UTC close (daily 1D bar) comparison
            d1_i = indo_btc_1d.assign(date=indo_btc_1d["timestamp_utc"].dt.strftime("%Y-%m-%d"))[["date", "close"]].rename(columns={"close": "indodax_1d_close"})
            d1_u = indo_usdt_1d.assign(date=indo_usdt_1d["timestamp_utc"].dt.strftime("%Y-%m-%d"))[["date", "close"]].rename(columns={"close": "usdtidr_1d_close"})
            d1_b = bin_btc_1d.assign(date=bin_btc_1d["timestamp_utc"].dt.strftime("%Y-%m-%d"))[["date", "close"]].rename(columns={"close": "binance_1d_close"})
            d1_cb_btc = cb_btc_1d.assign(date=cb_btc_1d["timestamp_utc"].dt.strftime("%Y-%m-%d"))[["date", "close"]].rename(columns={"close": "coinbase_btc_usd_1d"})
            base = base.merge(d1_i, on="date", how="left").merge(d1_u, on="date", how="left").merge(d1_b, on="date", how="left").merge(d1_cb_btc, on="date", how="left")

        valid = base.dropna(subset=["indodax_close", "usdtidr_close", "binance_close", "jisdor_idr_usd"]).copy()
        valid["is_stale_indodax"] = valid["indodax_volume"].fillna(0) == 0
        valid["is_stale_usdtidr"] = valid["usdtidr_volume"].fillna(0) == 0

        valid = compute_basis_decomposition(
            valid,
            p_idr_col="indodax_close",
            p_usdt_col="binance_close",
            u_idr_col="usdtidr_close",
            s_fx_col="jisdor_idr_usd",
            asset=asset,
            usdt_usd_col="cb_usdtusd_close",
        )
        valid.to_csv(proc_dir / out_name, index=False)
        diag[f"{asset.lower()}_primary_rows"] = int(len(valid))
        diag[f"{asset.lower()}_primary_stale_indo_pct"] = round(100.0 * float(valid["is_stale_indodax"].mean()), 2)

    # 5. All-calendar-days (with carry-forward JISDOR flagged, plus weekend-only diagnostics)
    cal_pub = cal.copy()
    cal_pub["pub_ts_utc"] = pd.to_datetime(cal_pub["pub_timestamp_utc"], utc=True)
    m_i = _asof_window_match(cal_pub, indo_btc_5m, "pub_ts_utc", "indodax", 0, 5)
    m_u = _asof_window_match(cal_pub, indo_usdt_5m, "pub_ts_utc", "usdtidr", 0, 5)
    m_b = _asof_window_match(cal_pub, bin_btc_5m, "pub_ts_utc", "binance", 0, 5)
    for m, cols in [
        (m_i, ["indodax_close", "indodax_volume"]),
        (m_u, ["usdtidr_close", "usdtidr_volume"]),
        (m_b, ["binance_close", "binance_volume"]),
    ]:
        for c in cols:
            cal_pub[c] = m[c].values
    cal_valid = cal_pub.dropna(subset=["indodax_close", "usdtidr_close", "binance_close", "jisdor_idr_usd_cf"]).copy()
    cal_valid = compute_basis_decomposition(
        cal_valid,
        p_idr_col="indodax_close",
        p_usdt_col="binance_close",
        u_idr_col="usdtidr_close",
        s_fx_col="jisdor_idr_usd_cf",
        asset="BTC",
    )
    cal_valid.to_csv(proc_dir / "btc_calendar_days_sensitivity.csv", index=False)

    # 6. Full 24/7 5-minute panel (2021-2026) for BTC, ETH, XRP crypto-basis & Indodax BTCUSDT
    p5_btc = (
        indo_btc_5m[["timestamp_utc", "close", "volume"]]
        .rename(columns={"close": "indodax_btcidr", "volume": "indodax_btcidr_vol"})
        .merge(
            indo_usdt_5m[["timestamp_utc", "close", "volume"]].rename(
                columns={"close": "indodax_usdtidr", "volume": "indodax_usdtidr_vol"}
            ),
            on="timestamp_utc",
            how="inner",
        )
        .merge(
            bin_btc_5m[["timestamp_utc", "close", "volume"]].rename(
                columns={"close": "binance_btcusdt", "volume": "binance_btcusdt_vol"}
            ),
            on="timestamp_utc",
            how="inner",
        )
    )
    p5_btc["b_crypto_bps"] = 10_000.0 * (
        np.log(p5_btc["indodax_btcidr"]) - np.log(p5_btc["binance_btcusdt"]) - np.log(p5_btc["indodax_usdtidr"])
    )
    p5_btc["is_active_both_indo"] = (p5_btc["indodax_btcidr_vol"] > 0) & (p5_btc["indodax_usdtidr_vol"] > 0)
    p5_btc.to_csv(proc_dir / "btc_5m_panel_2021_2026.csv.gz", index=False, compression="gzip")
    diag["btc_5m_panel_rows"] = int(len(p5_btc))
    diag["btc_5m_active_both_pct"] = round(100.0 * float(p5_btc["is_active_both_indo"].mean()), 2)

    # ETH & XRP 5m panels (for multi-asset intraday comparison)
    for asset, idf, bdf in [("eth", indo_eth_5m, bin_eth_5m), ("xrp", indo_xrp_5m, bin_xrp_5m)]:
        p5 = (
            idf[["timestamp_utc", "close", "volume"]]
            .rename(columns={"close": f"indodax_{asset}idr", "volume": f"indodax_{asset}idr_vol"})
            .merge(
                indo_usdt_5m[["timestamp_utc", "close", "volume"]].rename(
                    columns={"close": "indodax_usdtidr", "volume": "indodax_usdtidr_vol"}
                ),
                on="timestamp_utc",
                how="inner",
            )
            .merge(
                bdf[["timestamp_utc", "close", "volume"]].rename(
                    columns={"close": f"binance_{asset}usdt", "volume": f"binance_{asset}usdt_vol"}
                ),
                on="timestamp_utc",
                how="inner",
            )
        )
        p5["b_crypto_bps"] = 10_000.0 * (
            np.log(p5[f"indodax_{asset}idr"]) - np.log(p5[f"binance_{asset}usdt"]) - np.log(p5["indodax_usdtidr"])
        )
        p5["is_active_both_indo"] = (p5[f"indodax_{asset}idr_vol"] > 0) & (p5["indodax_usdtidr_vol"] > 0)
        p5.to_csv(proc_dir / f"{asset}_5m_panel_2021_2026.csv.gz", index=False, compression="gzip")
        diag[f"{asset}_5m_panel_rows"] = int(len(p5))

    # Binance direct IDR pair (Nov 2025 - Nov 2026) vs Indodax cross-venue comparison
    if not bin_btcidr_5m.empty and not bin_usdtidr_5m.empty:
        bin_direct = (
            indo_btc_5m[["timestamp_utc", "close", "volume"]].rename(columns={"close": "indo_btcidr", "volume": "indo_btcidr_vol"})
            .merge(bin_btcidr_5m[["timestamp_utc", "close", "volume"]].rename(columns={"close": "bin_btcidr", "volume": "bin_btcidr_vol"}), on="timestamp_utc", how="inner")
            .merge(indo_usdt_5m[["timestamp_utc", "close"]].rename(columns={"close": "indo_usdtidr"}), on="timestamp_utc", how="inner")
            .merge(bin_usdtidr_5m[["timestamp_utc", "close"]].rename(columns={"close": "bin_usdtidr"}), on="timestamp_utc", how="inner")
        )
        bin_direct["btcidr_indo_vs_bin_bps"] = 10_000.0 * (np.log(bin_direct["indo_btcidr"]) - np.log(bin_direct["bin_btcidr"]))
        bin_direct["usdtidr_indo_vs_bin_bps"] = 10_000.0 * (np.log(bin_direct["indo_usdtidr"]) - np.log(bin_direct["bin_usdtidr"]))
        bin_direct.to_csv(proc_dir / "binance_vs_indodax_idr_5m.csv.gz", index=False, compression="gzip")
        diag["binance_idr_overlap_5m_rows"] = int(len(bin_direct))

    # 1m 2026 micro-panel (if acquired)
    indo_btc_1m = load_indodax_df(raw_dir / "indodax", "BTCIDR", "1")
    indo_usdt_1m = load_indodax_df(raw_dir / "indodax", "USDTIDR", "1")
    bin_btc_1m = load_binance_klines_df(raw_dir / "binance", "BTCUSDT", "1m")
    if not indo_btc_1m.empty and not indo_usdt_1m.empty and not bin_btc_1m.empty:
        p1 = (
            indo_btc_1m[["timestamp_utc", "close", "volume"]].rename(columns={"close": "indodax_btcidr", "volume": "indodax_btcidr_vol"})
            .merge(indo_usdt_1m[["timestamp_utc", "close", "volume"]].rename(columns={"close": "indodax_usdtidr", "volume": "indodax_usdtidr_vol"}), on="timestamp_utc", how="inner")
            .merge(bin_btc_1m[["timestamp_utc", "close", "volume"]].rename(columns={"close": "binance_btcusdt", "volume": "binance_btcusdt_vol"}), on="timestamp_utc", how="inner")
        )
        p1["b_crypto_bps"] = 10_000.0 * (
            np.log(p1["indodax_btcidr"]) - np.log(p1["binance_btcusdt"]) - np.log(p1["indodax_usdtidr"])
        )
        p1.to_csv(proc_dir / "btc_1m_2026_panel.csv.gz", index=False, compression="gzip")
        diag["btc_1m_2026_rows"] = int(len(p1))

    (proc_dir / "data_quality_diagnostics.json").write_text(json.dumps(diag, indent=2))
    return diag
