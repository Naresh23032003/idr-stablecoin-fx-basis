"""Download continuous spot FX benchmarks (Yahoo Finance IDR=X, EURUSD=X, Frankfurter ECB)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_yahoo_fx(
    raw_dir: Path,
    symbol: str,
    start_date: str = "2021-01-01",
    end_date: str = "2026-11-13",
    force: bool = False,
) -> Dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("=", "_").lower()
    json_path = raw_dir / f"yahoo_{safe}_{start_date}_{end_date}.json"
    meta_path = raw_dir / f"yahoo_{safe}_{start_date}_{end_date}_meta.json"
    if json_path.exists() and meta_path.exists() and not force:
        return json.loads(meta_path.read_text())

    p1 = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": p1, "period2": p2, "interval": "1d", "events": "history"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=25)
    r.raise_for_status()
    json_path.write_bytes(r.content)
    meta = {
        "provider": "Yahoo Finance",
        "instrument": symbol,
        "source_url": r.url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(json_path),
        "size_bytes": len(r.content),
        "sha256": _sha256_bytes(r.content),
        "licence_notes": "Aggregator composite indicative FX close for research cross-validation.",
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def parse_yahoo_fx(json_path: Path, col_name: str) -> pd.DataFrame:
    payload = json.loads(json_path.read_text())
    res = payload["chart"]["result"][0]
    ts = res["timestamp"]
    quote = res["indicators"]["quote"][0]
    df = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(ts, unit="s", utc=True),
            col_name: pd.to_numeric(quote["close"], errors="coerce"),
            f"{col_name}_open": pd.to_numeric(quote["open"], errors="coerce"),
            f"{col_name}_high": pd.to_numeric(quote["high"], errors="coerce"),
            f"{col_name}_low": pd.to_numeric(quote["low"], errors="coerce"),
        }
    )
    df["date"] = df["timestamp_utc"].dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=[col_name]).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def download_frankfurter_fx(
    raw_dir: Path,
    start_date: str = "2021-01-01",
    end_date: str = "2026-11-12",
    base: str = "USD",
    quote: str = "IDR",
    force: bool = False,
) -> Dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    json_path = raw_dir / f"frankfurter_{base}_{quote}_{start_date}_{end_date}.json"
    meta_path = raw_dir / f"frankfurter_{base}_{quote}_{start_date}_{end_date}_meta.json"
    if json_path.exists() and meta_path.exists() and not force:
        return json.loads(meta_path.read_text())

    url = f"https://api.frankfurter.app/{start_date}..{end_date}"
    r = requests.get(url, params={"from": base, "to": quote}, headers=HEADERS, timeout=25)
    r.raise_for_status()
    json_path.write_bytes(r.content)
    meta = {
        "provider": "Frankfurter (European Central Bank Reference Rates)",
        "instrument": f"{base}/{quote}",
        "source_url": r.url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(json_path),
        "size_bytes": len(r.content),
        "sha256": _sha256_bytes(r.content),
        "licence_notes": "ECB official daily reference rate (~16:00 CET = 15:00 UTC / 14:00 UTC DST).",
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def parse_frankfurter_fx(json_path: Path, quote: str = "IDR") -> pd.DataFrame:
    payload = json.loads(json_path.read_text())
    rates = payload["rates"]
    rows = [{"date": d, "ecb_idr_usd": float(v[quote])} for d, v in sorted(rates.items()) if quote in v]
    return pd.DataFrame(rows)
