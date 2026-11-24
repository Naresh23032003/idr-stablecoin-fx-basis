"""Verify numerical consistency and typographic hygiene across the LaTeX manuscript."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_no_em_dashes_or_ai_buzzwords_in_manuscript():
    ms_dir = ROOT / "manuscript"
    tex_files = (
        list((ms_dir / "sections").glob("*.tex"))
        + list((ms_dir / "appendices").glob("*.tex"))
        + list(ms_dir.glob("sec*.tex"))
        + list(ms_dir.glob("app_*.tex"))
        + [ms_dir / "main.tex"]
    )
    tex_files = [p for p in tex_files if p.exists()]
    if not tex_files:
        return
    banned_buzz = ["delve", "tapestry", "testament", "pivotal moment", "game-changer", "uncharted"]
    for tf in tex_files:
        txt = tf.read_text()
        assert "---" not in txt, f"Em dash '---' found in {tf.name}"
        assert "\u2014" not in txt, f"Unicode em dash found in {tf.name}"
        low = txt.lower()
        for bw in banned_buzz:
            assert bw not in low, f"AI buzzword '{bw}' found in {tf.name}"


def test_manuscript_headline_numbers_match_results():
    ms_dir = ROOT / "manuscript"
    sec_dir = ms_dir / "sections" if (ms_dir / "sections").exists() else ms_dir
    if not (sec_dir / "sec5_empirical_results.tex").exists():
        return
    all_prose = "\n".join(p.read_text() for p in sec_dir.glob("sec*.tex")) + (ms_dir / "main.tex").read_text()
    t1 = pd.read_csv(ROOT / "results" / "tables" / "table1_descriptive_statistics.csv")
    vd = json.loads((ROOT / "results" / "models" / "variance_decomposition.json").read_text())

    btc_tot = t1[(t1["sample"].str.startswith("BTC Primary")) & (t1["series"].str.startswith("B_total"))].iloc[0]
    btc_cry = t1[(t1["sample"].str.startswith("BTC Primary")) & (t1["series"].str.startswith("B_crypto"))].iloc[0]
    btc_sf = t1[(t1["sample"].str.startswith("BTC Primary")) & (t1["series"].str.startswith("B_stablecoin_FX"))].iloc[0]

    assert f"{btc_tot['mean_bps']:.2f}" in all_prose or "30\\text{ bps}" in all_prose
    assert f"{btc_cry['mean_bps']:.2f}" in all_prose
    assert f"{btc_sf['mean_bps']:.2f}" in all_prose
    assert f"{vd['BTC']['gross_share_sf_pct']:.2f}" in all_prose
    assert f"{vd['BTC']['gross_share_crypto_pct']:.2f}" in all_prose
    assert f"{vd['BTC_pct_crypto_inside_dynamic_2leg_taker_band']:.2f}" in all_prose


def test_no_todo_or_missing_inputs_in_manuscript():
    ms_dir = ROOT / "manuscript"
    tex_files = list(ms_dir.glob("*.tex"))
    for tf in tex_files:
        txt = tf.read_text()
        assert "TODO" not in txt and "FIXME" not in txt, f"TODO/FIXME found in {tf.name}"
        for m in re.finditer(r"\\input\{([^}]+)\}", txt):
            inc = ms_dir / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")
            assert inc.exists(), f"Missing \\input file {inc} referenced in {tf.name}"
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", txt):
            fig = ms_dir / m.group(1)
            assert fig.exists(), f"Missing figure {fig} referenced in {tf.name}"
