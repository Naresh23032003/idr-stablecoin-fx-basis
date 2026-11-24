# CFX Event-Study Audit

**Date:** 2026-11-24  
**Source:** `results/diagnostics/cfx_event_robustness.csv`  

## 1. Event Window & Institutional Mechanism

- **Milestone:** Launch of CFX/KKI bourse and clearing levy (`2.22 bps` VAT-inclusive on IDR pairs, `4.44 bps` on USDT pairs) under BAPPEBTI PERBA No. 9/2024 and CFX/KKI SEB 003/004, effective `2024-10-31 23:59:59 WIB` (`2024-11-01`).

## 2. Sensitivity & Placebo Results on $B_t^{stablecoin\text{-}FX}$ (Controlled HAC OLS, $L=5$)

| Specification | $n$ | $\hat{\Delta}$ (bps) | HAC SE | Raw $p$-value |
|---|---:|---:|---:|---:|
| CFX Nov 1, 2024 ($\pm 7$ days) | 10 | `+6.41` | `2.97` | `0.0310` |
| CFX Nov 1, 2024 ($\pm 15$ days) | 22 | `+8.04` | `4.81` | `0.0943` |
| CFX Nov 1, 2024 ($\pm 30$ days, baseline) | 42 | `+18.19` | `5.12` | `0.0004` |
| CFX Nov 1, 2024 ($\pm 60$ days) | 82 | `+15.14` | `5.53` | `0.0062` |
| CFX Nov 1, 2024 ($\pm 30$d, trim 2 extremes) | 40 | `+14.48` | `6.08` | `0.0173` |
| **Placebo: 2023-06-15 ($\pm 30$ days)** | 38 | **`-18.70`** | `3.71` | **`<0.0001`** |
| **Placebo: 2024-03-01 ($\pm 30$ days)** | 37 | **`+36.47`** | `8.50` | **`<0.0001`** |
| Placebo: 2025-04-01 ($\pm 30$ days) | 35 | `+4.88` | `12.02` | `0.6849` |

## 3. Critical Referee Conclusion

1. Although the Nov 1, 2024 CFX shift (`+18.19` bps in $\pm 30$d on no-look-ahead data; `+14.48` to `+15.14` bps in $\pm 60$d and trimmed checks) is not driven by a single outlier, **two out of three arbitrary placebo dates on $B_t^{stablecoin\text{-}FX}$ also produce large, highly significant $\pm 30$-day shifts** (`-18.70` bps on 2023-06-15 and `+36.47` bps on 2024-03-01, both $p < 0.0001$).
2. **Reason:** Because $B_t^{stablecoin\text{-}FX}$ is a persistent, regime-shifting series (SD `73.66` bps, KPSS $p = 0.01$), local $\pm 30$-day pre/post dummy regressions with $L=5$ HAC SEs exhibit severe size distortion for mean shifts.
3. **Required Manuscript Revision:** Frame the CFX/KKI finding strictly as a **descriptive, non-causal post-event association that does not survive placebo-date falsification on the persistent stablecoin–FX leg**, rather than a clean regulatory event-study effect.
