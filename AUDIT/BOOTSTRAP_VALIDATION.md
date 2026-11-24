# Sequential Bootstrap and Monte Carlo Validation Audit

**Date:** 2026-11-24  
**Sources:** `src/econometrics/bootstrap.py`, `results/tables/table4_bootstrap_rank_tests.csv`, `results/tables/table4b_bootstrap_dgp_validation.csv`, `results/models/intraday_and_tar_results.json`, `results/diagnostics/bootstrap_5m_block_sensitivity.csv`, `results/diagnostics/bootstrap_rank_sequential.csv`, `results/diagnostics/bootstrap_monte_carlo.csv`  

## 1. Replication Counts & Precision Transparency

- **Primary Daily Sequential Bootstrap (`table4_bootstrap_rank_tests.csv`, Manuscript Table 3):** **$B = 9,999$** replications (`0` failures), block length $b = \mathrm{round}(1412^{1/4}) = 6$, minimum attainable $p = 0.0001$.
- **Primary 5-Minute 3-Variable Sequential Bootstrap (`intraday_and_tar_results.json`, Manuscript Table 4):** **$B = 499$** valid draws (`0` failures) for **all three rank hypotheses** ($H_0: r=0$, $H_0: r \le 1$, $H_0: r \le 2$), block length $b = 28$, minimum attainable $p = 0.0020$.
- **High-Frequency Block-Length Sensitivity (`bootstrap_5m_block_sensitivity.csv`):** **$B = 499$** valid draws (`0` failures) across $b \in \{14, 28, 56, 112\}$.
- **Daily Block-Length Sensitivity (`bootstrap_rank_sequential.csv`):** Separate diagnostic sensitivity grid using **$B = 999$** across $b \in \{1, 3, 6, 12, 24\}$.

## 2. Primary 5-Minute Sequential Rank & Block-Length Sensitivity ($B = 499$, `0` failures)

| Block Length | Null Hypothesis | Valid Draws | Failed | Trace Obs | Boot $p$ | MC SE | 95% Boot CV |
|---|---|---:|---:|---:|---:|---:|---:|
| $b = 14$ | $H_0: r=0$ | 499 | 0 | `9,125.47` | `0.0020` | `0.0020` | `50.76` |
| $b = 14$ | $H_0: r \le 1$ | 499 | 0 | `11.10` | `0.6440` | `0.0214` | `33.32` |
| **$b = 28$ (Primary)** | **$H_0: r=0$** | **499** | **0** | **`9,125.47`** | **`0.0020`** | **`0.0020`** | **`55.25`** |
| **$b = 28$ (Primary)** | **$H_0: r \le 1$** | **499** | **0** | **`11.10`** | **`0.6420`** | **`0.0215`** | **`30.22`** |
| **$b = 28$ (Primary)** | **$H_0: r \le 2$** | **499** | **0** | **`1.38`** | **`0.7000`** | **`0.0205`** | **`11.02`** |
| $b = 56$ | $H_0: r=0$ | 499 | 0 | `9,125.47` | `0.0020` | `0.0020` | `69.86` |
| $b = 56$ | $H_0: r \le 1$ | 499 | 0 | `11.10` | `0.6480` | `0.0214` | `29.28` |
| $b = 112$ | $H_0: r=0$ | 499 | 0 | `9,125.47` | `0.0020` | `0.0020` | `110.07` |
| $b = 112$ | $H_0: r \le 1$ | 499 | 0 | `11.10` | `0.5800` | `0.0221` | `26.06` |

## 3. Monte Carlo Validation (`table4b_bootstrap_dgp_validation.csv`)

- **Primary validation (`n_mc = 1,000`, `n_boot = 299`, `0` failures):** Empirical size is `5.9% ± 0.8%` ($T=25$), modestly above nominal at **`7.1% ± 0.8%`** ($T=100$), and `4.7% ± 0.7%` ($T=500$), compared to severe asymptotic over-rejection (`22.8% / 18.2% / 13.3%`). Finite-sample power is low at very small $T$ (**`8.7% ± 0.9%`** at $T=25$), rising to `72.8% ± 1.4%` at $T=100$ and `100.0%` at $T=500$.
- **Sensitivity grid (`n_mc = 200`, `n_boot = 199`, `0` failures):** Across $\phi \in \{0.0, 0.2, 0.5\}$, Student-$t_5$, and $b=1$, empirical size stays within `[4.5%, 7.5%]` and power is `100.0%` at $T=500$.
