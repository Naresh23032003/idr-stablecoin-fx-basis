"""Download and parse official Bank Indonesia JISDOR historical exchange rates."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

BI_JISDOR_URL = "https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/Default.aspx"
FORM_PREFIX = "ctl00$ctl51$g_038b892e_bdf2_4d00_a7cc_2642aa3a7ef8$ctl00$"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_bi_jisdor_excel(
    raw_dir: Path,
    start_date: str = "2021-01-01",
    end_date: str = "2026-11-12",
    force: bool = False,
) -> Dict[str, Any]:
    """Download official BI JISDOR Excel workbook via ASP.NET export postback."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = raw_dir / f"bi_jisdor_{start_date}_{end_date}.xlsx"
    meta_path = raw_dir / f"bi_jisdor_{start_date}_{end_date}_meta.json"

    if xlsx_path.exists() and meta_path.exists() and not force:
        return json.loads(meta_path.read_text())

    dt_from = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    dt_to = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y")

    sess = requests.Session()
    sess.headers.update(HEADERS)

    r_init = sess.get(BI_JISDOR_URL, timeout=30)
    r_init.raise_for_status()
    soup = BeautifulSoup(r_init.text, "lxml")

    form_data = {
        inp.get("name"): inp.get("value", "")
        for inp in soup.find_all("input")
        if inp.get("name")
    }
    post_search = {
        k: v
        for k, v in form_data.items()
        if "Button" not in k and "btn" not in k.lower()
    }
    post_search[FORM_PREFIX + "TextBoxFrom"] = dt_from
    post_search[FORM_PREFIX + "HiddenFieldDateFrom"] = dt_from
    post_search[FORM_PREFIX + "TextBoxDateTo"] = dt_to
    post_search[FORM_PREFIX + "HiddenFieldDateTo"] = dt_to
    post_search[FORM_PREFIX + "ButtonCari"] = "Search"

    r_search = sess.post(BI_JISDOR_URL, data=post_search, timeout=35)
    r_search.raise_for_status()

    psoup = BeautifulSoup(r_search.text, "lxml")
    exp_data = {
        inp.get("name"): inp.get("value", "")
        for inp in psoup.find_all("input")
        if inp.get("name")
    }
    exp_data = {
        k: v
        for k, v in exp_data.items()
        if "Button" not in k and "btn" not in k.lower()
    }
    exp_data["__EVENTTARGET"] = FORM_PREFIX + "ButtonExport"
    exp_data["__EVENTARGUMENT"] = ""
    exp_data[FORM_PREFIX + "TextBoxFrom"] = dt_from
    exp_data[FORM_PREFIX + "HiddenFieldDateFrom"] = dt_from
    exp_data[FORM_PREFIX + "TextBoxDateTo"] = dt_to
    exp_data[FORM_PREFIX + "HiddenFieldDateTo"] = dt_to

    r_exp = sess.post(BI_JISDOR_URL, data=exp_data, timeout=45)
    r_exp.raise_for_status()
    if b"PK" not in r_exp.content[:4]:
        raise RuntimeError(
            f"Unexpected BI JISDOR export payload: status={r_exp.status_code}, "
            f"content_type={r_exp.headers.get('Content-Type')}"
        )

    xlsx_path.write_bytes(r_exp.content)
    meta = {
        "provider": "Bank Indonesia",
        "instrument": "JISDOR",
        "pair": "USD/IDR",
        "source_url": BI_JISDOR_URL,
        "request_params": {"from": dt_from, "to": dt_to, "action": "ButtonExport"},
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(xlsx_path),
        "size_bytes": len(r_exp.content),
        "sha256": _sha256_bytes(r_exp.content),
        "content_type": r_exp.headers.get("Content-Type"),
        "licence_notes": "Official public Bank Indonesia statistical release; attribution required.",
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def parse_bi_jisdor_excel(xlsx_path: Path) -> pd.DataFrame:
    """Parse Bank Indonesia JISDOR Excel file into canonical daily DataFrame."""
    raw_df = pd.read_excel(xlsx_path, header=None)
    # Find header row containing Date / Tanggal
    header_idx = None
    for idx, row in raw_df.iterrows():
        vals = [str(v).strip().lower() for v in row.values if pd.notna(v)]
        if any(v in ("date", "tanggal") for v in vals):
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError(f"Could not locate header row in {xlsx_path}")

    df = raw_df.iloc[header_idx + 1 :].copy()
    df.columns = [str(c).strip() for c in raw_df.iloc[header_idx].values]
    df = df.dropna(how="all")

    # Identify date column and rate column
    date_col = [c for c in df.columns if "date" in c.lower() or "tanggal" in c.lower()][0]
    rate_col = [c for c in df.columns if "rate" in c.lower() or "kurs" in c.lower() or "jisdor" in c.lower()]
    if not rate_col:
        rate_col = [c for c in df.columns if c != date_col]
    rcol = rate_col[0]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
    # Clean strings like "Rp 18,241.00" or numeric values
    vals = (
        df[rcol]
        .astype(str)
        .str.replace("Rp", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    out["jisdor_idr_usd"] = pd.to_numeric(vals, errors="coerce")
    out = out.dropna(subset=["date", "jisdor_idr_usd"]).drop_duplicates(subset=["date"])
    out = out.sort_values("date").reset_index(drop=True)
    return out
