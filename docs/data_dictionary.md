# Data Dictionary

## 1. Primary Synchronized Datasets (`data/processed/{btc,eth,xrp}_jisdor_sync_primary.csv`)
| Column | Unit / Type | Definition | Provenance |
| :--- | :--- | :--- | :--- |
| `date` | ISO Date (`YYYY-MM-DD`) | Official Bank Indonesia JISDOR publication date (business days only) | `bi_jisdor` |
| `pub_timestamp_utc` | UTC ISO Timestamp | Regime-specific BI JISDOR release instant (`03:00`, `09:15`, or `08:15 UTC`) | `config/sampling.yaml` |
| `jisdor_idr_usd` | IDR per 1 USD (`float`) | Official Bank Indonesia JISDOR fixing rate; never forward-filled | Bank Indonesia Excel |
| `spot_idr_usd` | IDR per 1 USD (`float`) | Continuous indicative spot FX close (`IDR=X`); sensitivity only | Yahoo Finance |
| `ecb_idr_usd` | IDR per 1 USD (`float`) | ECB reference FX benchmark (`16:00 CET`); cross-validation only | Frankfurter API |
| `eur_usd` | USD per 1 EUR (`float`) | Placebo FX benchmark used strictly in falsification tests | Yahoo Finance |
| `indodax_close` | IDR per coin (`float`) | Indodax spot close (`{BTC,ETH,XRP}IDR`) at first 5m bar >= `pub_timestamp_utc` ($\le 5$m) | Indodax `/tradingview/history_v2` |
| `indodax_volume` | Base coin (`float`) | 5m bar traded volume; zero-volume bars flagged as `is_stale_indodax` | Indodax `/tradingview/history_v2` |
| `usdtidr_close` | IDR per 1 USDT (`float`) | Indodax `USDTIDR` 5m bar close synchronized to `pub_timestamp_utc` | Indodax `/tradingview/history_v2` |
| `binance_close` | USDT per coin (`float`) | Binance `{BTC,ETH,XRP}USDT` 5m bar close synchronized to `pub_timestamp_utc` | `data.binance.vision` |
| `cb_usdtusd_close` | USD per 1 USDT (`float`) | Coinbase `USDT-USD` 1h bar close (`[t-60m, t+60m]` tolerance) for peg wedge | Coinbase Public API |
| `b_total_bps` | Basis points (`1e4 * log`) | $10^4 [\ln P_t^{IDR} - \ln P_t^{USDT} - \ln S_t^{IDR/USD}]$ (total basis vs. JISDOR) | `src/variables/basis.py` |
| `b_crypto_bps` | Basis points (`1e4 * log`) | $10^4 [\ln P_t^{IDR} - \ln P_t^{USDT} - \ln U_t^{IDR/USDT}]$ (pure crypto leg) | `src/variables/basis.py` |
| `b_stablecoin_fx_bps` | Basis points (`1e4 * log`) | $10^4 [\ln U_t^{IDR/USDT} - \ln S_t^{IDR/USD}]$ (local stablecoin-FX basis) | `src/variables/basis.py` |
| `usd_usdt_wedge_bps` | Basis points (`1e4 * log`) | $10^4 \ln W_t^{USD/USDT}$ (explicit Coinbase stablecoin peg deviation) | `src/variables/basis.py` |

## 2. Intraday 5-Minute & 1-Minute Panels (`data/processed/*_5m_panel_2021_2026.csv.gz`, `btc_1m_2026_panel.csv.gz`)
- `timestamp_utc`: Exact 5m / 1m UTC bar open timestamp (`2021-01-01` to `2026-11-12` for 5m, `N=616,683`; `2026-01-01` to `2026-11-12` for 1m, `N=455,040`).
- `b_crypto_bps`: $10^4 [\ln P_t^{IDR} - \ln P_t^{USDT} - \ln U_t^{IDR/USDT}]$ invariant to banking holidays and JISDOR closure.
- `is_active_both_indo`: Boolean indicator requiring strictly positive traded volume on both local `BTC/IDR` and `USDT/IDR` bars (`98.13%` of all 5m bars).
