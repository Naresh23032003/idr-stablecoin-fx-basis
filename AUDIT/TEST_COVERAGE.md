# Automated Test Coverage Audit

**Date:** 2026-11-24  
**Test Suite:** `tests/test_core_methodology.py`, `tests/test_econometrics.py`, `tests/test_manuscript_consistency.py`, `tests/test_pipeline_and_manuscript.py`  

## Coverage Matrix

| Area | Test Function(s) | Status |
|---|---|---|
| Unit & sign checks | `test_unit_inversion_rejected`, `test_non_positive_price_rejected` | Passing |
| Basis & variance identity | `test_basis_identity_and_variance_identity`, `test_processed_primary_panel_integrity` | Passing |
| JISDOR historical schedule | `test_jisdor_historical_schedule_transitions` | Passing |
| No-look-ahead candle matching | `test_asof_window_matching_and_tolerance` (updated for `observation_available_time_utc` backward match) | Passing |
| Fee arithmetic & regime lookup | `test_fee_arithmetic_oct_2026_matches_published_indodax_pro`, `test_fee_regime_date_lookup_no_gaps` | Passing |
| Johansen RA/CL scaling | `test_johansen_reinsel_ahn_and_cheung_lai_scaling` | Passing |
| Engle-Granger vs fixed-(1,-1) | `test_engle_granger_vs_fixed_vector` | Passing |
| Block-wild bootstrap & MC DGP | `test_bootstrap_reproducibility_and_controlled_dgp` | Passing |
| Sequential bootstrap & `co`/`ci` | `test_sequential_bootstrap_and_deterministic_specs` | Passing |
| Unit-root suite | `test_unit_root_suite_stationary_vs_random_walk` | Passing |
| Manuscript hygiene & numbers | `test_no_em_dashes_or_ai_buzzwords_in_manuscript`, `test_manuscript_headline_numbers_match_results`, `test_no_todo_or_missing_inputs_in_manuscript` | Passing |
| Pipeline artifacts & PDF | `test_source_coverage_and_zero_synthetic_fill`, `test_generated_tables_figures_and_manuscript` | Passing |
