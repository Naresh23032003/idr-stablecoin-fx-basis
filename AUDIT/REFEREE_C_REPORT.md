# Independent Referee C Report (Research Reproducibility Reviewer)

**Focus:** Data provenance, code correctness, reproducibility, dependency management, results traceability, numerical stability, tests, and repository usability.

## 1. Initial Major Concerns (Before Revision)
1. **Stale Metadata & Paths:** `config/econometrics.yaml` listed `iid_residual_bootstrap`, `config/full_research.yaml` hardcoded `/Users/naresh/Library/TinyTeX/...`, and `src/manuscript/latex_tables.py` wrote to `manuscript/tables/` with stale v1 JSON keys.
2. **Unpersisted Robustness Check:** `jisdor_window_and_holm_events.py` printed VWAP shares to stdout without saving a machine-readable JSON artifact.
3. **Raw Data Absence:** `data/raw/` is omitted from Git for size, requiring clear provenance documentation.

## 2. Assessment of Final Revised Version
- **Resolved:** Portable LaTeX binary resolution in `config/full_research.yaml` and `src/pipeline.py`; stale bootstrap label fixed; `src/manuscript/latex_tables.py` generates all 8 `manuscript/tab_*.tex` directly from `results/`; `jisdor_window_vwap.json` persisted; 18 automated unit/integration/consistency tests pass (`pytest -v`); `manuscript/main.pdf` compiles cleanly with zero LaTeX/BibTeX errors or undefined references; `AUDIT/REPRODUCTION_MANIFEST.json` records SHA-256 checksums and exact environment metadata.
- **Remaining Operational Note:** Independent clean-machine reproduction requires either re-acquiring raw data via `python -m src.pipeline acquire` (subject to live exchange API availability) or starting from the tracked `data/processed/` panels and `data/manifests/raw_manifest.json`.

**Referee C Recommendation:** **Acceptable for Submission**.
