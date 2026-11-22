# Source Register & Licensing Notes

All raw market datasets and regulatory instruments were retrieved directly via public endpoints during `2026-11-13` with SHA-256 verification recorded per artifact in `data/raw/*_manifest.json` and `data/source_coverage_matrix.csv`.

1. **Bank Indonesia JISDOR (`https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/Default.aspx`)**
   - Official Indonesian interbank USD/IDR reference rate (1,415 business days, `2021-01-04` to `2026-11-12`), plus `PADG No. 7 Tahun 2026`, `Press Release No. 23/30/DKom`, and official JISDOR FAQ PDF archived locally under `data/raw/regulatory/` (`pajak.go.id` returned an 803-byte redirect shell, so PMK 68/2022 and PMK 50/2025 rates were cross-verified against official DJP/Kemenkeu legal texts and live Indodax CFX fee disclosures).
2. **Indodax Public Market APIs (`https://indodax.com/tradingview/history_v2`, `https://indodax.com/api/pairs`, `https://indodax.com/api/depth/`)**
   - Public TradingView OHLCV history (`1D`, `5m`, `1m`) for `BTCIDR`, `USDTIDR`, `BTCUSDT`, `ETHIDR`, `XRPIDR` (`2021-01-01` to `2026-11-12`, zero request errors) and live depth snapshot + published Pro fee schedule.
3. **Binance Public Data Vision (`https://data.binance.vision/data/spot/monthly/klines/`)**
   - Official compressed monthly historical archives with upstream `.CHECKSUM` SHA-256 verification for `BTCUSDT`, `ETHUSDT`, `XRPUSDT`, `USDCUSDT`, `BTCBIDR` (ended May 2024), `USDTBIDR` (ended May 2024), `BTCIDR` (started Nov 2025), and `USDTIDR` (started Nov 2025). Live depth via `api.binance.com/api/v3/depth`.
4. **Coinbase Exchange & Kraken Public REST APIs**
   - `api.exchange.coinbase.com/products/USDT-USD/candles` (`1D` and `1h`, since May 4, 2021), `BTC-USD`, `ETH-USD`, and `api.kraken.com/0/public/OHLC?pair=USDTUSD` (720-bar API cap documented).
5. **Global Spot FX Cross-Checks**
   - Yahoo Finance `IDR=X` and `EURUSD=X` (`query1.finance.yahoo.com/v8/finance/chart/`) and European Central Bank Frankfurter API (`api.frankfurter.app`).
6. **Non-Applicable Domestic Venues (Tested Live & Logged)**
   - Tokocrypto `/open/v1/market/klines` returned empty payloads; Pintu (`api.pintu.co.id/v2/trade/price-changes`) and Reku (`api.reku.id/v2/ticker`) expose only current snapshot quotes without historical candle endpoints. Excluded transparently from historical time-series panels.
