# Deterministic Specification Audit

**Date:** 2026-11-23  
**Status:** INCONSISTENCY IDENTIFIED AND RESOLVED  

## 1. Initial Defect

1. **Manuscript (`manuscript/sec4_econometric_methodology.tex`):** Described a restricted constant inside the cointegrating relation ($H_1^*(r)$, `deterministic="ci"`) for both Johansen rank tests and the bivariate VECM equation $\Delta Y_t = \alpha(\beta' Y_{t-1} + \mu) + \sum_{j=1}^{p-1} \Gamma_j \Delta Y_{t-j} + u_t$.
2. **Implementation (`src/econometrics/cointegration.py`, `ecm.py`, `bootstrap.py`):**
   - `coint_johansen(Y, det_order=0, ...)` implements Johansen's $H_1(r)$ (**unrestricted constant**, `co`), allowing a non-zero drift in $Y_t$ and an intercept in $\beta' Y_t$. (`statsmodels.tsa.vector_ar.vecm.coint_johansen` does not even support `ci`.)
   - `VECM(Y, ..., deterministic="co")` and the HAC OLS regressions in `ecm.py` also used `co` (unrestricted constant).
   - `bootstrap.py` simulated under `mu_hat` in first differences (`det_order=0` = `co`) and re-estimated `coint_johansen(..., det_order=0)`.
3. **Sensitivity Table Mislabelling (`src/robustness/runner.py` & `app_bootstrap_and_fees.tex`):**
   - `run_lag_and_deterministic_sensitivity` ran `det_order=0` (`co`) vs `det_order=1` (`lo`, linear trend) for Johansen, paired `det_order=1` with `VECM(..., deterministic="ci")`, and `app_bootstrap_and_fees.tex` mislabeled `det_order=0` as "Restricted constant" and `det_order=1` as "Unrestricted constant".

## 2. Economic & Statistical Resolution

1. **Primary Specification (`co`, Johansen $H_1(r)$):**
   - Log asset prices ($\ln P_{X,t}^{IDR}$, $\ln P_{X,t}^{USDT}$) and log FX rates ($\ln U_t^{IDR/USDT}$, $\ln S_t^{IDR/USD}$) exhibit secular drift over 2021–2026 (BTC appreciation and IDR depreciation), while the cointegrating spread $\beta' Y_t$ has a non-zero mean (e.g., $+30$ bps wedge) without a deterministic time trend.
   - Therefore, **`co` (unrestricted constant, $H_1(r)$, `det_order=0`)** is the economically appropriate primary specification and ensures 100% compatibility across Johansen rank tests, VECM estimation, HAC OLS, and the block-wild bootstrap.
2. **Code & Metadata Fixes:**
   - Added `johansen_ci_restricted_constant` ($H_1^*(r)$) in `src/econometrics/cointegration.py` so genuine `ci` sensitivity checks are available alongside `co` and `lo` (`det_order=1`).
   - Fixed `ecm.py` HAC OLS so when `det_order == "ci"`, the constant is placed inside `ect_lag` (`res.const_coint[0, 0]`) with no unrestricted intercept.
   - Fixed `run_lag_and_deterministic_sensitivity` in `src/robustness/runner.py` to test `"ci"`, `"co"`, and `"lo"` consistently across both Johansen and VECM.
   - Recorded `deterministic_spec` in all VECM, cointegration, and bootstrap outputs and `config/econometrics.yaml`.
   - Revised `manuscript/sec4_econometric_methodology.tex` and `manuscript/app_bootstrap_and_fees.tex` to match `co` ($H_1(r)$) and the corrected sensitivity table.
