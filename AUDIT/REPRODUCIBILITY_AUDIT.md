# Reproducibility and Software Engineering Audit

**Date:** 2026-11-24  

## 1. Defects Identified & Fixed

1. **Machine-Specific Paths (`config/full_research.yaml`, `src/pipeline.py`):**
   - Replaced hardcoded `/Users/naresh/Library/TinyTeX/bin/universal-darwin/{pdflatex,bibtex}` with portable `"pdflatex"` / `"bibtex"` plus `shutil.which` and fallback in `src/pipeline.py`.
2. **Stale Bootstrap Label (`config/econometrics.yaml`):**
   - Updated `method: "null_imposed_vecm_iid_residual_bootstrap"` to `method: "null_imposed_restricted_vecm_block_wild_bootstrap"` and added explicit `deterministic_spec: "co"`.
3. **Table Generation Target & Stale Keys (`src/manuscript/latex_tables.py`):**
   - Fixed output directory from `manuscript/tables/` to `manuscript/` so `main.tex` `\input{tab_*.tex}` always consumes freshly generated tables.
   - Updated `tab_vecm_ecm.tex` keys from v1 (`hf_vecm_all_5m`) to v2 (`hf_vecm_3var_all_5m`, `hf_vecm_3var_active_5m`, `hf_vecm_indep_fx_349d_3var`) and added sequential bootstrap p-values and eigenmode half-life notes.
4. **Unpersisted Robustness Output (`src/robustness/jisdor_window_and_holm_events.py`):**
   - Persisted JISDOR monitoring-window VWAP/TWAP results to `results/models/jisdor_window_vwap.json` so `tab_robustness.tex` reads them directly.
5. **Raw Data Provenance:**
   - `data/raw/` is excluded from Git via `.gitignore` for archive size; all raw files are SHA-256 checksummed in `data/manifests/raw_manifest.json` and re-acquirable via `python -m src.pipeline acquire --config config/full_research.yaml`.

## 2. Clean-Machine Reproduction Command

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
MPLCONFIGDIR=/tmp/mpl python -m src.pipeline run-all --config config/full_research.yaml
python src/robustness/jisdor_window_and_holm_events.py
pytest -v
```
