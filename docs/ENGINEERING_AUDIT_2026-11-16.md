# RetailPulse — Engineering Audit

**Review date:** 16 November 2026  
**Reviewed revision:** ce5fabd812704ac39dc64c1282bc6376406d6b68 (branch audit/engineering-baseline-2026-11, initially based on main)  
**Scope:** ingestion and data contracts, analytical transformations, cohort/value metrics, scenario functions, experiment planning/evaluation, provenance, dashboard deployment posture and CI quality gates.  
**Review type:** source-level engineering review and targeted statistical hardening. This is not an independent financial audit or causal-inference certification.

## Executive summary

RetailPulse has a comparatively mature analytical foundation: explicit transaction classification, customer identity preservation, invoice-grain aggregation, temporal backtesting, right-censored cohorts, output manifests and clear historical-data limitations. The highest-value remaining risks are inferential: the completed-experiment evaluator used the normal approximation without first checking expected conversion outcome counts, and its confidence interval is a Wald interval. Deployment also remains intentionally unauthenticated.

This branch fixes the first issue by preventing a sparse-count normal-approximation result from being labelled statistically significant. The nominal p-value remains available but is explicitly separated from the final decision.

## Findings

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| RP-01 | Medium | Experiment inference | The pooled two-proportion z-test could return a nominally significant result even when expected success/failure cells were sparse. The allocation diagnostic checked arm-size counts, not outcome-cell counts. | **Fixed in this branch** |
| RP-02 | Medium | Confidence intervals | The post-test difference interval uses an unpooled Wald normal approximation. It can have poor coverage near 0%/100% rates and with small samples. | Known limitation; score/exact intervals are next priority |
| RP-03 | High (deployment boundary) | Dashboard access | The Streamlit dashboard has no authentication or role-based access control. The current SECURITY.md correctly says not to expose it directly to the public internet. | Explicit limitation; retain local-only posture until protected deployment exists |
| RP-04 | Medium | Dataset freshness | The supplied UCI Online Retail II workbook covers December 2009–December 2011. Outputs are a reproducible historical case study, not current retailer telemetry or a live decision feed. | Explicit limitation; retain prominent labelling |
| RP-05 | Medium | Commercial scenarios | Repeat-purchase scenario outputs are assumption-driven gross-revenue sensitivities, not causal treatment effects, forecasts, contribution margin or profit. | Explicit limitation; preserve guardrails |
| RP-06 | Low | Pipeline scale | The pipeline relies on in-memory dataframe processing. The configured historical workbook is manageable for the current project, but larger multi-year/multi-tenant data will need measured memory and runtime budgets before scale claims. | Benchmark before expanding scope |

## Implemented hardening in this branch

- Calculate the four expected outcome cells under the pooled null conversion rate: control successes/failures and variant successes/failures.
- Require every expected outcome cell to be at least five before treating the normal-approximation z-test as an inferential decision.
- Retain the nominal p-value for transparency, but expose nominal significance separately from the guarded significance decision.
- Force an Inconclusive decision when the normal approximation is inadequate, including the reason and the minimum expected cell count.
- Add a regression test for 0/5 versus 5/5: a small-sample nominal p-value must not be presented as a dependable significant finding.
- Update Experiment Studio methodology, README and changelog.

The five-count rule is a conservative screening heuristic, not a universal theorem that validates every other normal approximation. It does not fix Wald interval coverage, sequential peeking, multiplicity, clustering, non-compliance or poor randomisation.

## Positive controls observed

- Core ingestion uses schema validation, finite-number checks and explicit row classifications.
- Customer identifiers remain opaque strings; invoice/customer metrics are computed at the documented analytical grain.
- Source and derived outputs are fingerprinted and checked for lineage/freshness before advanced outputs are trusted.
- Cohort value is labelled as observed historical revenue yield; future cohort periods are not imputed.
- The inactivity model uses a chronological holdout and 90-day embargo and is documented as a historical backtest, not a production churn score.
- Experiment planning and readout document independence, binary outcome and other statistical assumptions.
- Docker deployment runs non-root and uses read-only data mounts; the dashboard remains unauthenticated and the security policy warns against public exposure.
- CI covers Python 3.11–3.14, tests, CodeQL, dependency audit and a container health smoke test.

## Validation required before merge

Run the complete Python 3.11–3.14 CI matrix, strict deprecation-warning tests, synthetic core/Phase 3 pipeline and output-integrity verification, Docker dashboard health smoke test, CodeQL and dependency audit on this exact branch. No test result for this branch is claimed until GitHub Actions reports it.

## Next development priorities

1. Add exact two-proportion inference for sparse-count experiments and Wilson/Newcombe confidence intervals; compare output against independent reference cases.
2. Add sensitivity tests around expected-cell boundaries, extreme conversion rates and allocation imbalance.
3. Add explicit statistical status and assumptions to dashboard exports so CSV users cannot lose the caveats shown in the UI.
4. Profile peak memory and runtime on the full UCI workbook, then establish reproducible performance budgets.
5. Consider a protected multi-user deployment only after adding authentication, authorization and operational data-access controls.
6. Keep all predictive customer-value work separate from observed cohort yields, and validate forecasts on chronological holdouts before presenting them as predictive.

## Security and interpretation boundary

RetailPulse is an analytical portfolio project. It does not ingest a live retailer feed, authenticate dashboard viewers, guarantee causal experiment conclusions, provide accounting profit, or produce production-ready churn scores. Historical, observed, inferential and assumption-driven values must remain clearly distinguished.