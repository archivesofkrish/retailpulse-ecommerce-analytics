# Changelog

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
