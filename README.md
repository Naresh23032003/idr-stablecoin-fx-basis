# Where Does the Indonesian Cryptocurrency Premium Come From?

Replication package for *"Where does the Indonesian cryptocurrency premium come from? Currency conversion, the stablecoin--FX basis, and transaction costs"* by Naresh R (BITS Pilani; ORCID: `0009-0000-0735-2066`).

The study covers January 4, 2021 through November 12, 2026 (`n = 1,414` Bank Indonesia JISDOR-synchronized business days across BTC, ETH, and XRP; `N = 616,683` five-minute 24/7 bars; `N = 455,040` 2026 one-minute bars).

## Reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock

# Run full empirical pipeline (master PRNG seed: 20261113)
MPLCONFIGDIR=/tmp/matplotlib python -m src.pipeline run-all --config config/full_research.yaml

# Run JISDOR monitoring-window VWAP/TWAP check and Holm-adjusted event-window tests
python src/robustness/jisdor_window_and_holm_events.py

# Run unit tests
pytest -v
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
