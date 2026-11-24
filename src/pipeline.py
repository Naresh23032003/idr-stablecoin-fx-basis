"""Master reproducible research pipeline CLI: acquire -> process -> experiments -> figures -> tables -> compile."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import yaml

from src.acquisition.run_acquisition import run_all_acquisition
from src.experiments_runner import run_all_experiments
from src.manuscript.latex_tables import generate_all_latex_tables
from src.synchronization.aligner import build_all_datasets
from src.visualizations.figures import generate_all_figures


def compile_manuscript(root: Path, latex_bin: str, bibtex_bin: str) -> None:
    import shutil
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
    parser.add_argument("stage", choices=["acquire", "process", "experiments", "figures", "tables", "compile", "run-all"])
    parser.add_argument("--config", default="config/full_research.yaml")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / args.config).read_text())

    if args.stage in ("acquire",) or (args.stage == "run-all" and cfg.get("run_acquisition", False)):
        run_all_acquisition(root, root / cfg["acquisition_config"])
    if args.stage in ("process", "run-all"):
        build_all_datasets(root)
    if args.stage in ("experiments", "run-all"):
        run_all_experiments(root, root / cfg["econometrics_config"])
    if args.stage in ("figures", "run-all"):
        figs = generate_all_figures(root)
        print(f"Generated {len(figs)} PDF figures.")
    if args.stage in ("tables", "run-all"):
        tabs = generate_all_latex_tables(root)
        print(f"Generated {len(tabs)} LaTeX tables.")
    if args.stage in ("compile", "run-all") and (root / "manuscript" / "main.tex").exists():
        compile_manuscript(root, cfg["latex_binary"], cfg["bibtex_binary"])
        print("Compiled manuscript/main.pdf successfully.")


if __name__ == "__main__":
    main()
