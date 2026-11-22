# Indonesian Cryptocurrency Regulatory, FX Benchmark, and Fee Timeline (2021–2026)

## 1. Bank Indonesia JISDOR Publication Schedule
- **2021-01-04 to 2021-04-01:** Legacy 10:00 WIB (`03:00 UTC`) spot observation and publication window.
- **2021-04-05 (Effective Date per BI Press Release No. 23/30/DKom, Feb 3, 2021):** JISDOR shifted to an afternoon multi-hour averaging window (`08:00–16:00 WIB` transactions, published `16:15 WIB` / `09:15 UTC`). *Audit note:* Temporary COVID-19 pandemic operating hours occasionally released JISDOR at `15:15 WIB` (`08:15 UTC`) prior to the formal 2026 codification; tested via `-15m`, `+5m`, `+15m`, and daily close sensitivity specifications.
- **2026-04-01 (Effective Date per PADG No. 7 Tahun 2026):** Formal permanent publication window shifted to `15:15 WIB` (`08:15 UTC`).

## 2. Tax, Bourse (CFX), and Platform Fee Regimes (2021–2026)
| Regime ID | Date Span | Platform Fee (Indodax IDR Mkr/Tkr) | Buyer Asset VAT | Seller PPh 22 | CFX+KKI IDR Fee | Route A 2-Leg (Mkr/Tkr bps) | Route B 3-Leg (Mkr/Tkr bps) | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `R1_PRE_TAX_2021` | `2021-01-01` to `2022-04-30` | 0 / 30 bps | 0 bps | 0 bps | 0 bps | 0.0 / 60.0 | 7.5 / 70.0 | `VERIFIED_SECONDARY_AND_ARCHIVE` |
| `R2A_PMK68_0_30` | `2022-05-01` to `2023-08-22` | 0 / 30 bps | 11 bps | 10 bps | 0 bps | 21.0 / 81.0 | 28.5 / 91.0 | `PARTIALLY_VERIFIED` |
| `R2B_INDODAX_PRO_CUT` | `2023-08-23` to `2024-10-31` | 10 / 20 bps | 11 bps | 10 bps | 0 bps | 41.0 / 61.0 | 48.5 / 71.0 | `PARTIALLY_VERIFIED` |
| `R3_CFX_LAUNCH_PMK68` | `2024-11-01` to `2024-12-31` | 10 / 20 bps | 11 bps | 10 bps | 2.22 bps | 45.44 / 65.44 | 52.94 / 75.44 | `VERIFIED_PRIMARY` |
| `R3B_PMK81_VAT12_ADJ` | `2025-01-01` to `2025-07-31` | 10 / 20 bps | 11 bps | 10 bps | 2.22 bps | 45.44 / 65.44 | 52.94 / 75.44 | `VERIFIED_PRIMARY` |
| `R4_PMK50_2025` | `2025-08-01` to `2026-02-28` | 10 / 20 bps | 0 bps | 21 bps | 2.22 bps | 45.44 / 65.44 | 52.94 / 75.44 | `VERIFIED_PRIMARY` |
| `R5_CFX_CUT_MAR2026` | `2026-03-01` to `2026-09-30` | 10 / 20 bps | 0 bps | 21 bps | 1.11 bps | 43.22 / 63.22 | 50.72 / 73.22 | `VERIFIED_PRIMARY` |
| `R6_CFX_CUT_OCT2026` | `2026-10-01` to `2026-11-12` | 10 / 20 bps | 0 bps | 21 bps | 0.555 bps | 42.11 / 62.11 | 49.61 / 72.11 | `VERIFIED_PRIMARY` (5-decimal exact) |

### Key Institutional Audit Notes
- **PMK No. 68/PMK.03/2022 (May 1, 2022):** Established final PPN (0.11% at registered venues, 0.22% unregistered) and final PPh 22 (0.10% registered, 0.20% unregistered).
- **August 22–23, 2023 Indodax Fee Revision (`PARTIALLY_VERIFIED`):** Public notices cut Indodax Pro taker fees by roughly 40% (from 0.30% toward the modern 0.10% maker / 0.20% taker Pro schedule). Exact day-by-day historical maker/taker tiers across 2022–2023 remain partially documented in public snapshots and are bracketed via both `0/30` and `10/20` sensitivity bands.
- **CFX / KKI Fee Launch (Oct 31, 2024 23:59:59 WIB, PERBA 9/2024):** Added 2.22 bps IDR / 4.44 bps USDT clearing & bourse levies (including 11% service VAT).
- **POJK No. 27/2024 (Effective Jan 10, 2025):** Formal supervisory transfer of digital financial assets from BAPPEBTI to OJK.
- **PMK No. 50 Tahun 2025 (Effective Aug 1, 2025):** Eliminated buyer asset VAT (0%) while raising seller final PPh 22 to 0.21% domestically (1.00% foreign platforms). Total symmetric round-trip statutory friction remained 65.44 bps on Route A until CFX cuts, shifting tax incidence strictly onto sellers.
- **SEB No. 001/2026 & Oct 1, 2026 CFX Cuts:** Halved CFX/KKI fees twice (`2.22 -> 1.11 -> 0.555 bps` on IDR pairs), bringing Route A taker statutory cost to `62.11 bps` (`20.555 bps` buy + `41.555 bps` sell), verified to five decimal places against Indodax's live Pro fee table (`0.10555% / 0.20555%` buy, `0.31555% / 0.41555%` sell).
