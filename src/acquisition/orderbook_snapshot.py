"""Capture live cross-sectional order-book depth snapshots for Indodax and Binance."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import requests

HEADERS = {"User-Agent": "IndonesianCryptoResearch/4.0"}


def capture_orderbook_snapshots(
    indodax_raw_dir: Path,
    binance_raw_dir: Path,
    indodax_pairs: List[str] = ("btcidr", "usdtidr", "ethidr", "xrpidr", "btcusdt"),
    binance_symbols: List[str] = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "BTCIDR", "USDTIDR"),
) -> Dict[str, Any]:
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_dir_indo = indodax_raw_dir / "orderbook_snapshots"
    snap_dir_bin = binance_raw_dir / "orderbook_snapshots"
    snap_dir_indo.mkdir(parents=True, exist_ok=True)
    snap_dir_bin.mkdir(parents=True, exist_ok=True)

    results = {"captured_at_utc": ts_str, "indodax": {}, "binance": {}}
    sess = requests.Session()
    sess.headers.update(HEADERS)

    # Indodax pairs metadata
    rp = sess.get("https://indodax.com/api/pairs", timeout=15)
    if rp.status_code == 200:
        pfile = snap_dir_indo / f"indodax_pairs_{ts_str}.json"
        pfile.write_bytes(rp.content)
        results["indodax_pairs_sha256"] = hashlib.sha256(rp.content).hexdigest()

    for pair in indodax_pairs:
        r = sess.get(f"https://indodax.com/api/depth/{pair}", timeout=15)
        if r.status_code == 200:
            fp = snap_dir_indo / f"depth_{pair}_{ts_str}.json"
            fp.write_bytes(r.content)
            results["indodax"][pair] = {
                "file": str(fp),
                "sha256": hashlib.sha256(r.content).hexdigest(),
            }

    for sym in binance_symbols:
        r = sess.get("https://api.binance.com/api/v3/depth", params={"symbol": sym, "limit": 100}, timeout=15)
        if r.status_code == 200:
            fp = snap_dir_bin / f"depth_{sym}_{ts_str}.json"
            fp.write_bytes(r.content)
            results["binance"][sym] = {
                "file": str(fp),
                "sha256": hashlib.sha256(r.content).hexdigest(),
            }

    (snap_dir_indo / f"snapshot_manifest_{ts_str}.json").write_text(json.dumps(results, indent=2))
    return results
