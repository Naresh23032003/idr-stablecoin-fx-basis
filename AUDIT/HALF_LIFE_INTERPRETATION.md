# Half-Life Interpretation Audit

**Date:** 2026-11-24  
**Code:** `src/econometrics/ecm.py:compute_vecm_eigenmode_decomposition`, `compute_vecm_system_half_life`  
**Output:** `results/diagnostics/half_life_eigenmodes_5m.csv`  

## 1. Exact Normalization-Invariant Eigenmode Projection

Using the eigendecomposition $F = V \Lambda V^{-1}$ of the $18 \times 18$ levels VAR(6) companion matrix ($n=3$, $k_{\mathrm{ar}}=6$), the ECT impulse response at horizon $h$ to an initial state $s_0 = [d_0', 0, \dots, 0]'$ satisfies:
$$\frac{z_h}{z_0} = \frac{\beta' (F^h s_0)_{[:n]}}{\beta' d_0} = \sum_{j=1}^{18} c_j \lambda_j^h, \qquad c_j = \frac{(\beta' v_{j,[:n]})(w_j' s_0)}{\beta' d_0},$$
where $w_j'$ is the $j$-th row of $V^{-1}$. Because $v_j \to \gamma v_j$ implies $w_j' \to \gamma^{-1} w_j'$, each modal share $c_j$ is **strictly invariant to eigenvector normalization**. Direct verification in `compute_vecm_eigenmode_decomposition()` confirms:
- $\sum_j c_j^{\mathrm{local}} = 1.0000000000000000$
- $\sum_j c_j^{\mathrm{gen}} = 1.0000000000000004$
- $\max_{0 \le h \le 60} |z_h^{\mathrm{spectral}} - z_h^{\mathrm{direct}}| = 6.61 \times 10^{-15}$

## 2. Reconciling the Three Half-Life Summaries (5m 3-Variable VECM, $T_{\mathrm{eff}} = 616,677$)

| Measure | Value (5m bars) | Modal Share / Interpretation |
|---|---:|---|
| Local-shock ECT IRF half-life ($e_1$) | **1.13** (~5.65 min) | `52.96%` of $z_0$ loads onto fast transient modes ($|\lambda| \le 0.5786$, HL $\le 1.27$ bars), pushing $|z_h|$ below $0.5|z_0|$ in ~1 bar. |
| Generalized-shock ECT IRF half-life ($d_{\mathrm{gen}}$) | **0.95** (~4.75 min) | `59.22%` of $z_0$ loads onto fast transient modes. |
| Scalar $1 + \beta'\alpha$ benchmark | **12.09** (~1.01 hours) | No-lag approximation ignoring $\Gamma_1, \dots, \Gamma_5$. |
| Slowest stable companion-root mode ($\lambda = 0.972746$) | **25.08** (~2.09 hours) | Carries the remaining **`47.04%`** (local) / **`40.78%`** (generalized) persistent tail. |

**Caveat:** Both the adjustment shares and companion/IRF half-lives are point-estimate summaries of the 5-minute VECM; unlike the weak-exogeneity test (whose HAC $p \in [0.413, 0.425]$ is verified across bandwidths $L \in [12, 288]$), these dynamic summaries should be interpreted descriptively.
