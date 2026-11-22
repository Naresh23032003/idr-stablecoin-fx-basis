"""Download USD/USDT and BTC/USD reference data from Coinbase Exchange and Kraken."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import requests

HEADERS = {"User-Agent": "IndonesianCryptoResearch/4.0"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_coinbase_candles(
    raw_dir: Path,
    product: str,
    granularity_sec: int,
    start_date: str,
    end_date: str,
    rate_limit_sec: float = 0.25,
) -> Dict[str, Any]:
    """Download Coinbase Exchange historical candles (max 300 candles per request)."""
    prod_dir = raw_dir / product / f"gran_{granularity_sec}"
    chunks_dir = prod_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    window_sec = 290 * granularity_sec
    sess = requests.Session()
    sess.headers.update(HEADERS)

    cur = dt_start
    idx = 0
    chunks_ok = 0
    total_rows = 0
    errors: List[Dict[str, Any]] = []

    while cur < dt_end:
        nxt = min(dt_end, cur + timedelta(seconds=window_sec))
        cfile = chunks_dir / f"cb_{idx:04d}.json"
        mfile = chunks_dir / f"cb_{idx:04d}.meta.json"
        if cfile.exists() and mfile.exists():
            meta = json.loads(mfile.read_text())
            chunks_ok += 1
            total_rows += meta.get("n_rows", 0)
            cur = nxt
            idx += 1
            continue

        url = f"https://api.exchange.coinbase.com/products/{product}/candles"
        params = {
            "granularity": granularity_sec,
            "start": cur.isoformat().replace("+00:00", "Z"),
            "end": nxt.isoformat().replace("+00:00", "Z"),
        }
        for attempt in range(4):
            try:
                r = sess.get(url, params=params, timeout=20)
                if r.status_code == 429:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                r.raise_for_status()
                data = r.json()
                cfile.write_bytes(r.content)
                meta = {
                    "url": r.url,
                    "n_rows": len(data) if isinstance(data, list) else 0,
                    "sha256": _sha256_bytes(r.content),
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                mfile.write_text(json.dumps(meta, indent=2))
                chunks_ok += 1
                total_rows += meta["n_rows"]
                break
            except Exception as exc:
                if attempt == 3:
                    errors.append({"idx": idx, "start": params["start"], "error": str(exc)})
                else:
                    time.sleep(1.5 * (2**attempt))

        cur = nxt
        idx += 1
        time.sleep(rate_limit_sec)

    summary = {
        "provider": "Coinbase Exchange REST API",
        "product": product,
        "granularity_sec": granularity_sec,
        "chunks_ok": chunks_ok,
        "total_rows": total_rows,
        "errors": errors,
    }
    (prod_dir / "download_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def load_coinbase_df(raw_dir: Path, product: str, granularity_sec: int) -> pd.DataFrame:
    chunks_dir = raw_dir / product / f"gran_{granularity_sec}" / "chunks"
    files = sorted(p for p in chunks_dir.glob("cb_*.json") if not p.name.endswith(".meta.json"))
    rows = []
    for fp in files:
        d = json.loads(fp.read_text())
        if isinstance(d, list):
            rows.extend(d)
    if not rows:
        return pd.DataFrame()
    # Coinbase candle schema: [time, low, high, open, close, volume]
    df = pd.DataFrame(rows, columns=["time_unix", "low", "high", "open", "close", "volume"])
    df["timestamp_utc"] = pd.to_datetime(pd.to_numeric(df["time_unix"], errors="coerce"), unit="s", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return (
        df.dropna(subset=["timestamp_utc", "close"])
        .drop_duplicates(subset=["timestamp_utc"])
        .sort_values("timestamp_utc")
        .reset_index(drop=True)[["timestamp_utc", "open", "high", "low", "close", "volume"]]
    )


def download_kraken_ohlc(
    raw_dir: Path,
    pair: str = "USDTUSD",
    interval_min: int = 1440,
    since_unix: int = 1609459200,
    force: bool = False,
) -> Dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    jpath = raw_dir / f"kraken_{pair}_{interval_min}.json"
    mpath = raw_dir / f"kraken_{pair}_{interval_min}_meta.json"
    if jpath.exists() and mpath.exists() and not force:
        return json.loads(mpath.read_text())

    url = "https://api.kraken.com/0/public/OHLC"
    r = requests.get(url, params={"pair": pair, "interval": interval_min, "since": since_unix}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    jpath.write_bytes(r.content)
    meta = {
        "provider": "Kraken Public REST API",
        "pair": pair,
        "interval_min": interval_min,
        "url": r.url,
        "sha256": _sha256_bytes(r.content),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    mpath.write_text(json.dumps(meta, indent=2))
    return meta


def load_kraken_df(raw_dir: Path, pair: str = "USDTUSD", interval_min: int = 1440) -> pd.DataFrame:
    jpath = raw_dir / f"kraken_{pair}_{interval_min}.json"
    payload = json.loads(jpath.read_text())["result"]
    key = [k for k in payload.keys() if k != "last"][0]
    rows = payload[key]
    df = pd.DataFrame(rows, columns=["time_unix", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["timestamp_utc"] = pd.to_datetime(pd.to_numeric(df["time_unix"], errors="coerce"), unit="s", utc=True)
    for c in ["open", "high", "low", "close", "vwap", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return (
        df.dropna(subset=["timestamp_utc", "close"])
        .drop_duplicates(subset=["timestamp_utc"])
        .sort_values("timestamp_utc")
        .reset_index(drop=True)[["timestamp_utc", "open", "high", "low", "close", "vwap", "volume", "count"]]
    )
