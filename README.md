# Where Does the Indonesian Cryptocurrency Premium Come From?

Replication package for *"Where does the Indonesian cryptocurrency premium come from? Currency conversion, the stablecoin--FX basis, and transaction costs"* by Naresh R (BITS Pilani; ORCID: `0009-0000-0735-2066`).

The study covers January 4, 2021 through November 12, 2026 (`n = 1,414` Bank Indonesia JISDOR-synchronized business days across BTC, ETH, and XRP; `N = 616,683` five-minute 24/7 bars; `N = 455,040` 2026 one-minute bars).

## Reproduction

Two explicit pipeline modes are supported:

1. **Processed-data reproduction (clean checkout, no `data/raw/` required):** Uses tracked `data/processed/` panels and `results/tables/orderbook_microstructure_snapshot.csv`, fails early if any required file is missing, and runs all experiments, JISDOR monitoring-window VWAP checks, figures, LaTeX tables, and PDF compilation:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock

# Clean-checkout reproduction from tracked processed panels (master seed: 20261113)
MPLCONFIGDIR=/tmp/matplotlib python -m src.pipeline reproduce-processed --config config/full_research.yaml

# Run automated verification suite
pytest -v
```

2. **Full raw rebuild (requires `data/raw/` or live acquisition):**

```bash
# Acquire raw archives from public APIs (optional if data/raw/ already present)
python -m src.pipeline acquire --config config/full_research.yaml

# Validate raw inputs, rebuild processed panels, and run the complete pipeline
MPLCONFIGDIR=/tmp/matplotlib python -m src.pipeline run-all --mode full-raw --config config/full_research.yaml
```

## Directory layout

- `config/`: YAML configurations (`acquisition.yaml`, `sampling.yaml`, `econometrics.yaml`, `full_research.yaml`).
- `data/manifests/`: SHA-256 verification manifests for all raw exchange and central-bank files.
- `data/processed/`: Cleaned synchronized daily and high-frequency panels (`.csv` and `.csv.gz`). Raw archives are omitted for size and can be re-fetched via `src/acquisition/`.
- `data/source_coverage_matrix.csv`: Coverage and quality diagnostics across all instruments.
- `src/`: Acquisition, calendar alignment, fee reconstruction, order-book slippage, unit-root/cointegration/bootstrap/VECM/Band-TAR/event-window modules, and pipeline CLI.
- `results/tables/`, `results/models/`: Machine-readable empirical outputs.
- `tests/`: Automated unit and consistency tests.
- `docs/`: Data dictionary, methodology notes, regulatory timeline, reproducibility guide, and source register.
- `manuscript/`: Springer Nature (`sn-jnl`) LaTeX source, figures, tables, bibliography, and compiled `main.pdf`.
