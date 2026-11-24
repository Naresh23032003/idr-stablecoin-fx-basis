# Final Execution Summary

| Item | Initial State | Final State | Evidence |
|---|---|---|---|
| Timestamp validity | 5-min look-ahead (`direction="forward"` on candle `open_time`) | Fixed (`direction="backward"` on `observation_available_time_utc`, `0.0s` lag across 1,414 days) | `AUDIT/TIMESTAMP_AUDIT.md`, `results/diagnostics/timestamp_alignment_summary.json` |
| Deterministic terms | Manuscript claimed `ci`, code ran `co`, Appendix mislabeled `0`/`1` | Unified on `co` ($H_1(r)$) across code & manuscript; genuine `ci`/`co`/`lo` sensitivity added | `AUDIT/DETERMINISTIC_SPECIFICATION_AUDIT.md`, `table10_lag_deterministic_sensitivity.csv` |
| Bootstrap inference | Tested only $H_0: r=0$; stale `iid` label in `econometrics.yaml` | Sequential $H_0: r=0, r\le 1, r\le 2$ block-wild bootstrap + block-length sensitivity | `AUDIT/BOOTSTRAP_VALIDATION.md`, `results/diagnostics/bootstrap_rank_sequential.csv` |
| Monte Carlo validation | Single $\phi=0.20$ Gaussian run without MC SEs | Added MC SEs, `n_failed`, $\phi \in \{0.0, 0.2, 0.5\}$, Student-$t_5$, and $b=1$ sensitivity (`0` failures) | `results/tables/table4b_bootstrap_dgp_validation.csv`, `results/diagnostics/bootstrap_monte_carlo.csv` |
| Half-life interpretation | Foregrounded `25.08` bars without explaining `1.13`-bar IRF | Eigenmode projection shows `53.0%` fast-mode (`<=1.27` bars) vs `47.0%` slow-mode (`25.08` bars) | `AUDIT/HALF_LIFE_INTERPRETATION.md`, `results/diagnostics/half_life_eigenmodes_5m.csv` |
| HAC robustness | Single `L=12` bandwidth on 5m VECM | Tested $L \in \{12, 24, 27, 48, 144, 288\}$; Binance weak exog invariant ($p \in [0.413, 0.425]$) | `AUDIT/HAC_AND_RESIDUAL_DIAGNOSTICS.md`, `results/diagnostics/hac_bandwidth_sensitivity.csv` |
| Stale-price robustness | All-bars vs irregular active-only only | Tested prolonged zero-vol exclusions (`>3, >6, >12` bars) on regular grid; ~80% Indodax share invariant | `AUDIT/STALE_PRICE_AND_ZERO_VOLUME.md`, `results/diagnostics/stale_price_sensitivity_5m.csv` |
| Structural stability | Event windows + one 2023 Chow test | Subsample cointegration & VECM across all 6 institutional regimes (`r=1` in all 6) | `AUDIT/STRUCTURAL_STABILITY.md`, `results/diagnostics/structural_stability_regimes.csv` |
| Event-study robustness | CFX `+17.37 bps` ($p_H=0.026$) without placebo check | Rebuilt `+18.19 bps` ($p_H=0.008$), but 2/3 placebos reject on $B^{s\text{-}FX}$; qualified as non-causal | `AUDIT/CFX_EVENT_STUDY.md`, `results/diagnostics/cfx_event_robustness.csv` |
| Fee evidence | Partially verified 2022–2024 tiers noted in prose | Full primary/secondary source register (`12` entries) + `[61, 81]` bps bounds (`[97.24%, 98.59%]`) | `AUDIT/INSTITUTIONAL_AND_FEE_EVIDENCE.md`, `AUDIT/SOURCE_EVIDENCE_REGISTER.csv` |
| Reproducibility | Hardcoded `/Users/naresh/Library/TinyTeX/...`, stale `latex_tables.py` | Portable `pdflatex` resolution, `latex_tables.py` fixed, `jisdor_window_vwap.json` persisted, `18` tests pass | `AUDIT/REPRODUCIBILITY_AUDIT.md`, `AUDIT/REPRODUCTION_MANIFEST.json` |
| Manuscript consistency | Stale pre-fix numbers & `ci` equations | All numbers, tables, figures, and PDF rebuilt and verified (`0` LaTeX/BibTeX errors) | `AUDIT/FINAL_VALIDATION_REPORT.md`, `manuscript/main.pdf` |
| Independent referee assessment | — | Three independent reviews + editorial simulation: **Acceptable for Submission** | `AUDIT/REFEREE_{A,B,C}_REPORT.md`, `AUDIT/EDITORIAL_DECISION.md` |

## Exact Reproduction Command
```bash
MPLCONFIGDIR=/tmp/mpl python -m src.pipeline run-all --config config/full_research.yaml
python src/robustness/jisdor_window_and_holm_events.py
pytest -v
```
