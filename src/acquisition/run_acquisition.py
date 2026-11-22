"""Master data acquisition runner producing raw archives, manifest, and source coverage matrix."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from src.acquisition.bi_jisdor import download_bi_jisdor_excel, parse_bi_jisdor_excel
from src.acquisition.binance_vision import download_binance_klines, load_binance_klines_df
from src.acquisition.coinbase_kraken import (
    download_coinbase_candles,
    download_kraken_ohlc,
    load_coinbase_df,
    load_kraken_df,
)
from src.acquisition.fx_spot import (
    download_frankfurter_fx,
    download_yahoo_fx,
    parse_frankfurter_fx,
    parse_yahoo_fx,
)
from src.acquisition.indodax_history import download_indodax_history, load_indodax_df
from src.acquisition.orderbook_snapshot import capture_orderbook_snapshots


def _coverage_row(
    provider: str,
    exchange: str,
    instrument: str,
    pair: str,
    data_type: str,
    df: pd.DataFrame,
    ts_col: str,
    price_col: str,
    freq: str,
    tz_label: str,
    source_url: str,
    licence: str,
    status: str,
    limitations: str,
) -> Dict[str, Any]:
    if df.empty:
        return {
            "provider": provider,
            "exchange": exchange,
            "instrument": instrument,
            "pair": pair,
            "data_type": data_type,
            "first_timestamp": None,
            "last_timestamp": None,
            "frequency": freq,
            "timezone": tz_label,
            "rows_retrieved": 0,
            "unique_timestamps": 0,
            "missingness_pct": 100.0,
            "duplicate_count": 0,
            "zero_invalid_price_count": 0,
            "retrieval_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source_url": source_url,
            "licence_usage_notes": licence,
            "acquisition_status": status,
            "known_limitations": limitations,
        }

    ts = pd.to_datetime(df[ts_col], utc=True) if ts_col == "timestamp_utc" else pd.to_datetime(df[ts_col])
    n_rows = len(df)
    n_uniq = int(ts.nunique())
    dups = n_rows - n_uniq
    prices = pd.to_numeric(df[price_col], errors="coerce")
    bad_px = int((prices.isna() | (prices <= 0)).sum())

    # Estimate missingness vs expected grid
    if freq in ("1d", "1D"):
        expected = max(1, int((ts.max() - ts.min()).days) + 1)
    elif freq == "5m":
        expected = max(1, int((ts.max() - ts.min()).total_seconds() // 300) + 1)
    elif freq == "1m":
        expected = max(1, int((ts.max() - ts.min()).total_seconds() // 60) + 1)
    elif freq == "1h":
        expected = max(1, int((ts.max() - ts.min()).total_seconds() // 3600) + 1)
    else:
        expected = n_uniq
    miss_pct = max(0.0, round(100.0 * (1.0 - n_uniq / expected), 4)) if "business" not in limitations.lower() else round(100.0 * (1.0 - n_uniq / expected), 4)

    return {
        "provider": provider,
        "exchange": exchange,
        "instrument": instrument,
        "pair": pair,
        "data_type": data_type,
        "first_timestamp": ts.min().isoformat(),
        "last_timestamp": ts.max().isoformat(),
        "frequency": freq,
        "timezone": tz_label,
        "rows_retrieved": n_rows,
        "unique_timestamps": n_uniq,
        "missingness_pct": miss_pct,
        "duplicate_count": dups,
        "zero_invalid_price_count": bad_px,
        "retrieval_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source_url": source_url,
        "licence_usage_notes": licence,
        "acquisition_status": status,
        "known_limitations": limitations,
    }


def run_all_acquisition(root: Path, config_path: Path) -> None:
    cfg = yaml.safe_load(config_path.read_text())
    acq = cfg["acquisition"]
    start_date = cfg["project"]["start_date"]
    end_date = cfg["project"]["end_date"]

    raw_dir = root / "data" / "raw"
    manifest: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "sources": {},
    }

    print("[1/6] Downloading Bank Indonesia JISDOR official Excel...", flush=True)
    manifest["sources"]["bi_jisdor"] = download_bi_jisdor_excel(raw_dir / "bi_jisdor", start_date, end_date)

    print("[2/6] Downloading Spot FX benchmarks (Yahoo IDR=X, EURUSD=X, Frankfurter ECB)...", flush=True)
    manifest["sources"]["yahoo_idrx"] = download_yahoo_fx(raw_dir / "fx_spot", "IDR=X", start_date, "2026-11-13")
    manifest["sources"]["yahoo_eurusd"] = download_yahoo_fx(raw_dir / "fx_spot", "EURUSD=X", start_date, "2026-11-13")
    manifest["sources"]["frankfurter_usdidr"] = download_frankfurter_fx(raw_dir / "fx_spot", start_date, end_date)

    print("[3/6] Capturing live cross-sectional order-book depth snapshots...", flush=True)
    manifest["sources"]["orderbook_snapshots"] = capture_orderbook_snapshots(
        raw_dir / "indodax", raw_dir / "binance"
    )

    print("[4/6] Downloading Coinbase & Kraken USD/USDT and BTC/USD reference series...", flush=True)
    cb_summaries = {}
    for prod in acq["coinbase"]["products"]:
        cb_summaries[f"{prod}_86400"] = download_coinbase_candles(
            raw_dir / "coinbase", prod, 86400, start_date, end_date, rate_limit_sec=0.2
        )
    cb_summaries["USDT-USD_3600"] = download_coinbase_candles(
        raw_dir / "coinbase", "USDT-USD", 3600, start_date, end_date, rate_limit_sec=0.2
    )
    manifest["sources"]["coinbase"] = cb_summaries
    manifest["sources"]["kraken_usdtusd"] = download_kraken_ohlc(raw_dir / "kraken", "USDTUSD", 1440)

    print("[5/6] Downloading Binance Vision historical klines with SHA-256 checksums...", flush=True)
    bin_jobs = []
    for sym in acq["binance"]["symbols_full"]:
        for iv in acq["binance"]["intervals"]:
            bin_jobs.append((sym, iv, start_date, end_date))
    for sym in acq["binance"]["symbols_bidr"]:
        for iv in acq["binance"]["intervals"]:
            bin_jobs.append((sym, iv, start_date, "2024-05-31"))
    for sym in acq["binance"]["symbols_idr"]:
        for iv in acq["binance"]["intervals"]:
            bin_jobs.append((sym, iv, "2025-11-01", end_date))
    for sym in acq["binance"]["intraday_1m_symbols"]:
        bin_jobs.append((sym, "1m", acq["binance"]["intraday_1m_start"], acq["binance"]["intraday_1m_end"]))

    bin_summaries = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {
            ex.submit(download_binance_klines, raw_dir / "binance", sym, iv, sd, ed, 0.02): (sym, iv)
            for sym, iv, sd, ed in bin_jobs
        }
        for fut in as_completed(futs):
            sym, iv = futs[fut]
            res = fut.result()
            bin_summaries[f"{sym}_{iv}"] = res
            print(f"  Binance {sym} {iv}: ok={res['files_ok']}/{res['files_total_attempted']}", flush=True)
    manifest["sources"]["binance"] = bin_summaries

    print("[6/6] Downloading Indodax TradingView history_v2 (1D, 5m, 2026 1m)...", flush=True)
    indo_jobs = []
    for sym in acq["indodax"]["symbols"]:
        for tf in acq["indodax"]["timeframes"]:
            indo_jobs.append((sym, tf, start_date, end_date))
    for sym in acq["indodax"]["intraday_1m_symbols"]:
        indo_jobs.append((sym, "1", acq["indodax"]["intraday_1m_start"], acq["indodax"]["intraday_1m_end"]))

    indo_summaries = {}
    # Polite concurrency of 2 workers across Indodax endpoints
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {
            ex.submit(download_indodax_history, raw_dir / "indodax", sym, tf, sd, ed, 8, 0.12): (sym, tf)
            for sym, tf, sd, ed in indo_jobs
        }
        for fut in as_completed(futs):
            sym, tf = futs[fut]
            res = fut.result()
            indo_summaries[f"{sym}_tf{tf}"] = res
            print(f"  Indodax {sym} tf={tf}: chunks={res['chunks_ok']}, rows={res['total_bars_raw']}, errs={len(res['errors'])}", flush=True)
    manifest["sources"]["indodax"] = indo_summaries

    (root / "data" / "manifests").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manifests" / "raw_manifest.json").write_text(json.dumps(manifest, indent=2))

    # Build source_coverage_matrix.csv (Part D8)
    print("Building data/source_coverage_matrix.csv...", flush=True)
    cov_rows: List[Dict[str, Any]] = []

    jdf = parse_bi_jisdor_excel(raw_dir / "bi_jisdor" / f"bi_jisdor_{start_date}_{end_date}.xlsx")
    cov_rows.append(
        _coverage_row(
            "Bank Indonesia", "Bank Indonesia (Interbank)", "JISDOR", "USD/IDR", "FX Reference Rate",
            jdf, "date", "jisdor_idr_usd", "1d (business days)", "WIB (10:00/15:15/16:15)",
            "https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/Default.aspx",
            "Official public BI statistical release; attribution required", "COMPLETED",
            "Business days only; excludes weekends & Indonesian public holidays",
        )
    )

    y_idr = parse_yahoo_fx(raw_dir / "fx_spot" / f"yahoo_idr_x_{start_date}_2026-11-13.json", "spot_idr_usd")
    cov_rows.append(
        _coverage_row(
            "Yahoo Finance", "Global FX Composite", "IDR=X", "USD/IDR", "Indicative FX Spot OHLC",
            y_idr, "timestamp_utc", "spot_idr_usd", "1d (business days)", "UTC",
            "https://query1.finance.yahoo.com/v8/finance/chart/IDR=X",
            "Aggregator composite indicative FX close; cross-validation only", "COMPLETED",
            "Indicative composite close; excludes weekends",
        )
    )

    y_eur = parse_yahoo_fx(raw_dir / "fx_spot" / f"yahoo_eurusd_x_{start_date}_2026-11-13.json", "eur_usd")
    cov_rows.append(
        _coverage_row(
            "Yahoo Finance", "Global FX Composite", "EURUSD=X", "EUR/USD", "Indicative FX Spot OHLC",
            y_eur, "timestamp_utc", "eur_usd", "1d (business days)", "UTC",
            "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X",
            "Aggregator composite indicative FX close; falsification check", "COMPLETED",
            "Business days only",
        )
    )

    fdf = parse_frankfurter_fx(raw_dir / "fx_spot" / f"frankfurter_USD_IDR_{start_date}_{end_date}.json")
    cov_rows.append(
        _coverage_row(
            "Frankfurter (ECB)", "European Central Bank", "USD/IDR", "USD/IDR", "Official Reference Rate",
            fdf, "date", "ecb_idr_usd", "1d (TARGET business days)", "CET/UTC (~14:00-15:00 UTC)",
            "https://api.frankfurter.app/",
            "Public ECB reference rates", "COMPLETED",
            "ECB fixing ~16:00 CET; excludes weekends & TARGET holidays",
        )
    )

    for prod in acq["coinbase"]["products"]:
        cdf = load_coinbase_df(raw_dir / "coinbase", prod, 86400)
        cov_rows.append(
            _coverage_row(
                "Coinbase Exchange", "Coinbase", prod, prod.replace("-", "/"), "Spot OHLCV",
                cdf, "timestamp_utc", "close", "1d", "UTC",
                f"https://api.exchange.coinbase.com/products/{prod}/candles",
                "Coinbase Public Market Data API", "COMPLETED",
                "USDT-USD listed May 2021",
            )
        )
    cdf_1h = load_coinbase_df(raw_dir / "coinbase", "USDT-USD", 3600)
    cov_rows.append(
        _coverage_row(
            "Coinbase Exchange", "Coinbase", "USDT-USD", "USDT/USD", "Spot OHLCV",
            cdf_1h, "timestamp_utc", "close", "1h", "UTC",
            "https://api.exchange.coinbase.com/products/USDT-USD/candles",
            "Coinbase Public Market Data API", "COMPLETED",
            "Hourly USD/USDT peg wedge from May 2021",
        )
    )

    kdf = load_kraken_df(raw_dir / "kraken", "USDTUSD", 1440)
    cov_rows.append(
        _coverage_row(
            "Kraken", "Kraken", "USDTUSD", "USDT/USD", "Spot OHLCV",
            kdf, "timestamp_utc", "close", "1d", "UTC",
            "https://api.kraken.com/0/public/OHLC",
            "Kraken Public REST API (last 720 bars cap)", "COMPLETED_TRUNCATED_720",
            "Kraken public OHLC returns at most 720 most recent bars (~Nov 2024-Nov 2026)",
        )
    )

    for sym, iv, sd, ed in bin_jobs:
        bdf = load_binance_klines_df(raw_dir / "binance", sym, iv)
        cov_rows.append(
            _coverage_row(
                "Binance Public Data Vision", "Binance Spot", sym, sym, "Spot Klines",
                bdf, "timestamp_utc", "close", iv, "UTC",
                f"https://data.binance.vision/data/spot/monthly/klines/{sym}/{iv}/",
                "Binance public historical archive; SHA-256 verified", "COMPLETED",
                "BIDR delisted 2024-05-17; IDR pairs launched Nov 2025",
            )
        )

    for sym, tf, sd, ed in indo_jobs:
        idf = load_indodax_df(raw_dir / "indodax", sym, tf)
        freq_lbl = "1d" if tf == "1D" else f"{tf}m"
        stale_pct = round(100.0 * float((idf["volume"] == 0).mean()), 2) if not idf.empty else 0.0
        cov_rows.append(
            _coverage_row(
                "Indodax", "Indodax", sym, sym, "Spot OHLCV",
                idf, "timestamp_utc", "close", freq_lbl, "UTC (Unix epoch)",
                "https://indodax.com/tradingview/history_v2",
                "Indodax public TradingView market data endpoint", "COMPLETED",
                f"Carry-forward close on zero-volume bars ({stale_pct}% zero-volume)",
            )
        )

    cov_df = pd.DataFrame(cov_rows)
    cov_df.to_csv(root / "data" / "source_coverage_matrix.csv", index=False)
    print(f"Saved data/source_coverage_matrix.csv ({len(cov_df)} rows).", flush=True)


if __name__ == "__main__":
    root_dir = Path("/Users/naresh/Desktop/Finance/indonesian_crypto_research_final")
    run_all_acquisition(root_dir, root_dir / "config" / "acquisition.yaml")
