# Independent Reproducibility Guide

## Environment Setup
```bash
cd /Users/naresh/Desktop/Finance/indonesian_crypto_research_final
python3.11 -m venv .venv
source .venv/bin/activate
pip install --no-build-isolation --no-deps -e .
# Or install exact versions:
pip install -r requirements.lock
```

## Pipeline Commands (`src/pipeline.py`)
- Verify saved raw files, rebuild all synchronized datasets, run all econometric/robustness tests, generate all 8 PDF/PNG figures and 7 LaTeX tables, and compile `manuscript/main.pdf`:
  ```bash
  MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m src.pipeline run-all --config config/full_research.yaml
  ```
- Re-acquire live raw data from official APIs/archives (requires internet access; existing manifests are validated if `run_acquisition: false`):
  ```bash
  .venv/bin/python -m src.pipeline acquire --config config/full_research.yaml
  ```
- Execute full verification test suite:
  ```bash
  .venv/bin/pytest -v
  ```

## Determinism & Provenance
- Master PRNG seed: `20261113` (`config/full_research.yaml` & `config/econometrics.yaml`).
- Every raw file has SHA-256 hashes recorded in `data/raw/*_manifest.json` and `release/sha256_manifest.txt`.
- Every manuscript figure and LaTeX table in `manuscript/figures/` and `manuscript/tables/` is programmatically generated from `data/processed/` and `results/`.
