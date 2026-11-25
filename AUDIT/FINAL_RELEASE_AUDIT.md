# Final APFM Release Audit Report

**Repository:** `https://github.com/Naresh23032003/idr-stablecoin-fx-basis`
**Audit Date:** 2026-11-25
**Python Clean Environment:** Python 3.11.13 (`/tmp/apfm_fresh_venv`, installed cleanly from `requirements.lock`)
**LaTeX Toolchain:** TinyTeX `pdflatex` + `bibtex` (`LaTeX2e <2026-06-01>`)
**Final Verdict:** **READY FOR SUBMISSION**

---

## 1. Executive Summary

An independent, end-to-end release audit and clean-environment reproduction was executed on the repository from a clean checkout without `data/raw/`. Every empirical table, model JSON, diagnostic artifact, figure, LaTeX table, and compiled PDF was regenerated from tracked `data/processed/` inputs via the documented single-command workflow (`python -m src.pipeline reproduce-processed --config config/full_research.yaml`), producing zero numerical drift relative to the pre-release baseline, 22/22 passing automated tests, and a 38-page Springer `sn-jnl` PDF with zero LaTeX errors, zero undefined references or citations, and zero overfull hboxes.

---

## 2. Item-by-Item Release Audit Checklist

| # | Audit Dimension | Status | Evidence & Notes |
|---|---|---|---|
| 1 | **Git & Repository Cleanliness** | `PASS` | Verified clean branch `main` (backup tag `backup-initial-2fcaefd` preserved), removed stray untracked `AUDIT.zip`, added `*.egg-info/` to `.gitignore`, zero absolute machine paths in `requirements.lock` (fixed `-e /Users/...` to `-e .`). |
| 2 | **Mandatory Humanizer Editorial Review** | `PASS` | Executed installed `humanizer` v4.0.0 (and checked v2.1.1) across all 11 manuscript `.tex` files; removed AI vocabulary/fillers, formulaic openings, decorative inline boldface, and redundant `rather than` contrasts; verified zero em dashes (`---` or Unicode `—`); second-pass review confirmed 100% preservation of numbers, equations, citations, and qualifications. Recorded in `AUDIT/HUMANIZER_REVIEW.md` and `AUDIT/manuscript_humanizer.diff`. |
| 3 | **Dependency Portability (`requirements.lock`)** | `PASS` | Replaced machine-specific editable path with `-e .`; installed cleanly into brand-new Python 3.11.13 virtual environment (`/tmp/apfm_fresh_venv`) with `pip install -r requirements.lock` (exit code 0, all 49 pinned packages + `indonesian-crypto-research==4.0.0`). |
| 4 | **Clean-Checkout Processed-Data Reproduction** | `PASS` | Verified `data/raw/` absent; executed `python -m src.pipeline reproduce-processed --config config/full_research.yaml` (without `--skip-compile`) in the brand-new Python 3.11.13 venv. Exited with code 0; regenerated all tables, models, diagnostics, 8 figures, 8 LaTeX tables, and `manuscript/main.pdf` with zero numerical drift across every `results/` CSV/JSON. |
| 5 | **Full Raw-Data Rebuild (`--mode full-raw`)** | `NOT VERIFIED` | `data/raw/` is intentionally excluded from Git (multi-gigabyte upstream exchange archives) and listed in `.gitignore`. Code-path fail-early validation (missing raw inputs / checksum verification) is implemented in `src/pipeline.py` and covered by unit/integration tests; end-to-end live network re-download was not executed during this release freeze. Upstream raw provenance hashes remain preserved in `data/manifests/`. |
| 6 | **Automated Test Suite (`pytest -v`)** | `PASS` | `22 passed, 0 failed` in `7.80s` inside the fresh Python 3.11.13 venv (`results/logs/pytest_final.txt`), including look-ahead rejection, JISDOR calendar transitions, fee arithmetic, sequential bootstrap, eigenmode spectral identity, independent 6-regime HAC Wald reconstruction, no-em-dash/buzzword gate, headline number match, and clean-checkout reproduction without `data/raw/`. |
| 7 | **Timestamp Alignment & No-Look-Ahead Protocol** | `PASS` | Backward matching strictly on `observation_available_time_utc = open_time + dt` (`0.0 s` lag to configured 4-regime schedule: 62d `03:00`, 280d `08:15`, 920d `09:15`, 152d `08:15 UTC`). Regression test `test_rejects_forward_open_time_lookahead_matching` enforces no return to open-time/forward matching. `+/-60m` pandemic-window sensitivity holds (`B_crypto` in `[-0.92, -0.50] bps`, s-FX share in `[82.76%, 84.09%]`, Trace RA in `[150.06, 150.50]`). |
| 8 | **Deterministic VECM Specification (`co` vs. `ci`/`lo`)** | `PASS` | Unified on `co` (`H1(r)`, `det_order=0`) across code, tables, and manuscript; 15-specification lag (`k = 2..6`) and deterministic (`ci`, `co`, `lo`) sensitivity confirms `r = 1` across all 15 models (`Trace_RA = 49.43` to `198.76`, `p_global in [0.124, 0.328]`). |
| 9 | **Daily Sequential Block-Wild Bootstrap (`B = 9,999`)** | `PASS` | Null-imposed restricted-VECM block-wild bootstrap (`B = 9,999`, `b = 6`, deterministic `SeedSequence`) confirms BTC-JISDOR `p(r=0) = 0.0001`, `p(r<=1) = 0.7028`; BTC-USDT `p(r=0) = 0.0001`, `p(r<=1) = 0.7201`; USDT/IDR-JISDOR `p(r=0) = 0.0008`, `p(r<=1) = 0.8108`. Monte Carlo validation (`n_MC = 1,000, B = 299, 0 failures`) accurately disclosed (`7.1%` size at `T = 100`, `8.7%` power at `T = 25`, `4.7%` size / `100.0%` power at `T = 500`). |
| 10 | **High-Frequency 5m Sequential Bootstrap & Block Sensitivity** | `PASS` | 3-variable 5m VECM (`T_eff = 616,677`, `L = 12`, `B = 499`, `0` failures): `p(r=0) = 0.0020`, `p(r<=1) = 0.6420`, `p(r<=2) = 0.7000`. Block-length sensitivity across `b in {14, 28, 56, 112}` (`B = 499` each, `0` failures) confirms rank `r = 1` invariant (`results/diagnostics/bootstrap_5m_block_sensitivity.csv`). |
| 11 | **Half-Life Reconciliation & Eigenmode Decomposition** | `PASS` | Normalization-invariant eigenmode projection (`compute_vecm_eigenmode_decomposition`, reconstruction error `6.61e-15`) reconciles fast local IRF half-life (`1.13` bars; `53.0%` fast transient modes), scalar benchmark (`12.09` bars), and companion slowest-mode half-life (`25.08` bars; `47.0%` slow mode). |
| 12 | **HAC Bandwidth Sensitivity** | `PASS` | Binance `BTC/USDT` weak exogeneity (`p = 0.4179` at `L = 12`) holds across `L in {12, 24, 27, 48, 144, 288}` (`p in [0.413, 0.425]`, `results/diagnostics/hac_bandwidth_sensitivity.csv`). |
| 13 | **6-Regime Pooled HAC Interaction Wald Test** | `PASS` | Tracked in `src/econometrics/structural_breaks.py:estimate_regime_stability_and_wald`, independently reconstructed in `test_regime_stability_wald_independent_reconstruction`: `chi2(5) = 2.356`, `p = 0.7980`. Manuscript explicitly scopes this test to equality of `alpha_local` conditional on full-sample `beta`, not comprehensive full-VECM stability. |
| 14 | **CFX Event Study & Placebo Qualification** | `PASS` | Under controlled `+/-30d` HAC + 20-test Holm adjustment, only Nov 1, 2024 CFX/KKI launch survives on `B_sFX` (`+18.19 bps`, `p_Holm = 0.0077`). Because 2/3 placebo dates also reject on persistent `B_sFX`, the manuscript explicitly qualifies this as a non-causal descriptive association. |
| 15 | **Route B vs. Route A Fee Containment & LOB Snapshot Scope** | `PASS` | Headline containment correctly foregrounds cross-venue 3-leg Route B (`99.01%`) alongside tighter domestic 2-leg Route A (`98.30%`, sensitivity `[97.24%, 98.59%]`). Single-day Nov 13, 2026 LOB depth snapshot is explicitly distinguished from 5-year historical statutory schedules throughout. |
| 16 | **Market Scope & Multi-Venue Disclosure** | `PASS` | Historical pre-November 2025 claims are explicitly scoped to Indodax; 349-day direct Binance IDR overlap (`N = 100,362` 5m bars: `-0.19 bps` BTC/IDR, `-2.11 bps` USDT/IDR) is kept distinct; Tokocrypto, Pintu, and Reku exclusions are documented in Appendix A. |
| 17 | **Claim-to-Code Traceability** | `PASS` | All 15 central empirical claims traced in both `AUDIT/CLAIM_TO_CODE_MAP.md` and `AUDIT/CLAIM_TO_CODE_MAP.csv` to exact source files, functions, inputs, and outputs. |
| 18 | **LaTeX Compilation & Log Quality Gate** | `PASS` | Compiled `manuscript/main.pdf` (38 pages, `995,011` bytes) via `pdflatex` + `bibtex` + `pdflatex` x2: **0 LaTeX errors, 0 undefined citations/references, 0 overfull hboxes** (fixed prior 29.8pt overfull hbox in `tab_vecm_ecm.tex` via `src/manuscript/latex_tables.py`). |
| 19 | **Page-by-Page Visual PDF Inspection** | `PASS` | Rendered all 38 pages of `manuscript/main.pdf` via `pdftoppm` and visually inspected all 38 pages across 4 contact sheets: zero clipped tables, zero margin overflow, zero overlapping figures, zero broken equations, zero blank pages, clean Springer `sn-jnl` typography and bibliography. |
| 20 | **Final Release Freeze, Manifest & Archive Verification** | `PASS` | Final HEAD committed cleanly, `AUDIT/REPRODUCTION_MANIFEST.json` regenerated against final HEAD with verified SHA-256 checksums, `release/APFM_FINAL_SUBMISSION/` and `release/APFM_FINAL_SUBMISSION.zip` built, extract-tested in `/tmp/verify_extract/`, all manifest checksums verified, and extracted `main.pdf` confirmed byte-identical to `manuscript/main.pdf`. |

---

## 3. Non-Blocking Disclosed Limitations

1. **Raw-data rebuild exclusion:** `data/raw/` is excluded from version control due to archive size; independent verification from a clean Git checkout reproduces all empirical results, tables, figures, and the compiled PDF from tracked `data/processed/` datasets (`reproduce-processed` mode), while raw upstream hashes are preserved in `data/manifests/`.
2. **Historical single-exchange scope (pre-November 2025):** Multi-year historical series prior to Binance's November 29, 2025 native IDR launch rest on Indodax alone (Tokocrypto, Pintu, and Reku public endpoints lacked multi-year historical klines).
3. **Point-in-time LOB depth:** Order-book slippage estimates reflect a single November 13, 2026 live snapshot rather than a five-year L2 replay.
4. **Partially verified 2022-2024 Indodax fee tier transition:** Bracketed via sensitivity bounds (`[97.24%, 98.59%]` Route A containment).
5. **Ad-hoc JISDOR operational notices:** Bank Indonesia does not publish a machine-readable calendar of temporary pandemic/Ramadan schedule exceptions; `+/-60m` schedule sensitivity confirms all core findings are invariant.
6. **Non-causal event-study inference:** Persistent level shifts in `B_sFX` trigger placebo-date rejections, so the `+18.19 bps` post-CFX shift is reported strictly as a descriptive association.

---

## 4. Final Decision

**READY FOR SUBMISSION** to *Asia-Pacific Financial Markets (APFM)*.
