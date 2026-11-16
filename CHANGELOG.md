# Changelog

## Unreleased

- Refresh the engineering audit to reflect merged exact conversion inference, Newcombe-Wilson intervals, sparse allocation exact tests and current CI evidence.

## Unreleased

- Use a two-sided probability-ordered exact binomial allocation test when either expected sample-ratio arm count is below five; retain Pearson chi-square inference for adequate expected counts.
- Fail closed with no p-value when exact allocation support exceeds 100,000 outcomes, and render the selected method or not-computed state explicitly in the dashboard.
- Add sparse-allocation, exact-imbalance and computation-budget regression tests; update Experiment Studio methodology.

## Unreleased

- Use a two-sided probability-ordered Fisher exact test when any pooled-null expected conversion outcome cell is below five; fail closed when the bounded exact-table budget is exceeded.
- Replace the unpooled Wald difference interval with a Newcombe hybrid score interval based on Wilson limits.
- Expose the selected inference method/status and keep the nominal z-test p-value separate from the inferential p-value.
- Add sparse-count, extreme-rate, interval-boundary and exact-computation-budget regression tests; update the Experiment Studio readout.


## Unreleased

- Prevent Experiment Studio from presenting a normal-approximation conversion result as statistically significant when any pooled-null expected success/failure cell is below five; retain the nominal p-value but mark the decision inconclusive.
- Expose expected-cell adequacy diagnostics and add regression coverage for an apparently significant sparse-count comparison.
- Record the source-level audit, dashboard deployment boundary and statistical-method follow-up priorities.


## 1.6.0 - 2026-11-16

- Add a sample-ratio-mismatch diagnostic using a one-degree-of-freedom Pearson chi-square goodness-of-fit test against the pre-declared allocation.
- Support non-equal planned allocations, a conservative p < 0.001 default alert threshold and explicit low-expected-count warnings.
- Integrate expected-versus-observed control/variant allocation visualisation into the Experiment Studio results panel.
- Add finite-input and count validation, tests for balanced, imbalanced, custom-allocation and low-count cases, and experiment-quality documentation.
- Clarify that the allocation diagnostic flags an imbalance signal but cannot prove random assignment, exposure integrity or instrumentation correctness.

## 1.5.0 - 2026-11-15

- Add an Experiment Studio for two-proportion A/B-test sample-size planning with configurable baseline conversion, minimum detectable effect, alpha and power.
- Add sample-size sensitivity analysis, equal-allocation control/variant blueprint cards and an enrollment-duration estimate based only on user-entered eligible participants per day.
- Add post-test conversion comparison with a two-sided pooled z-test, unpooled confidence interval, p-value and explicit decision/limitations.
- Add strict numeric/count validation, regression tests, methodology documentation and dashboard styling.
- Label historical UCI repeat-purchase rates as reference-only; do not infer present-day conversion or traffic from the 2009–2011 dataset.

## 1.4.0 - 2026-11-15

- Add a Customer Value Studio with cohort-comparable 12-calendar-month observed revenue yield, retention curves and a cohort value heatmap.
- Add a reproducible monthly cohort-value export with original cohort size, active customers, revenue yield, cumulative yield and partial-period flags.
- Exclude partial final months from mature-cohort comparisons and preserve right-censored future periods as unobserved.
- Redesign the Streamlit interface with a responsive gradient hero, refined navigation, premium metric cards and cohesive Plotly styling.
- Add reusable cohort-value calculations, regression tests, methodology notes and portfolio walkthrough updates.
- Explicitly distinguish observed historical gross-revenue yield from projected CLV, forecasts and profit.


## 1.3.0 - 2026-11-15

- Add an interactive Repeat-Purchase Scenario Lab to the Streamlit dashboard.
- Add conservative, base and stretch 90-day repeat-rate uplift scenarios with configurable average-order-value assumptions.
- Add incremental expected second-order calculations, gross-revenue sensitivity analysis and CSV export.
- Publish mean and median identified-customer order value in the Phase 3 summary.
- Add reusable, validated scenario calculations and unit/integration tests.
- Document assumptions, empty-state behaviour and interpretation limits; scenario outputs are not forecasts, causal estimates or profit projections.

## 1.2.0 - 2026-11-15

- Add reproducible source ingestion, output manifests, Phase 3 analytics, data-integrity verification and the Professional Edition dashboard.
- Add evidence-backed business insight rules, a historical inactivity backtest, container health validation and extended end-to-end tests.
- Add Python 3.11–3.14 CI, CodeQL and dependency auditing.
