# Timestamp and Look-Ahead Audit

**Date:** 2026-11-24  
**Status:** CRITICAL DEFECT IDENTIFIED, FIXED, AND SCHEDULE-SENSITIVITY AUDITED  

## 1. Root-Cause Findings (Before Fix)

1. **Binance Vision klines (`src/acquisition/binance_vision.py`), Indodax TradingView candles (`src/acquisition/indodax_history.py`), and Coinbase Exchange candles (`src/acquisition/coinbase_kraken.py`):** All timestamp each bar by its **candle opening time** while reporting the bar's **closing price**.
2. **Look-ahead defect in `src/synchronization/aligner.py`:** `_asof_window_match()` originally used `direction="forward"` on `timestamp_utc` (`open_time`), matching JISDOR fixings at $\tau_t$ to the bar opening at $\tau_t$ whose `close` was not realized until 5 minutes later.
3. **Manuscript schedule-description omission:** `sec3_data_and_synchronization.tex` originally omitted the pandemic operational-hours regime (`R2_COVID_ADJUSTED_1515`, 15:15 WIB / 08:15 UTC) even though `config/sampling.yaml` and `data/processed/jisdor_schedule_calendar.csv` implemented all four regimes.

## 2. Implemented Fix & Four-Regime JISDOR Calendar

1. All loaders now explicitly construct `candle_open_time_utc`, `candle_close_time_utc`, `observation_available_time_utc = candle_open_time_utc + bar_duration`, `source_timestamp_utc`, and `source`.
2. `_asof_window_match()` matches backward on `observation_available_time_utc` (`direction="backward"`, tolerance `5m` for 5m bars, `120m` for Coinbase 1h), eliminating look-ahead bias (`0.0s` lag relative to the configured JISDOR schedule across all `1,414` matched days; `1` boundary/gap day dropped out of `1,415` published days).
3. **Configured Four-Regime JISDOR Schedule (`data/processed/jisdor_schedule_calendar.csv`):**
   - `R1_PRE_APRIL_2021` (2021-01-04 to 2021-04-01, `n = 62` published days): `10:00 WIB` (`03:00 UTC`), window `08:00–09:45 WIB` (SE BI No. 15/18/DPM).
   - `R2_COVID_ADJUSTED_1515` (2021-04-05 to 2022-05-31, `n = 281` published / `280` matched days): `15:15 WIB` (`08:15 UTC`), window `09:00–15:00 WIB` (BI Press Release No. 23/30/DKom pandemic operational hours).
   - `R3_NORMAL_1615_PADG11` (2022-06-02 to 2026-03-31, `n = 920` days): `16:15 WIB` (`09:15 UTC`), window `08:00–16:00 WIB` (BI Press Release No. 23/30/DKom & PADG No. 11/2024).
   - `R4_PADG_07_2026` (2026-04-01 to 2026-11-12, `n = 152` days): `15:15 WIB` (`08:15 UTC`), window `09:00–15:00 WIB` (PADG No. 7 Tahun 2026).

## 3. One-Hour Operational-Hours Sensitivity (`results/diagnostics/jisdor_schedule_audit.csv`)

Because Bank Indonesia does not publish a machine-readable day-by-day log of ad-hoc Ramadan or pandemic operational-hour transition dates, we test shifting all `280` matched `R2` pandemic days by `+60 min` (to `09:15 UTC`) and shifting all `151` June–December 2022 days by `-60 min` (to `08:15 UTC`):

| Schedule Scenario | $N$ | Shifted Days | Mean $B^{tot}$ | Mean $B^{cry}$ | $B^{s\text{-}FX}$ Var Share | Trace (RA) | $\hat{\alpha}_{local}$ ($p$) | $p_{global}$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline 4-Regime Schedule | 1,414 | 0 | `29.73` | `-0.92` | `83.77%` | `150.06` | `-0.396` (`0.0197`) | `0.2847` |
| R2 Pandemic Shifted to 09:15 UTC | 1,414 | 280 | `30.20` | `-0.50` | `82.76%` | `150.50` | `-0.386` (`0.0222`) | `0.3147` |
| All 2021–2022 at 08:15 UTC | 1,414 | 151 | `29.93` | `-0.65` | `84.09%` | `150.49` | `-0.409` (`0.0153`) | `0.2516` |

All empirical conclusions are invariant to 1-hour pandemic/transition schedule uncertainty.
