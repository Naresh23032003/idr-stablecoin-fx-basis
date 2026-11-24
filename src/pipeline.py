"""Master reproducible research pipeline CLI with explicit processed-data and full-raw modes."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import List

import yaml

from src.acquisition.run_acquisition import run_all_acquisition
from src.experiments_runner import run_all_experiments
from src.manuscript.latex_tables import generate_all_latex_tables
from src.robustness.jisdor_window_and_holm_events import main as run_jisdor_window_vwap
from src.synchronization.aligner import build_all_datasets
from src.visualizations.figures import generate_all_figures


REQUIRED_PROCESSED_FILES: List[str] = [
    "data/processed/btc_jisdor_sync_primary.csv",
    "data/processed/eth_jisdor_sync_primary.csv",
    "data/processed/xrp_jisdor_sync_primary.csv",
    "data/processed/btc_calendar_days_sensitivity.csv",
    "data/processed/jisdor_schedule_calendar.csv",
    "data/processed/btc_5m_panel_2021_2026.csv.gz",
    "data/processed/binance_vs_indodax_idr_5m.csv.gz",
    "data/source_coverage_matrix.csv",
    "results/tables/orderbook_microstructure_snapshot.csv",
]


def validate_processed_inputs(root: Path) -> None:
    """Fail early with an actionable error if any required processed input is missing or empty."""
    missing = []
    for rel in REQUIRED_PROCESSED_FILES:
        p = root / rel
        if not p.exists() or p.stat().st_size == 0:
            missing.append(rel)
    if missing:
        raise FileNotFoundError(
            "Processed-data reproduction cannot proceed; missing or empty required files:\n  - "
            + "\n  - ".join(missing)
            + "\nRestore tracked data/processed/ files or run with `--mode full-raw`."
        )


def validate_raw_inputs(root: Path) -> None:
    """Fail early if data/raw/ or raw manifest is missing before full raw rebuild."""
    raw_dir = root / "data" / "raw"
    manifest_path = root / "data" / "manifests" / "raw_manifest.json"
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_dir}. "
            "Run `python -m src.pipeline acquire` first, or use `--mode processed` for tracked processed-data reproduction."
        )
    if not manifest_path.exists():
        raise FileNotFoundError(f"Raw manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    if not manifest:
        raise ValueError(f"Raw manifest is empty: {manifest_path}")
    # Verify core raw directories exist
    for sub in ("bi_jisdor", "binance", "indodax", "coinbase", "fx_spot"):
        if not (raw_dir / sub).exists():
            raise FileNotFoundError(
                f"Required raw source directory missing: {raw_dir / sub}. "
                "Re-acquire raw data or run `--mode processed`."
            )


def compile_manuscript(root: Path, latex_bin: str, bibtex_bin: str) -> None:
    ms_dir = root / "manuscript"
    ltx = shutil.which(latex_bin) or str(Path.home() / "Library/TinyTeX/bin/universal-darwin/pdflatex")
    bib = shutil.which(bibtex_bin) or str(Path.home() / "Library/TinyTeX/bin/universal-darwin/bibtex")
    for cmd in [
        [ltx, "-interaction=nonstopmode", "main.tex"],
        [bib, "main"],
        [ltx, "-interaction=nonstopmode", "main.tex"],
        [ltx, "-interaction=nonstopmode", "main.tex"],
    ]:
        proc = subprocess.run(cmd, cwd=ms_dir, capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-2000:])
            print(proc.stderr[-1000:])
            raise RuntimeError(f"LaTeX command failed: {' '.join(cmd)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Indonesian Crypto Research Pipeline")
    parser.add_argument(
        "stage",
        choices=["acquire", "process", "experiments", "figures", "tables", "compile", "reproduce-processed", "run-all"],
    )
    parser.add_argument("--config", default="config/full_research.yaml")
    parser.add_argument(
        "--mode",
        choices=["processed", "full-raw"],
        default="processed",
        help="Pipeline mode for run-all: 'processed' uses tracked data/processed/ (no data/raw/ needed); 'full-raw' validates/rebuilds from data/raw/.",
    )
    parser.add_argument("--skip-compile", action="store_true", help="Skip LaTeX PDF compilation.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / args.config).read_text())

    effective_mode = "processed" if args.stage == "reproduce-processed" else args.mode

    if args.stage == "acquire" or (args.stage == "run-all" and effective_mode == "full-raw" and cfg.get("run_acquisition", False)):
        run_all_acquisition(root, root / cfg["acquisition_config"])

    if args.stage == "process" or (args.stage == "run-all" and effective_mode == "full-raw"):
        validate_raw_inputs(root)
        build_all_datasets(root)

    if args.stage in ("experiments", "reproduce-processed", "run-all"):
        validate_processed_inputs(root)
        run_all_experiments(root, root / cfg["econometrics_config"])
        run_jisdor_window_vwap()

    if args.stage in ("figures", "reproduce-processed", "run-all"):
        validate_processed_inputs(root)
        figs = generate_all_figures(root)
        print(f"Generated {len(figs)} PDF figures.")

    if args.stage in ("tables", "reproduce-processed", "run-all"):
        tabs = generate_all_latex_tables(root)
        print(f"Generated {len(tabs)} LaTeX tables.")

    if not args.skip_compile and args.stage in ("compile", "reproduce-processed", "run-all") and (root / "manuscript" / "main.tex").exists():
        compile_manuscript(root, cfg["latex_binary"], cfg["bibtex_binary"])
        print("Compiled manuscript/main.pdf successfully.")


if __name__ == "__main__":
    main()
