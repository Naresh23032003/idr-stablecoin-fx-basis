# Initial Repository Inventory

**Audit Timestamp:** 2026-11-23T17:43:00+05:30  
**Repository Path:** `/Users/naresh/Desktop/Finance/idr-stablecoin-fx-basis`  
**Remote URL:** `https://github.com/Naresh23032003/idr-stablecoin-fx-basis`  
**Branch:** `main` (tracking `origin/main`)  
**HEAD Commit SHA:** `2fcaefd` (Tag: `v2.0.0-apfm-revision`)  
**Backup Tag Created:** `backup-initial-2fcaefd` (points to `2fcaefd`)  
**Working Tree Status:** Clean (`nothing to commit, working tree clean`)  

## Git History Summary
- `2fcaefd` (`v2.0.0-apfm-revision`): APFM revision: 3-var 5m VECM, companion half-life, block-wild bootstrap, controlled/joint event study, and production fixes
- `7066f8e`: Merge initial remote README
- `e761ce1`: Initial replication package and manuscript for Indonesian crypto stablecoin-FX basis study
- `74d2290`: docs: add README

## Directory & File Inventory

### Configuration (`config/`)
- `config/acquisition.yaml` — API/archive download settings
- `config/econometrics.yaml` — Seed (`20261113`), unit-root, cointegration, bootstrap (`method: null_imposed_vecm_iid_residual_bootstrap` — **stale label**), ECM, Band-TAR, and 10 regulatory event dates
- `config/full_research.yaml` — Master pipeline config; contains machine-specific `latex_binary` and `bibtex_binary` paths (`/Users/naresh/Library/TinyTeX/bin/universal-darwin/...`)
- `config/sampling.yaml` — JISDOR publication regimes (R1–R4), synchronization offsets `[-15, 0, 5, 15]`, tolerance `5` min

### Data (`data/`)
- `data/raw/` — **Absent** in `idr-stablecoin-fx-basis` (omitted from git for size; present in sibling directory `/Users/naresh/Desktop/Finance/indonesian_crypto_research_final/data/raw/`)
- `data/manifests/raw_manifest.json` — SHA-256 manifests for raw files
- `data/source_coverage_matrix.csv` — Instrument coverage summary
- `data/processed/` — 12 processed files:
  - `btc_jisdor_sync_primary.csv`, `eth_jisdor_sync_primary.csv`, `xrp_jisdor_sync_primary.csv`
  - `btc_calendar_days_sensitivity.csv`, `jisdor_schedule_calendar.csv`
  - `btc_5m_panel_2021_2026.csv.gz`, `eth_5m_panel_2021_2026.csv.gz`, `xrp_5m_panel_2021_2026.csv.gz`
  - `binance_vs_indodax_idr_5m.csv.gz`, `btc_1m_2026_panel.csv.gz`
  - `data_quality_diagnostics.json`

### Source Code (`src/`)
- `src/pipeline.py` — End-to-end CLI (`acquire`, `process`, `experiments`, `figures`, `tables`, `compile`, `run-all`)
- `src/experiments_runner.py` — Master experiment runner (EXP-01 to EXP-10)
- `src/acquisition/` — `bi_jisdor.py`, `binance_vision.py`, `coinbase_kraken.py`, `fx_spot.py`, `indodax_history.py`, `orderbook_snapshot.py`, `run_acquisition.py`
- `src/processing/jisdor_calendar.py` — JISDOR schedule calendar builder
- `src/synchronization/aligner.py` — Quality checks, `_asof_window_match`, `build_all_datasets`
- `src/variables/basis.py` — Log basis decomposition and variance identity verification
- `src/econometrics/` — `unit_root.py`, `cointegration.py`, `bootstrap.py`, `ecm.py`, `nonlinear_tar.py`, `structural_breaks.py`
- `src/fees/` — `fee_schedule.py`, `orderbook_economics.py`
- `src/robustness/` — `runner.py`, `jisdor_window_and_holm_events.py`
- `src/visualizations/figures.py` — Generates 8 PDF figures in `manuscript/` and `results/figures/`
- `src/manuscript/latex_tables.py` — Generates 8 LaTeX `.tex` table files in `manuscript/`

### Results (`results/`)
- `results/tables/` — 14 CSV tables (`table1`–`table10`, `table4b`, `historical_fee_reconstruction`, `orderbook_microstructure_snapshot`, `route_specific_execution_costs`)
- `results/models/` — `intraday_and_tar_results.json`, `variance_decomposition.json`, `binance_vs_indodax_idr_summary.json`
- `results/diagnostics/`, `results/figures/`, `results/logs/` — Currently empty

### Tests (`tests/`)
- `tests/test_core_methodology.py`, `tests/test_econometrics.py`, `tests/test_manuscript_consistency.py`, `tests/test_pipeline_and_manuscript.py` (16 tests total; all pass in baseline using sibling `.venv` Python 3.11)

### Manuscript (`manuscript/`)
- `main.tex`, `sn-jnl.cls`, `sn-basic.bst`, `references.bib`
- `sec1_introduction.tex` through `sec8_conclusion.tex`, `app_provenance.tex`, `app_bootstrap_and_fees.tex`
- `tab_*.tex` (8 generated tables), `fig1_*.pdf`–`fig8_*.pdf` (8 figures), compiled `main.pdf`
