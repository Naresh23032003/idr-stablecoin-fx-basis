# Structural Stability and Regime Dependence Audit

**Date:** 2026-11-24  
**Sources:** `results/diagnostics/structural_stability_regimes.csv`, `results/diagnostics/structural_stability_wald.json`  

## 1. Subsample Cointegration, $\hat{\beta}$, and HAC 95% CIs Across Six Institutional Regimes

| Regime | $n$ | $\bar{B}_{s\text{-}FX}$ | $\hat{\beta}$ | Trace (RA) | $\hat{\alpha}_{local}$ [95% HAC CI] | $p_{loc}$ | $p_{glob}$ |
|---|---:|---:|---:|---:|---|---:|---:|
| R1 Pre-Tax (2021-01 to 2022-04) | 327 | `83.02` | `1.0225` | `44.68` | `-0.312` `[-0.758, 0.134]` | `0.170` | `0.562` |
| R2A PMK68 (2022-05 to 2023-08) | 315 | `8.01` | `0.9952` | `102.69` | `-0.443` `[-1.684, 0.798]` | `0.484` | `0.817` |
| R2B ProCut (2023-08 to 2024-10) | 288 | `25.03` | `1.0010` | `81.34` | `-1.364` `[-2.143, -0.586]` | `0.001` | `0.056` |
| R3 CFX/OJK (2024-11 to 2025-07) | 172 | `26.85` | `0.9912` | `63.20` | `-1.353` `[-2.761, 0.055]` | `0.060` | `0.352` |
| R4 PMK50 (2025-08 to 2026-02) | 143 | `26.26` | `1.0031` | `47.67` | `-1.436` `[-2.968, 0.097]` | `0.066` | `0.320` |
| R5–R6 CFX Cuts (2026-03 to 2026-11) | 169 | `-11.31` | `0.9929` | `34.66` | `-0.681` `[-2.015, 0.652]` | `0.317` | `0.737` |

## 2. Formal Parameter-Stability Wald Test

- **Test:** Pooled HAC ($L=5$) interaction Wald test of $H_0: \alpha_{\mathrm{local}, R1} = \alpha_{\mathrm{local}, R2A} = \dots = \alpha_{\mathrm{local}, R6}$ (`results/diagnostics/structural_stability_wald.json`).
- **Result:** $\chi^2(5) = 2.356$, **$p = 0.7980$** — **fail to reject equality of $\alpha_{\mathrm{local}}$ across regimes**.
- **Interpretation:** Although point estimates of $\hat{\alpha}_{\mathrm{local}}$ vary across subsamples (`-0.312` to `-1.436`), subsample HAC confidence intervals are wide and heavily overlapping (especially in shorter 2024–2026 regimes of $n = 143$–$172$ days). Cointegration rank $r=1$ and $\hat{\beta} \approx 1.00$ (`0.991`–`1.023`) hold in all six regimes, whereas mean $B_t^{stablecoin\text{-}FX}$ undergoes large level shifts (`+83.02` bps in R1 to `-11.31` bps in R5–R6).
