"""Cross-sectional order-book spread, depth, and VWAP slippage analysis from live depth snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd


def compute_book_metrics(
    bids: List[List[Any]],
    asks: List[List[Any]],
    trade_sizes_usd: List[float] = (1_000.0, 10_000.0, 50_000.0, 100_000.0),
    fx_idr_per_usd: float = 18_200.0,
    is_idr_quoted: bool = True,
) -> Dict[str, Any]:
    """Compute top-of-book spread, cumulative depth, and VWAP slippage at specified USD notional sizes."""
    b_levels = [(float(p), float(q)) for p, q in bids]
    a_levels = [(float(p), float(q)) for p, q in asks]
    if not b_levels or not a_levels:
        return {"status": "EMPTY_BOOK"}

    best_bid = b_levels[0][0]
    best_ask = a_levels[0][0]
    mid = 0.5 * (best_bid + best_ask)
    spread_bps = ((best_ask - best_bid) / mid) * 10_000.0

    def _vwap_slip(levels, is_ask: bool, target_usd: float) -> float:
        target_quote = target_usd * fx_idr_per_usd if is_idr_quoted else target_usd
        rem_q = target_quote
        cost_q = 0.0
        qty_base = 0.0
        for px, qty in levels:
            lvl_q = px * qty
            take_q = min(rem_q, lvl_q)
            qty_base += take_q / px
            cost_q += take_q
            rem_q -= take_q
            if rem_q <= 1e-6:
                break
        if rem_q > 1e-3 or qty_base == 0:
            return float("nan")
        vwap = cost_q / qty_base
        return ((vwap - mid) / mid) * 10_000.0 if is_ask else ((mid - vwap) / mid) * 10_000.0

    bid_depth_usd = sum(p * q for p, q in b_levels) / (fx_idr_per_usd if is_idr_quoted else 1.0)
    ask_depth_usd = sum(p * q for p, q in a_levels) / (fx_idr_per_usd if is_idr_quoted else 1.0)

    out = {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        "top_spread_bps": round(spread_bps, 4),
        "bid_levels": len(b_levels),
        "ask_levels": len(a_levels),
        "visible_bid_depth_usd": round(bid_depth_usd, 2),
        "visible_ask_depth_usd": round(ask_depth_usd, 2),
    }
    for sz in trade_sizes_usd:
        tag = int(sz // 1000)
        sb = _vwap_slip(b_levels, False, sz)
        sa = _vwap_slip(a_levels, True, sz)
        out[f"slip_buy_{tag}k_bps"] = round(sa, 4) if pd.notna(sa) else None
        out[f"slip_sell_{tag}k_bps"] = round(sb, 4) if pd.notna(sb) else None
        out[f"roundtrip_spread_slip_{tag}k_bps"] = round(sa + sb, 4) if (pd.notna(sa) and pd.notna(sb)) else None
    return out


def analyze_saved_orderbook_snapshots(raw_dir: Path, fx_idr_per_usd: float = 18_241.0) -> pd.DataFrame:
    rows = []
    indo_snaps = sorted((raw_dir / "indodax" / "orderbook_snapshots").glob("depth_*.json"))
    bin_snaps = sorted((raw_dir / "binance" / "orderbook_snapshots").glob("depth_*.json"))

    for fp in indo_snaps:
        pair = fp.stem.split("_")[1]
        d = json.loads(fp.read_text())
        is_idr = pair.endswith("idr")
        m = compute_book_metrics(d.get("buy", []), d.get("sell", []), fx_idr_per_usd=fx_idr_per_usd, is_idr_quoted=is_idr)
        rows.append({"exchange": "Indodax", "pair": pair.upper(), "snapshot_file": fp.name, **m})

    for fp in bin_snaps:
        sym = fp.stem.split("_")[1]
        d = json.loads(fp.read_text())
        is_idr = sym.endswith("IDR")
        m = compute_book_metrics(d.get("bids", []), d.get("asks", []), fx_idr_per_usd=fx_idr_per_usd, is_idr_quoted=is_idr)
        rows.append({"exchange": "Binance", "pair": sym, "snapshot_file": fp.name, **m})

    return pd.DataFrame(rows)
