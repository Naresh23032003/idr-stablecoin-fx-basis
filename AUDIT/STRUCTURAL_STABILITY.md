# Structural Stability and Regime Dependence Audit

**Date:** 2026-11-24  
**Source Code:** `src/econometrics/structural_breaks.py:estimate_regime_stability_and_wald`  
**Outputs:** `results/diagnostics/structural_stability_regimes.csv`, `results/diagnostics/structural_stability_wald.json`  

## 1. Pooled HAC Interaction Wald Specification

- **Sample:** $T_{\mathrm{eff}} = 1,412$ synchronized daily business days (`2021-01-04` to `2026-11-12`, $k_{\mathrm{ar\_diff}} = 1$, `deterministic = "co"`).
- **Regression Equation:** Conditional on the full-sample cointegrating error $z_{t-1} = \hat{\beta}' Y_{t-1}$ where $Y_t = [\ln P_{BTC,t}^{IDR}, \ln(P_{BTC,t}^{USDT} S_t^{JISDOR})]'$:
  $$\Delta \ln P_{BTC,t}^{IDR} = c_0 + \alpha_0 z_{t-1} + \gamma_1 \Delta \ln P_{BTC,t-1}^{IDR} + \gamma_2 \Delta \ln P_{BTC,t-1}^{*} + \sum_{r=2}^{6} \left[ \delta_r \mathbb{I}(t \in r) + \theta_r (z_{t-1} \mathbb{I}(t \in r)) \right] + u_t.$$
- **Parameter Restrictions:** $H_0: \theta_2 = \theta_3 = \theta_4 = \theta_5 = \theta_6 = 0$ ($\mathrm{df} = 5$).
- **Covariance Estimator:** Newey--West HAC (`maxlags = 5`).
- **Result:** $\chi^2(5) = 2.356$, **$p = 0.7980$** (fail to reject equality of $\alpha_{\mathrm{local}}$ across the six regimes).
- **Explicit Scope Clarification:** This test evaluates equality of the local error-correction coefficient $\alpha_{\mathrm{local}}$ across the six institutional regimes conditional on the full-sample cointegrating vector $\hat{\beta}$. It does **not** constitute a comprehensive structural-stability test of the full VECM ($\beta$, $\Gamma_j$, $\mu_0$, and $\Sigma_u$).

## 2. Subsample Estimates & 95% HAC CIs (`structural_stability_regimes.csv`)

| Regime | $n$ | $\bar{B}_{s\text{-}FX}$ | $\hat{\beta}$ | Trace (RA) | $\hat{\alpha}_{local}$ [95% HAC CI] | $p_{loc}$ | $p_{glob}$ |
|---|---:|---:|---:|---:|---|---:|---:|
| R1 Pre-Tax (2021-01 to 2022-04) | 327 | `83.02` | `1.0225` | `44.68` | `-0.312` `[-0.758, 0.134]` | `0.170` | `0.562` |
| R2A PMK68 (2022-05 to 2023-08) | 315 | `8.01` | `0.9952` | `102.69` | `-0.443` `[-1.684, 0.798]` | `0.484` | `0.817` |
| R2B ProCut (2023-08 to 2024-10) | 288 | `25.03` | `1.0010` | `81.34` | `-1.364` `[-2.143, -0.586]` | `0.001` | `0.056` |
| R3 CFX/OJK (2024-11 to 2025-07) | 172 | `26.85` | `0.9912` | `63.20` | `-1.353` `[-2.761, 0.055]` | `0.060` | `0.352` |
| R4 PMK50 (2025-08 to 2026-02) | 143 | `26.26` | `1.0031` | `47.67` | `-1.436` `[-2.968, 0.097]` | `0.066` | `0.320` |
| R5–R6 CFX Cuts (2026-03 to 2026-11) | 169 | `-11.31` | `0.9929` | `34.66` | `-0.681` `[-2.015, 0.652]` | `0.317` | `0.737` |
