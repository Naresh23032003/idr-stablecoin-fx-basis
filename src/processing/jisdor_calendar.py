"""Construct historical Bank Indonesia JISDOR publication schedule calendar."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import yaml


def build_jisdor_schedule_calendar(
    sampling_cfg_path: Path,
    start_date: str = "2021-01-01",
    end_date: str = "2026-11-12",
    jisdor_dates: set[str] | None = None,
) -> pd.DataFrame:
    """Build daily calendar recording active JISDOR publication time (WIB & UTC) and regime."""
    cfg = yaml.safe_load(sampling_cfg_path.read_text())["sampling"]
    regimes = cfg["jisdor_schedule"]

    d0 = datetime.strptime(start_date, "%Y-%m-%d").date()
    d1 = datetime.strptime(end_date, "%Y-%m-%d").date()

    rows: List[Dict[str, Any]] = []
    cur = d0
    while cur <= d1:
        ds = cur.strftime("%Y-%m-%d")
        matched = None
        for reg in regimes:
            if reg["start_date"] <= ds <= reg["end_date"]:
                matched = reg
                break
        if matched is None:
            raise ValueError(f"No JISDOR regime matched for {ds}")

        is_wknd = cur.weekday() >= 5
        has_jisdor = (ds in jisdor_dates) if jisdor_dates is not None else (not is_wknd)

        pub_utc_dt = pd.Timestamp(f"{ds} {matched['pub_time_utc']}", tz="UTC")
        pub_wib_dt = pd.Timestamp(f"{ds} {matched['pub_time_wib']}", tz="Asia/Jakarta")

        rows.append(
            {
                "date": ds,
                "day_of_week": cur.strftime("%A"),
                "is_weekend": is_wknd,
                "is_jisdor_published": bool(has_jisdor),
                "regime": matched["regime"],
                "monitoring_window_wib": matched["monitoring_window_wib"],
                "pub_time_wib": matched["pub_time_wib"],
                "pub_time_utc": matched["pub_time_utc"],
                "pub_timestamp_utc": pub_utc_dt.isoformat(),
                "pub_timestamp_wib": pub_wib_dt.isoformat(),
                "authority": matched["authority"],
            }
        )
        cur += timedelta(days=1)

    return pd.DataFrame(rows)
