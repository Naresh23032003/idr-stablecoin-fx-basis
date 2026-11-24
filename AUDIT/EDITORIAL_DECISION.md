# Editorial Decision (Asia-Pacific Financial Markets Simulation)

**Manuscript:** *Where does the Indonesian cryptocurrency premium come from? Currency conversion, the stablecoin--FX basis, and transaction costs*  
**Decision:** **Acceptable for Submission** (with all remaining limitations transparently disclosed)

## Summary Assessment
The initial manuscript contained three critical technical defects (a 5-minute look-ahead bias in candle-to-JISDOR matching, a deterministic-term mismatch between the manuscript's `ci` equations and the code's `co` implementation, and single-rank `r=0` bootstrap testing) alongside over-interpreted half-life dynamics and an unqualified CFX event-study claim.

All critical defects have been corrected in executable code, datasets have been rebuilt from raw archives, all models and robustness checks have been rerun, and the manuscript has been revised so that every reported number traces directly to `results/` and every claim stays within what the evidence establishes. Remaining structural constraints (Indodax-only pre-2025 coverage, partially archived 2022–2024 USDT fee tiers, single-day November 13, 2026 order-book depth, and non-causal event-window association) are explicitly disclosed in the Abstract, Results, Discussion, and Limitations.
