# Institutional and Historical Fee Evidence Audit

**Date:** 2026-11-24  
**Source:** `src/fees/fee_schedule.py`, `src/fees/orderbook_economics.py`, `docs/source_register.md`  

## 1. Classification of Fee Inputs

1. **Directly Observed / Primary-Verified Historical Rates:**
   - **Pre-Tax Baseline (R1: 2021-01-01 to 2022-04-30):** Indodax IDR spot `0 bps` maker / `30 bps` taker; no special crypto VAT/PPh.
   - **PMK No. 68/PMK.03/2022 (2022-05-01 to 2025-07-31):** `11 bps` buyer PPN + `10 bps` seller PPh 22 on registered domestic exchanges (`22 bps` / `20 bps` unregistered).
   - **PERBA No. 9/2024 & CFX/KKI SEB 003/004 (2024-11-01 to 2026-02-28):** `2.00 bps` base IDR (`2.22 bps` VAT-inclusive), `4.00 bps` base USDT (`4.44 bps` VAT-inclusive), verified via Indodax Help Center (`39505059756569`, effective `2024-10-31 23:59:59 WIB`).
   - **PMK No. 50 Tahun 2025 (2025-08-01 onward):** `0 bps` buyer asset VAT + `21 bps` seller PPh 22 domestic (`100 bps` foreign).
   - **CFX/KKI Stage-1 Cut (2026-03-01 to 2026-09-30):** SEB No. 001/SEB/CFX-KKI/SPOT/II/2026 halved CFX/KKI to `1.11 bps` IDR / `2.22 bps` USDT (VAT-inclusive).
   - **CFX/KKI Stage-2 Cut (2026-10-01 to 2026-11-12):** `0.555 bps` IDR / `1.11 bps` USDT (VAT-inclusive); verified to 5 decimal places against Indodax's live October 2026 Pro schedule (`0.10555% / 0.20555%` buy, `0.31555% / 0.41555%` sell, `0.2511% / 0.2811%` USDT).
2. **Partially Verified / Reconstructed Intermediate Schedules:**
   - **Regimes R2A & R2B (2022-05-01 to 2024-10-31):** Statutory taxes (`11 + 10 = 21 bps`) are primary-verified, but day-by-day Indodax Pro maker/taker tiers on USDT pairs and the exact transition from `0/30` to `10/20` around August 22–23, 2023 are only partially preserved in public archives (`PARTIALLY_VERIFIED` flag in `fee_schedule.py`).
   - **Sensitivity Bounds:** Evaluated across `[61.0, 81.0]` bps Route A taker cost for May 2022–October 2024 (re-verified in `variance_decomposition.json`).
3. **Point-in-Time Snapshot Depth:**
   - Limit-order book slippage (`orderbook_microstructure_snapshot.csv`, `route_specific_execution_costs.csv`) comes exclusively from a **single live snapshot on November 13, 2026** and is never extrapolated backward to 2021–2026.
