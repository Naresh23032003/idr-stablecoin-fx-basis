# Econometric & Quantitative Methodology

1. **Three-Leg Accounting Identity (Zero Unverified Unit Assumptions):**
   For asset $X \in \{\text{BTC}, \text{ETH}, \text{XRP}\}$, define:
   $$B_t^{total} = \ln P_{X,t}^{IDR} - \ln P_{X,t}^{USDT} - \ln S_t^{IDR/USD}$$
   $$B_t^{crypto} = \ln P_{X,t}^{IDR} - \ln P_{X,t}^{USDT} - \ln U_t^{IDR/USDT}$$
   $$B_t^{stablecoin\text{-}FX} = \ln U_t^{IDR/USDT} - \ln S_t^{IDR/USD}$$
   Because global $P_{X,t}^{USDT}$ is quoted in USDT (not USD), we observe the live USD/USDT peg wedge $W_t^{USD/USDT}$ separately on Coinbase (`USDT-USD`) rather than assuming $\text{USD} \equiv \text{USDT}$. By exact algebra:
   $$\mathrm{Var}(B_t^{total}) = \mathrm{Var}(B_t^{crypto}) + \mathrm{Var}(B_t^{stablecoin\text{-}FX}) + 2\,\mathrm{Cov}(B_t^{crypto}, B_t^{stablecoin\text{-}FX}).$$
2. **Synchronization Protocol:** Primary daily tests match crypto 5-minute closes strictly at or within 5 minutes after official JISDOR publication instants (`03:00 UTC` pre-Apr 5, 2021; `09:15 UTC` through Mar 31, 2026; `08:15 UTC` from Apr 1, 2026 onward), never forward-filling weekend/holiday JISDOR values into primary inference. Sensitivity tests cover `-15m`, `+5m`, `+15m`, `23:59 UTC`, `t+1` JISDOR, Yahoo `IDR=X`, and ECB `USD/IDR`.
3. **Unit Roots & Cointegration:** Full ADF, Phillips-Perron, KPSS, and Zivot-Andrews testing is followed by three distinct tests: (i) Engle-Granger (estimated slope $\hat\beta$), (ii) Fixed-$(1,-1)$ ADF/KPSS on the imposed economic spread, and (iii) Johansen Trace/Max-Eigenvalue with Reinsel-Ahn $(T - kp)/T$ statistic scaling and Cheung-Lai critical-value scaling.
4. **Null-Imposed VECM Residual Bootstrap ($B = 9,999$):** Restricted VECM under $H_0: r=0$ preserves short-run VAR dynamics $\hat\Gamma_j$ and resamples centered i.i.d. innovation vectors recursively with Monte Carlo SE $< 0.005$ at $p=0.5$. Size and power are validated across $T \in \{25, 100, 500\}$ under controlled $r=0$ and $r=1$ DGPs.
5. **Adjustment, Price Discovery, Nonlinearity & Breaks:** Bivariate VECMs use HAC (Newey-West) covariance and report half-lives strictly in native sampling units (business days for JISDOR panels; 5-minute bars for 24/7 panels). Price discovery reports Gonzalo-Granger permanent-component weights alongside Cholesky Hasbrouck IS bounds, flagging daily contemporaneous residual correlation ($\rho_u = 0.991$) as making Cholesky bounds uninformative. Symmetric Band-TAR strictly nests linear AR dynamics for positive `sup-Wald` testing with residual bootstrap $p$-values.
