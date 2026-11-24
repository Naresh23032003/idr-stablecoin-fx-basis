# HAC Bandwidth and Residual Diagnostics Audit

**Date:** 2026-11-24  
**Source:** `results/diagnostics/hac_bandwidth_sensitivity.csv`, `results/diagnostics/residual_diagnostics_multilag.csv`  

## 1. Multi-Lag Residual Diagnostics (5-Minute 3-Variable VECM, $T_{\mathrm{eff}} = 616,677$)

Ljung-Box and ARCH-LM tests across lags $5, 10, 24, 48$ reject white noise and homoskedasticity ($p < 10^{-16}$) in all three equations (`Indodax_BTCIDR`, `Binance_BTCUSDT`, `Indodax_USDTIDR`). In high-frequency ($N > 600{,}000$) crypto return series, volatility clustering and microstructure bounce routinely yield $p \approx 0$ on portmanteau tests; this does not invalidate the VECM point estimates, but it renders i.i.d. ML standard errors unreliable and requires HAC covariance estimation for adjustment inference and heteroskedasticity-robust (block-wild) bootstrap for rank inference.

## 2. HAC Bandwidth Sensitivity ($L \in \{12, 24, 27\,(\text{NW auto}), 48, 144, 288\}$)

For the critical weak-exogeneity test on **global Binance `BTC/USDT`**:

| Bandwidth $L$ | $\hat{\alpha}_{\mathrm{BTC/USDT}}$ | HAC SE | $t$-stat | $p$-value | 95% CI |
|---:|---:|---:|---:|---:|---|
| 12 (1h, baseline) | `0.00113` | `0.00139` | `0.810` | `0.41787` | `[-0.00160, 0.00385]` |
| 24 (2h) | `0.00113` | `0.00138` | `0.813` | `0.41596` | `[-0.00159, 0.00384]` |
| 27 (NW auto) | `0.00113` | `0.00139` | `0.813` | `0.41641` | `[-0.00159, 0.00384]` |
| 48 (4h) | `0.00113` | `0.00140` | `0.807` | `0.41977` | `[-0.00161, 0.00386]` |
| 144 (12h) | `0.00113` | `0.00141` | `0.798` | `0.42494` | `[-0.00164, 0.00389]` |
| 288 (24h) | `0.00113` | `0.00138` | `0.819` | `0.41303` | `[-0.00157, 0.00382]` |

**Conclusion:** Weak exogeneity of Binance `BTC/USDT` ($p \in [0.413, 0.425]$) and significance of Indodax `BTC/IDR` and `USDT/IDR` adjustment ($p < 0.0001$ at all bandwidths) are completely robust across HAC bandwidths from 1 hour to 24 hours.
