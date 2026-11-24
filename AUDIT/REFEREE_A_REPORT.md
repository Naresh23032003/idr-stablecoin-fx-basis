# Independent Referee A Report (Econometrician)

**Focus:** Cointegration identification, sequential bootstrap rank inference, deterministic terms, residual diagnostics, half-life interpretation, structural stability, and finite-sample inference.

## 1. Initial Major Concerns (Before Revision)
1. **5-Minute Look-Ahead Bias:** `_asof_window_match` matched forward on candle opening time (`timestamp_utc`), pairing JISDOR fixings with candles closing 5 minutes *after* JISDOR publication.
2. **Deterministic-Term Mismatch:** Manuscript `sec4` specified a restricted constant (`ci`, $H_1^*(r)$), while `coint_johansen(..., det_order=0)`, `VECM(..., deterministic="co")`, and `bootstrap.py` implemented an unrestricted constant (`co`, $H_1(r)$). Appendix Table `tab:lag_sens` also mislabeled `det_order=0` and `det_order=1`.
3. **Incomplete Bootstrap Rank Testing:** `bootstrap.py` tested only $H_0: r=0$, leaving $H_0: r \le 1$ (and $H_0: r \le 2$ in the 3-variable system) unbootstrapped.
4. **Half-Life Interpretation:** Foregrounding `25.08` 5-minute bars obscured the fact that `half_life_irf_local` is `1.13` bars (`0.95` bars generalized).
5. **Event-Study Size Distortion:** On $B_t^{stablecoin\text{-}FX}$, $\pm 30$-day pre/post dummies with $L=5$ HAC SEs reject on arbitrary placebo dates (`2023-06-15`, `2024-03-01`) due to regime shifts.

## 2. Assessment of Final Revised Version
- **Resolved:** Look-ahead bias eliminated via `observation_available_time_utc` backward matching (lag `0.0s` across all 1,414 days); deterministic terms unified on `co` ($H_1(r)$) with genuine `ci` and `lo` sensitivity; sequential block-wild bootstrap implemented and confirming $r=1$ ($p=0.0001$ for $r=0$, $p=0.7028$ for $r \le 1$ daily; $p=0.0020$, $0.6100$, $0.6900$ for $r=0,1,2$ intraday); eigenmode projection clarifies `53.0%` fast-mode vs `47.0%` slow-mode (`25.08`-bar) dynamics; HAC bandwidths $L \in [12, 288]$ confirm invariance of Binance weak exogeneity ($p \in [0.413, 0.425]$); CFX event-study claim appropriately downgraded to non-causal association.
- **Remaining Minor Limitations:** Daily bivariate VECMs still exhibit $\rho_u = 0.990$ (unidentifiable daily Hasbrouck bounds, properly omitted); high-frequency VECM residuals remain conditionally heteroskedastic ($\text{ARCH } p < 0.001$), which is handled via HAC and block-wild bootstrap rather than a multivariate GARCH-VECM.

**Referee A Recommendation:** **Minor Revision / Acceptable** (technical econometric defects resolved).
