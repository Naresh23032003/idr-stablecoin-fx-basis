# Market Scope and Arbitrage Claims Audit

**Date:** 2026-11-24  

## 1. Empirical Scope Boundaries

1. **Venue Coverage:** Pre-November 2025 historical evidence characterizes **Indodax** specifically (Indonesia's longest-running high-volume rupiah spot exchange), as Tokocrypto, Pintu, and Reku lacked downloadable multi-year historical OHLCV endpoints. Cross-venue validation against Binance's direct IDR pairs covers the final **349 days** (November 29, 2025–November 12, 2026; $N = 100,362$ 5-minute bars). The title, abstract, introduction, and conclusion must explicitly frame the long-horizon evidence as **Indodax-based** rather than market-wide Indonesian price discovery.
2. **JISDOR Non-Executability:** Bank Indonesia's JISDOR is a daily transaction-weighted interbank reference fixing, **not** an executable offshore USD/IDR quote. Consequently, $B_t^{stablecoin\text{-}FX}$ measures the statistical wedge between onshore `USDT/IDR` and the official reference rate, not a frictionless executable FX arbitrage profit.
3. **Distinguishing Six Concepts:**
   - *Statistical price wedge* ($B_t^{total}, B_t^{crypto}, B_t^{stablecoin\text{-}FX}$)
   - *Cointegration relationship* (long-run equilibrium between Indodax IDR prices and FX-converted global prices)
   - *Regulatory cost reconstruction* (statutory tax + CFX + Indodax Pro fee bands)
   - *Order-book snapshot* (single-day November 13, 2026 depth slippage)
   - *Executable arbitrage opportunity* vs. *Realized arbitrage profitability* (which cannot be claimed over 2021–2026 without historical L2 order-book replay, banking wire spreads, and capital-transfer latency).
4. **Title & Abstract Assessment:** The current title (*"Where does the Indonesian cryptocurrency premium come from? Currency conversion, the stablecoin--FX basis, and transaction costs"*) is clear, but the abstract and introduction must explicitly state that long-horizon evidence comes from **Indodax** (with 349-day Binance IDR cross-checks) and must not equate fee-band containment or the Nov 2024 CFX association with causal or executable arbitrage claims.
