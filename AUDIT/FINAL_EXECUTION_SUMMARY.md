# Final Execution Summary

| Item | Initial State | Final State | Evidence |
|---|---|---|---|
| Timestamp validity | 5-min look-ahead (`forward` on `open_time`); stale `sampling.yaml` rule | Fixed (`backward` on `observation_available_time_utc`, 4-regime JISDOR + 1h sensitivity, regression test) | `AUDIT/TIMESTAMP_AUDIT.md`, `config/sampling.yaml`, `jisdor_schedule_audit.csv` |
| Deterministic terms | Manuscript claimed `ci`, code ran `co`, Appendix mislabeled `0`/`1` | Unified on `co` ($H_1(r)$) across code & manuscript; genuine `ci`/`co`/`lo` sensitivity added | `AUDIT/DETERMINISTIC_SPECIFICATION_AUDIT.md`, `table10_lag_deterministic_sensitivity.csv` |
| Bootstrap inference | Tested only $H_0: r=0$; stale `iid` label; 5m $r\le 1,2$ had $B=99$ | Daily $B=9,999$ sequential; 5m $B=499$ (`0` failures) for $r=0,1,2$ + $b\in\{14,28,56,112\}$ sensitivity | `AUDIT/BOOTSTRAP_VALIDATION.md`, `bootstrap_5m_block_sensitivity.csv` |
| Monte Carlo validation | Single $\phi=0.20$ run without MC SEs | Added MC SEs, `n_failed=0`, $\phi \in \{0.0, 0.2, 0.5\}$, $t_5$, and accurate `7.1%` size ($T=100$) / `8.7%` power ($T=25$) prose | `table4b_bootstrap_dgp_validation.csv`, `bootstrap_monte_carlo.csv` |
| Half-life interpretation | Foregrounded `25.08` bars without explaining `1.13`-bar IRF | Normalization-invariant `compute_vecm_eigenmode_decomposition()` in `ecm.py` (`53.0%` fast / `47.0%` slow, err $6.6\times 10^{-15}$) | `AUDIT/HALF_LIFE_INTERPRETATION.md`, `src/econometrics/ecm.py` |
| HAC robustness | Single `L=12` bandwidth on 5m VECM | Tested $L \in \{12, 24, 27, 48, 144, 288\}$; Binance weak exog invariant ($p \in [0.413, 0.425]$) | `AUDIT/HAC_AND_RESIDUAL_DIAGNOSTICS.md`, `hac_bandwidth_sensitivity.csv` |
| Stale-price robustness | All-bars vs irregular active-only only | Tested prolonged zero-vol exclusions (`>3, >6, >12` bars) on regular grid; ~80% Indodax share invariant | `AUDIT/STALE_PRICE_AND_ZERO_VOLUME.md`, `stale_price_sensitivity_5m.csv` |
| Structural stability | Event windows + one 2023 Chow test | Tracked `estimate_regime_stability_and_wald()` in `structural_breaks.py` ($\chi^2(5)=2.356, p=0.798$, scoped to $\alpha_{\mathrm{local}}$) | `AUDIT/STRUCTURAL_STABILITY.md`, `structural_stability_wald.json` |
| Event-study robustness | CFX `+17.37 bps` ($p_H=0.026$) without placebo check | Rebuilt `+18.19 bps` ($p_H=0.008$), 2/3 placebos reject on $B^{s\text{-}FX}$; qualified as non-causal | `AUDIT/CFX_EVENT_STUDY.md`, `cfx_event_robustness.csv` |
| Fee evidence & routes | Route A foregrounded for cross-venue $B^{crypto}$ | Route B (`99.01%`) foregrounded as cross-venue benchmark alongside Route A (`98.30%`, `[97.24%, 98.59%]`) | `AUDIT/INSTITUTIONAL_AND_FEE_EVIDENCE.md`, `SOURCE_EVIDENCE_REGISTER.csv` |
| Reproducibility | No processed-only mode; hardcoded TinyTeX paths | Explicit `reproduce-processed` vs `--mode full-raw`, fail-early validation, verified without `data/raw/`, **`22` tests pass** | `AUDIT/REPRODUCIBILITY_AUDIT.md`, `AUDIT/REPRODUCTION_MANIFEST.json` |
| Manuscript consistency | Stale numbers & `ci` equations | All numbers, tables, figures, and PDF rebuilt and verified (`0` LaTeX/BibTeX errors) | `AUDIT/FINAL_VALIDATION_REPORT.md`, `manuscript/main.pdf` |
| Independent referee assessment | Major revision | All P0/P1 items resolved in code, tests, and manuscript | `AUDIT/EDITORIAL_DECISION.md` |

## Clean-Checkout Reproduction Command (No `data/raw/` Required)
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
MPLCONFIGDIR=/tmp/mpl python -m src.pipeline reproduce-processed --config config/full_research.yaml
pytest -v
```
