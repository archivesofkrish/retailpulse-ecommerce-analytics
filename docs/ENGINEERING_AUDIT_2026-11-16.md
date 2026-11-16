# RetailPulse — Engineering Audit

**Review date:** 16 November 2026  
**Reviewed revision:** 187923fc06bdaa9ce22578dc4a743796ac078efb (current main after PR #24)  
**Scope:** ingestion and data contracts, analytical transformations, cohort/value metrics, scenario functions, experiment planning/evaluation, sample-ratio diagnostics, provenance, dashboard deployment posture and CI quality gates.  
**Review type:** source-level engineering review and targeted statistical hardening. This is not an independent financial audit or causal-inference certification.

## Executive summary

RetailPulse has a mature analytical foundation: explicit transaction classification, customer identity preservation, invoice-grain aggregation, temporal backtesting, right-censored cohorts, output manifests and clear historical-data limitations. The mainline now uses Fisher exact inference for sparse conversion-outcome cells, a Newcombe-Wilson score interval, and an exact binomial allocation test for sparse sample-ratio diagnostics. The primary remaining risks are deployment access control, unmeasured scale limits, and the interpretation boundaries of historical data and assumption-driven scenarios.

## Findings

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| RP-01 | Medium | Experiment inference | The pooled two-proportion z-test could return a nominally significant result even when expected success/failure cells were sparse. The allocation diagnostic checked arm-size counts, not outcome-cell counts. | **Fixed: sparse cells use Fisher exact inference; bounded fallback fails closed** |
| RP-02 | Medium | Confidence intervals | The original post-test difference interval used an unpooled Wald normal approximation with poor coverage near extreme rates. | **Fixed: Newcombe hybrid score interval based on Wilson limits** |
| RP-03 | High (deployment boundary) | Dashboard access | The Streamlit dashboard has no authentication or role-based access control. The current SECURITY.md correctly says not to expose it directly to the public internet. | Explicit limitation; retain local-only posture until protected deployment exists |
| RP-04 | Medium | Dataset freshness | The supplied UCI Online Retail II workbook covers December 2009–December 2011. Outputs are a reproducible historical case study, not current retailer telemetry or a live decision feed. | Explicit limitation; retain prominent labelling |
| RP-05 | Medium | Commercial scenarios | Repeat-purchase scenario outputs are assumption-driven gross-revenue sensitivities, not causal treatment effects, forecasts, contribution margin or profit. | Explicit limitation; preserve guardrails |
| RP-06 | Low | Pipeline scale | The pipeline relies on in-memory dataframe processing. The configured historical workbook is manageable for the current project, but larger multi-year/multi-tenant data will need measured memory and runtime budgets before scale claims. | Benchmark before expanding scope |
| RP-07 | Medium | Sample-ratio inference | The allocation diagnostic previously marked sparse expected arm counts as unreliable but still returned and displayed the Pearson chi-square p-value. | **Fixed in PR #24: sparse allocations use exact binomial inference; over-budget cases return no p-value** |

## Implemented hardening on main

- Calculate the four expected outcome cells under the pooled null conversion rate: control successes/failures and variant successes/failures.
- Require every expected outcome cell to be at least five before treating the normal-approximation z-test as an inferential decision.
- Retain the nominal p-value for transparency, but expose nominal significance separately from the guarded significance decision.
- Switch to a probability-ordered two-sided Fisher exact test when the normal approximation is inadequate; fail closed if the exact support exceeds 100,000 tables.
- Add a regression test for 0/5 versus 5/5: sparse conversion outcomes use Fisher exact inference rather than an unguarded z-test.
- Replace the unpooled Wald conversion-difference interval with a Newcombe hybrid score interval based on Wilson limits.
- Use a two-sided, probability-ordered exact binomial test for sample-ratio diagnostics when either expected arm count is below five.
- Bound exact allocation support to 100,000 possible counts and fail closed with no p-value when that bound is exceeded.
- Update Experiment Studio to show the selected allocation method and display Not computed when the exact-test budget is exceeded.

The five-count rules are conservative method-selection heuristics, not universal guarantees for every experiment design. The Newcombe-Wilson interval remains an approximation. None of these methods corrects sequential peeking, multiplicity, clustering, non-compliance, selection bias or poor randomisation.

## Positive controls observed

- Core ingestion uses schema validation, finite-number checks and explicit row classifications.
- Customer identifiers remain opaque strings; invoice/customer metrics are computed at the documented analytical grain.
- Source and derived outputs are fingerprinted and checked for lineage/freshness before advanced outputs are trusted.
- Cohort value is labelled as observed historical revenue yield; future cohort periods are not imputed.
- The inactivity model uses a chronological holdout and 90-day embargo and is documented as a historical backtest, not a production churn score.
- Experiment planning and readout document independence, binary outcome and other statistical assumptions.
- Docker deployment runs non-root and uses read-only data mounts; the dashboard remains unauthenticated and the security policy warns against public exposure.
- CI covers Python 3.11–3.14, tests, CodeQL, dependency audit and a container health smoke test.

## Validation evidence

PR #24 passed all eight checks on its exact head revision: Python 3.11–3.14, Docker build/dashboard health, CodeQL and dependency audit. The merged `main` revision `187923fc06bdaa9ce22578dc4a743796ac078efb` also passed the post-merge RetailPulse CI, CodeQL and dependency-audit workflows. See [main CI](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43862492516), [CodeQL](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43862492380) and [dependency audit](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43862492379).

## Next development priorities

1. Add independent reference-value/property-based checks for the Fisher exact, exact binomial and Newcombe interval implementations.
2. Add explicit statistical method/status and assumptions to dashboard exports so CSV users cannot lose the caveats shown in the UI.
3. Profile peak memory and runtime on the full UCI workbook, then establish reproducible performance budgets before adopting larger-data infrastructure.
4. Consider a protected multi-user deployment only after adding authentication, authorization and operational data-access controls.
5. Keep predictive customer-value work separate from observed cohort yields, and validate any forecast on chronological holdouts before presenting it as predictive.

## Security and interpretation boundary

RetailPulse is an analytical portfolio project. It does not ingest a live retailer feed, authenticate dashboard viewers, guarantee causal experiment conclusions, provide accounting profit, or produce production-ready churn scores. Historical, observed, inferential and assumption-driven values must remain clearly distinguished.