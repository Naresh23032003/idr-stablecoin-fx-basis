# Stale-Price and Zero-Volume Audit (5-Minute Panel)

**Date:** 2026-11-24  
**Source:** `results/diagnostics/stale_price_sensitivity_5m.csv`  

## 1. Regular Clock-Time Grid vs. Stale-Bar Filtering

In the primary regular 5-minute panel ($N = 616,683$ bars), `11,527` bars (`1.87%`) have zero volume on Indodax `BTC/IDR` or `USDT/IDR`. We test sensitivity to removing prolonged zero-volume runs on the regular grid versus the irregular active-only subsample:

| Sample Specification | $N$ | Dropped | $\hat{\alpha}_{\mathrm{BTC/IDR}}$ ($p$) | $\hat{\alpha}_{\mathrm{BTC/USDT}}$ ($p$) | Adj. Share `BTC/IDR` | Companion HL | IRF Local HL |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full Regular 5m Grid (Primary) | 616,683 | 0 | `-0.0445` (`0.0000`) | `0.0011` (`0.4179`) | `79.95%` | `25.08` | `1.13` |
| Exclude Zero-Vol Runs $>12$ bars (1h) | 614,126 | 2,557 | `-0.0571` (`0.0000`) | `0.0010` (`0.5443`) | `80.22%` | `19.61` | `1.00` |
| Exclude Zero-Vol Runs $>6$ bars (30m) | 613,863 | 2,820 | `-0.0572` (`0.0000`) | `0.0010` (`0.5652`) | `80.28%` | `19.62` | `0.99` |
| Exclude Zero-Vol Runs $>3$ bars (15m) | 613,295 | 3,388 | `-0.0572` (`0.0000`) | `0.0010` (`0.5601`) | `80.26%` | `19.62` | `0.99` |
| Irregular Active-Only (Sensitivity) | 605,156 | 11,527 | `-0.0579` (`0.0000`) | `0.0010` (`0.5850`) | `80.26%` | `19.42` (obs) | `0.99` (obs) |

## 2. Interpretation

- **Retain regular clock-time grid as primary:** It preserves exact 5-minute lag units without silently compressing time.
- **Role of prolonged outages:** Dropping the `2,557` prolonged zero-volume bars ($>1$ hour, exchange maintenance/outages) increases `|alpha_BTC/IDR|` from `0.0445` to `0.0571` and lowers the companion-root half-life from `25.08` to `19.61` bars, while leaving the ~80% Indodax adjustment share and Binance weak exogeneity ($p > 0.41$) invariant.
- **Irregular active-only sample:** Treated strictly as an event-time sensitivity check whose lag units are active observations, not 5-minute clock intervals.
