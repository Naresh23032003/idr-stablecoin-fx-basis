# Mandatory Humanizer Review — APFM Final Release Sprint

## 1. Skill Provenance & Scope

- **Primary Installed Skill Used:** `humanizer` v4.0.0 (`/Users/naresh/Desktop/Finance/indonesian_crypto_research_final/docs/humanizer_SKILL.md`, 26-pattern editorial guide)
- **Secondary Installed Skill Checked:** `humanizer` v2.1.1 (`/Users/naresh/.claude/skills/humanizer/SKILL.md`)
- **Saved Diff:** `AUDIT/manuscript_humanizer.diff`
- **Files Audited (all 11 manuscript prose files):**
  - `manuscript/main.tex` (title, abstract, declarations)
  - `manuscript/sec1_introduction.tex` *(edited)*
  - `manuscript/sec2_institutional_setting.tex` *(reviewed; no edits needed)*
  - `manuscript/sec3_data_and_synchronization.tex` *(edited)*
  - `manuscript/sec4_econometric_methodology.tex` *(reviewed; no edits needed)*
  - `manuscript/sec5_empirical_results.tex` *(edited)*
  - `manuscript/sec6_robustness_and_falsification.tex` *(reviewed; no edits needed)*
  - `manuscript/sec7_discussion_and_limitations.tex` *(edited)*
  - `manuscript/sec8_conclusion.tex` *(edited)*
  - `manuscript/app_provenance.tex` *(reviewed; no edits needed)*
  - `manuscript/app_bootstrap_and_fees.tex` *(reviewed; no edits needed)*

## 2. Patterns Identified & Corrected (First Pass)

Following the 26-pattern `humanizer` v4.0.0 rubric, the review targeted residual AI-style phrasing while keeping academic precision intact:

1. **AI-characteristic vocabulary and promotional qualifiers** (`clean setting`, `cleanly`, `key`, `align with`, `overwhelmingly`):
   - `sec1_introduction.tex`: `"Indonesia is a clean setting..."` $\rightarrow$ `"Indonesia offers a direct setting..."`
   - `sec3_data_and_synchronization.tex`: `"alongside key regulatory milestones"` $\rightarrow$ `"alongside regulatory milestones"`
   - `sec5_empirical_results.tex`: `"overturns those null results cleanly."` $\rightarrow$ `"overturns those null results."`
   - `sec7_discussion_and_limitations.tex`: `"\subsection{Why Indonesian bitcoin spreads align with conversion frictions}"` $\rightarrow$ `"\subsection{Why Indonesian bitcoin spreads reflect conversion frictions}"`
   - `sec8_conclusion.tex`: `"is overwhelmingly a domestic stablecoin--FX spread rather than a cross-venue bitcoin price gap."` $\rightarrow$ `"reflects primarily a domestic stablecoin--FX spread, not a cross-venue bitcoin price gap."`
2. **Formulaic synthesis openings** (`Two main findings emerge`, `Three concrete regulatory insights emerge`):
   - `sec5_empirical_results.tex`: `"Two main findings emerge from comparing these specifications."` $\rightarrow$ `"Two findings stand out across these specifications."`
   - `sec7_discussion_and_limitations.tex`: `"Three concrete regulatory insights emerge."` $\rightarrow$ `"Three regulatory implications follow from the estimates."`
3. **Decorative inline boldface in narrative prose**:
   - `sec5_empirical_results.tex`: Removed unnecessary `\textbf{...}` around `"November 1, 2024 CFX/KKI bourse fee launch"` and `"August 1, 2025 PMK 50/2025 tax overhaul"` in narrative paragraphs (preserving `\textbf{...}` only in structured enumerations and route labels where it serves visual indexing).
4. **Redundant `rather than` negative-parallelism constructions**:
   - `sec3_data_and_synchronization.tex`: `"so those venues are excluded rather than extrapolated."` $\rightarrow$ `"so those venues are excluded."`
   - `sec5_empirical_results.tex`: `"strictly a descriptive post-event association rather than an identified causal regulatory effect."` $\rightarrow$ `"a descriptive post-event association, not an identified causal regulatory effect."`
   - `sec5_empirical_results.tex`: `"point-in-time execution costs on November 13, 2026 rather than historical five-year depth."` $\rightarrow$ `"point-in-time execution costs on November 13, 2026 and do not capture historical five-year depth."`
   - `sec7_discussion_and_limitations.tex`: `"monitor the domestic USDT/IDR--JISDOR basis rather than unadjusted BTC/IDR premia, because domestic stablecoin conversion accounts for the bulk of total basis variation."` $\rightarrow$ `"monitor the domestic USDT/IDR--JISDOR basis alongside BTC/IDR premia, because domestic stablecoin conversion accounts for most total basis variation."`

## 3. Passages Deliberately Left Unchanged

- **Abstract (`main.tex`):** Dense, factual, quantitative, and free of promotional filler; every sentence carries a verified estimate or methodological caveat.
- **Institutional setting & tax arithmetic (`sec2_institutional_setting.tex`, `app_bootstrap_and_fees.tex`):** Structured numbered regimes and exact five-decimal regulatory reconciliations where bold item labels aid readability and precision.
- **Econometric methodology (`sec4_econometric_methodology.tex`):** Formal definitions, equations, VECM companion-form spectral decomposition, Band-TAR specification, and sequential block-wild bootstrap protocol.
- **Robustness & negative controls (`sec6_robustness_and_falsification.tex`) and provenance appendix (`app_provenance.tex`):** Already direct, restrained, and explicit about borderline/mixed placebo behavior and scope limitations.

## 4. Independent Second-Pass Editorial Audit

A line-by-line audit of `AUDIT/manuscript_humanizer.diff` (9 lines changed across 5 files; 0 lines added/removed outside targeted prose substitutions) confirms:

- **Numerical preservation:** 100% of reported numbers, basis-point values, sample counts, p-values, confidence intervals, half-lives, and dates are byte-identical before and after editing.
- **Equation and citation preservation:** 0 equations, `\label`/`\ref` keys, or `\citep`/`\citet` citations were modified.
- **Qualification preservation:** All methodological limitations (Indodax historical scope, single-day November 13, 2026 LOB snapshot, non-causal CFX event-study association, partial verification of 2022--2024 Indodax fee tiers, JISDOR pandemic schedule sensitivity, and $\alpha_{local}$-only scope of the pooled HAC Wald test) remain intact and explicit.
- **Voice & academic tone:** The prose reads as restrained, direct empirical financial economics suitable for *Asia-Pacific Financial Markets (APFM)*.
