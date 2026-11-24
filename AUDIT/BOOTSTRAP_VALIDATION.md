# Sequential Bootstrap and Monte Carlo Validation Audit

**Date:** 2026-11-24  
**Sources:** `src/econometrics/bootstrap.py`, `results/tables/table4_bootstrap_rank_tests.csv`, `results/tables/table4b_bootstrap_dgp_validation.csv`, `results/models/intraday_and_tar_results.json`, `results/diagnostics/bootstrap_rank_sequential.csv`, `results/diagnostics/bootstrap_monte_carlo.csv`  

## 1. Replication Counts & Precision Transparency

To avoid any ambiguity between primary runs and diagnostic sensitivity grids:
- **Primary Daily Sequential Bootstrap (`table4_bootstrap_rank_tests.csv`, reported in Manuscript Table 3):** **$B = 9,999$** replications, block length $b = \mathrm{round}(1412^{1/4}) = 6$, minimum attainable $p = 1/(9999+1) = 0.0001$.
- **Primary 5-Minute 3-Variable Sequential Bootstrap (`intraday_and_tar_results.json`, reported in Manuscript Table 4):** **$B = 499$** for $H_0: r=0$ (min $p = 0.0020$) and **$B = 99$** for $H_0: r \le 1$ and $H_0: r \le 2$ (min $p = 0.0100$), block length $b = \mathrm{round}(616677^{1/4}) = 28$.
- **Daily Block-Length Sensitivity Grid (`results/diagnostics/bootstrap_rank_sequential.csv`):** Separate diagnostic sensitivity run using **$B = 999$** (min $p = 0.0010$) across $b \in \{1, 3, 6, 12, 24\}$.

## 2. Primary Daily Sequential Rank Results (`table4_bootstrap_rank_tests.csv`, $B = 9,999$, $b = 6$)

| System | $p_{\mathrm{boot}}(H_0: r=0)$ | $p_{\mathrm{boot}}(H_0: r \le 1)$ | Conclusion |
|---|---:|---:|---|
| `BTC_Unadjusted` | `0.8679` | `0.7273` | **Rank $r = 0$** |
| `BTC_JISDOR_Converted` | `0.0001` | `0.7028` | **Rank $r = 1$** |
| `BTC_USDT_Converted` | `0.0001` | `0.7201` | **Rank $r = 1$** |
| `BTC_SpotFX_Converted` | `0.0001` | `0.7133` | **Rank $r = 1$** |
| `USDT_IDR_vs_JISDOR` | `0.0008` | `0.8108` | **Rank $r = 1$** |
| `ETH_JISDOR_Converted` | `0.0001` | `0.0556` | **Rank $r = 1$** |
| `XRP_JISDOR_Converted` | `0.0001` | `0.3594` | **Rank $r = 1$** |

**Primary 5-Minute 3-Variable System ($b = 28$):**
- $H_0: r=0$ ($B=499$): $\text{Trace} = 9,125.47$, $p_{\mathrm{boot}} = 0.0020$ (95% CV `56.19`) — **Reject**.
- $H_0: r \le 1$ ($B=99$): $\text{Trace} = 11.10$, $p_{\mathrm{boot}} = 0.6100$ — **Fail to reject**.
- $H_0: r \le 2$ ($B=99$): $\text{Trace} = 1.38$, $p_{\mathrm{boot}} = 0.6900$ — **Fail to reject**.

**Block-Length Sensitivity (`BTC_JISDOR`, $B = 999$, $b \in \{1, 3, 6, 12, 24\}$):**  
Across all block lengths, $H_0: r=0$ rejects at $p = 0.0010$ (95% CV rises from `34.25` at $b=1$ to `72.97` at $b=24$ vs observed `150.49`) and $H_0: r \le 1$ fails to reject ($p \in [0.718, 0.761]$).

## 3. Monte Carlo Validation (`table4b_bootstrap_dgp_validation.csv` & `bootstrap_monte_carlo.csv`)

- **Primary validation (`n_mc = 1,000`, `n_boot = 299`, `0` failures):** Empirical size `5.9% ± 0.8%` ($T=25$), `7.1% ± 0.8%` ($T=100$), `4.7% ± 0.7%` ($T=500$) vs asymptotic `22.8% / 18.2% / 13.3%`; power reaches `72.8%` ($T=100$) and `100.0%` ($T=500$).
- **Sensitivity grid (`n_mc = 200`, `n_boot = 199`, `0` failures):** Across $\phi \in \{0.0, 0.2, 0.5\}$, Student-$t_5$, and $b=1$, empirical size stays within `[4.5%, 7.5%]` and power is `100.0%` at $T=500$.
