"""Resumable downloader for Binance Spot public historical kline archives (data.binance.vision)."""
from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import requests

BASE_URL = "https://data.binance.vision/data/spot"
KLINE_COLS = [
    "open_time_raw", "open", "high", "low", "close", "volume",
    "close_time_raw", "quote_asset_volume", "num_trades",
    "taker_buy_base_vol", "taker_buy_quote_vol", "ignore",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _month_range(start_ym: str, end_ym: str) -> List[str]:
    y, m = map(int, start_ym.split("-"))
    ey, em = map(int, end_ym.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out


def _normalize_binance_ts(raw_series: pd.Series) -> pd.Series:
    """Normalize Binance timestamps (13-digit ms pre-2025, 16-digit us from 2025+)."""
    vals = pd.to_numeric(raw_series, errors="coerce").astype("int64")
    # 1e14 in ms is year ~5138; in us is year ~1973. So > 1e14 => microseconds.
    is_us = vals > 10**14
    ms = vals.where(~is_us, vals // 1000)
    return pd.to_datetime(ms, unit="ms", utc=True)


def _download_with_checksum(
    sess: requests.Session,
    zip_url: str,
    dest_zip: Path,
    timeout: int = 30,
    max_retries: int = 4,
) -> Dict[str, Any]:
    """Download a Binance Vision zip and verify its .CHECKSUM file if present."""
    if dest_zip.exists() and dest_zip.with_suffix(".zip.meta.json").exists():
        return json.loads(dest_zip.with_suffix(".zip.meta.json").read_text())

    for attempt in range(max_retries):
        try:
            r = sess.get(zip_url, timeout=timeout)
            if r.status_code == 404:
                return {"status": "not_found", "url": zip_url, "http_status": 404}
            r.raise_for_status()
            content = r.content
            actual_sha = _sha256_bytes(content)

            # Fetch .CHECKSUM
            cs_url = zip_url + ".CHECKSUM"
            rcs = sess.get(cs_url, timeout=timeout)
            expected_sha = None
            checksum_verified = False
            if rcs.status_code == 200:
                expected_sha = rcs.text.strip().split()[0].lower()
                if actual_sha.lower() != expected_sha:
                    raise ValueError(
                        f"Checksum mismatch for {zip_url}: expected {expected_sha}, got {actual_sha}"
                    )
                checksum_verified = True

            dest_zip.parent.mkdir(parents=True, exist_ok=True)
            dest_zip.write_bytes(content)
            meta = {
                "status": "ok",
                "url": zip_url,
                "checksum_url": cs_url if expected_sha else None,
                "checksum_verified": checksum_verified,
                "sha256": actual_sha,
                "size_bytes": len(content),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            dest_zip.with_suffix(".zip.meta.json").write_text(json.dumps(meta, indent=2))
            return meta
        except Exception as exc:
            if attempt == max_retries - 1:
                return {"status": "error", "url": zip_url, "error": str(exc)}
            time.sleep(1.5 * (2**attempt))
    return {"status": "error", "url": zip_url, "error": "max_retries"}


def download_binance_klines(
    raw_dir: Path,
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str,
    rate_limit_sec: float = 0.05,
) -> Dict[str, Any]:
    """Download monthly archives plus daily archives for any trailing partial month."""
    sym_dir = raw_dir / symbol / interval
    sym_dir.mkdir(parents=True, exist_ok=True)

    d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Monthly up to month before end_date (or including end_date's month if full/available)
    months = _month_range(d_start.strftime("%Y-%m"), d_end.strftime("%Y-%m"))
    sess = requests.Session()
    sess.headers.update({"User-Agent": "IndonesianCryptoResearch/4.0"})

    manifest_entries = []
    missing_months = []

    for ym in months:
        zip_name = f"{symbol}-{interval}-{ym}.zip"
        url = f"{BASE_URL}/monthly/klines/{symbol}/{interval}/{zip_name}"
        res = _download_with_checksum(sess, url, sym_dir / zip_name)
        manifest_entries.append(res)
        if res["status"] == "not_found":
            missing_months.append(ym)
        time.sleep(rate_limit_sec)

    # For months where monthly archive isn't published yet (e.g. current month 2026-11), fetch daily zips
    for ym in missing_months:
        y, m = map(int, ym.split("-"))
        cur = date(y, m, 1)
        next_m = date(y + (m == 12), (m % 12) + 1, 1)
        last_d = min(d_end, next_m - timedelta(days=1))
        while cur <= last_d:
            if cur >= d_start:
                ds = cur.strftime("%Y-%m-%d")
                zip_name = f"{symbol}-{interval}-{ds}.zip"
                url = f"{BASE_URL}/daily/klines/{symbol}/{interval}/{zip_name}"
                res = _download_with_checksum(sess, url, sym_dir / "daily" / zip_name)
                manifest_entries.append(res)
                time.sleep(rate_limit_sec)
            cur += timedelta(days=1)

    ok_count = sum(1 for e in manifest_entries if e.get("status") == "ok")
    summary = {
        "provider": "Binance Public Data Vision",
        "exchange": "Binance Spot",
        "symbol": symbol,
        "interval": interval,
        "files_ok": ok_count,
        "files_total_attempted": len(manifest_entries),
        "checksums_verified": sum(1 for e in manifest_entries if e.get("checksum_verified")),
        "errors": [e for e in manifest_entries if e.get("status") == "error"],
    }
    (sym_dir / "download_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _interval_to_timedelta(interval: str) -> pd.Timedelta:
    if interval.endswith("m"):
        return pd.Timedelta(minutes=int(interval[:-1]))
    if interval.endswith("h"):
        return pd.Timedelta(hours=int(interval[:-1]))
    if interval.endswith("d"):
        return pd.Timedelta(days=int(interval[:-1]))
    raise ValueError(f"Unsupported Binance interval: {interval}")


def load_binance_klines_df(raw_dir: Path, symbol: str, interval: str) -> pd.DataFrame:
    """Parse all downloaded Binance Vision zips for symbol/interval into a clean UTC DataFrame."""
    sym_dir = raw_dir / symbol / interval
    zips = sorted(sym_dir.glob("*.zip")) + sorted((sym_dir / "daily").glob("*.zip"))
    if not zips:
        return pd.DataFrame()

    frames = []
    for zp in zips:
        with zipfile.ZipFile(zp, "r") as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                with zf.open(name) as f:
                    raw_bytes = f.read()
                first_line = raw_bytes.splitlines()[0].decode("utf-8", errors="ignore")
                has_header = "open_time" in first_line.lower()
                df = pd.read_csv(
                    io.BytesIO(raw_bytes),
                    header=0 if has_header else None,
                    names=None if has_header else KLINE_COLS,
                )
                if has_header:
                    df.columns = KLINE_COLS[: len(df.columns)]
                frames.append(df)

    if not frames:
        return pd.DataFrame()
    full = pd.concat(frames, ignore_index=True)
    bar_td = _interval_to_timedelta(interval)
    full["candle_open_time_utc"] = _normalize_binance_ts(full["open_time_raw"])
    full["candle_close_time_utc"] = _normalize_binance_ts(full["close_time_raw"])
    full["observation_available_time_utc"] = full["candle_open_time_utc"] + bar_td
    full["source_timestamp_utc"] = full["candle_open_time_utc"]
    full["timestamp_utc"] = full["candle_open_time_utc"]
    full["source"] = f"binance_spot_{symbol}_{interval}"
    for col in ["open", "high", "low", "close", "volume", "quote_asset_volume"]:
        full[col] = pd.to_numeric(full[col], errors="coerce")
    full["num_trades"] = pd.to_numeric(full["num_trades"], errors="coerce")
    full = (
        full.dropna(subset=["timestamp_utc", "close"])
        .drop_duplicates(subset=["timestamp_utc"])
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )
    return full[[
        "timestamp_utc", "candle_open_time_utc", "candle_close_time_utc",
        "observation_available_time_utc", "source_timestamp_utc", "source",
        "open", "high", "low", "close", "volume", "quote_asset_volume", "num_trades"
    ]]
