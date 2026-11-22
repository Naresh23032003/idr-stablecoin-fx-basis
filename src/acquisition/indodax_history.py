"""Resumable chunked downloader for Indodax TradingView history_v2 API."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import requests

INDODAX_TV_URL = "https://indodax.com/tradingview/history_v2"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_indodax_history(
    raw_dir: Path,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    chunk_days: int = 8,
    rate_limit_sec: float = 0.12,
    max_retries: int = 5,
) -> Dict[str, Any]:
    """Download Indodax OHLCV with checkpointed chunks respecting the 9-day intraday API cap."""
    sym_dir = raw_dir / symbol / f"tf_{timeframe}"
    chunks_dir = sym_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    ts_start = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    ts_end = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86399

    # For 1D, Indodax returns full history in one call; for intraday, chunk <= 8 days (< 9-day server cap)
    step_sec = (ts_end - ts_start + 1) if timeframe == "1D" else chunk_days * 86400

    sess = requests.Session()
    sess.headers.update(HEADERS)

    cur = ts_start
    chunk_idx = 0
    errors: List[Dict[str, Any]] = []
    chunks_ok = 0
    total_bars_raw = 0

    while cur <= ts_end:
        nxt = min(ts_end, cur + step_sec - 1) if timeframe != "1D" else ts_end
        chunk_file = chunks_dir / f"chunk_{chunk_idx:04d}_{cur}_{nxt}.json"
        meta_file = chunks_dir / f"chunk_{chunk_idx:04d}_{cur}_{nxt}.meta.json"

        if chunk_file.exists() and meta_file.exists():
            meta = json.loads(meta_file.read_text())
            chunks_ok += 1
            total_bars_raw += meta.get("n_rows", 0)
            cur = nxt + 1
            chunk_idx += 1
            continue

        params = {"symbol": symbol, "tf": timeframe, "from": cur, "to": nxt}
        success = False
        for attempt in range(max_retries):
            try:
                r = sess.get(INDODAX_TV_URL, params=params, timeout=25)
                r.raise_for_status()
                payload = r.json()
                if not isinstance(payload, list):
                    raise ValueError(f"Unexpected payload type: {str(payload)[:120]}")
                raw_bytes = r.content
                chunk_file.write_bytes(raw_bytes)
                meta = {
                    "url": r.url,
                    "params": params,
                    "n_rows": len(payload),
                    "first_ts": payload[0]["Time"] if payload else None,
                    "last_ts": payload[-1]["Time"] if payload else None,
                    "sha256": _sha256_bytes(raw_bytes),
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                meta_file.write_text(json.dumps(meta, indent=2))
                chunks_ok += 1
                total_bars_raw += len(payload)
                success = True
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    errors.append({"chunk": chunk_idx, "from": cur, "to": nxt, "error": str(exc)})
                else:
                    time.sleep(1.5 * (2**attempt))

        if not success:
            break
        cur = nxt + 1
        chunk_idx += 1
        time.sleep(rate_limit_sec)

    summary = {
        "provider": "Indodax Official TradingView History API",
        "exchange": "Indodax",
        "symbol": symbol,
        "timeframe": timeframe,
        "chunks_ok": chunks_ok,
        "total_bars_raw": total_bars_raw,
        "errors": errors,
    }
    (sym_dir / "download_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def load_indodax_df(raw_dir: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    """Assemble and deduplicate all raw Indodax JSON chunks into a UTC DataFrame."""
    chunks_dir = raw_dir / symbol / f"tf_{timeframe}" / "chunks"
    files = sorted(p for p in chunks_dir.glob("chunk_*.json") if not p.name.endswith(".meta.json"))
    rows = []
    for fp in files:
        data = json.loads(fp.read_text())
        if data:
            rows.extend(data)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp_utc"] = pd.to_datetime(pd.to_numeric(df["Time"], errors="coerce"), unit="s", utc=True)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col.lower()] = pd.to_numeric(df[col], errors="coerce")
    df = (
        df.dropna(subset=["timestamp_utc", "close"])
        .drop_duplicates(subset=["timestamp_utc"])
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )
    return df[["timestamp_utc", "open", "high", "low", "close", "volume"]]
