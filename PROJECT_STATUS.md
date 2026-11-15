# RetailPulse — Project Status

**Version:** 1.5.0  
**Merged to main:** 15 November 2026  
**Repository:** [archivesofkrish/retailpulse-ecommerce-analytics](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics)  
**Feature PR:** [#19 — Experiment Studio and dashboard tab](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/19)  
**Release merge commit:** `86b61c8d34286d4a9886b887ae1b2d47cd7105e6`  
**Pre-merge CI:** [Run 43744875767](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43744875767) — passed  
**Pre-merge CodeQL:** [Run 43744875760](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43744875760) — passed  
**Pre-merge dependency audit:** [Run 43744875879](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43744875879) — passed  
**Post-merge CI:** [Run 43745056436](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43745056436) — passed  
**Post-merge CodeQL:** [Run 43745056629](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43745056629) — passed  
**Post-merge dependency audit:** [Run 43745056442](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43745056442) — passed  
**Status:** v1.5.0 is merged to main. Experiment Studio passed the full pre-merge and post-merge quality/security checks.

## What changed in v1.5.0

### Experiment Studio

- Adds a two-proportion sample-size planner with configurable control rate, minimum detectable effect, two-sided significance level and target power.
- Adds an equal-allocation experiment blueprint, sample-size sensitivity and enrollment-duration estimate using only user-entered eligible participants per day.
- Adds completed-test evaluation with observed conversion rates, absolute/relative lift, p-value, confidence interval and an explicit inconclusive state.
- Adds standalone statistical methodology, assumption notes, validation tests and a styled tenth dashboard section.
- Does not randomise participants, monitor live tests or infer present-day traffic from historical UCI records.

## What changed in v1.4.0

### Customer Value Studio

- Adds a monthly customer-cohort value panel based on each identified customer's first observed invoice month.
- Aggregates invoice lines into distinct customer-invoice orders before computing cohort metrics.
- Reports monthly active share, monthly gross-revenue yield per acquired customer, cumulative observed revenue yield and revenue per active customer.
- Compares 12-calendar-month results only for cohorts with all 12 periods observed; the partial final source month is excluded from that comparison.
- Adds cumulative revenue and retention curves, a cohort value heatmap, cohort-level comparisons and CSV export.
- Adds Phase 3 summary metadata and includes the new CSV in the output SHA-256 manifest.

### Visual and interaction refresh

- Replaces the plain title with a branded gradient hero, clear product positioning and compact capability markers.
- Uses a consistent visual system across the page: soft gradient canvas, dark indigo sidebar, pill-style navigation, elevated KPI cards and refined Plotly chart surfaces.
- Adds a dedicated ninth dashboard tab for customer economics, with an explicit historical-not-forecast label.
- Preserves responsive layouts and Streamlit-native controls.

## Delivered capabilities

- Reproducible UCI Online Retail II ingestion and transaction classification.
- Strict source-schema, customer-identifier and finite-number validation.
- Shared decision-metric validation: percentages must be finite and within 0–100; count inputs must be non-negative integers; booleans are not accepted as numeric metrics.
- Revenue/customer reconciliation and explicit row-classification diagnostics.
- RFM segmentation, repeat-purchase and right-censored cohort analytics.
- Merchandise/operational classification, SKU and country concentration.
- Invoice-level product affinity with support, confidence and lift.
- Customer ID integrity across Phase 3: zero-padded and alphanumeric identifiers remain distinct.
- Correct invoice-level SKU diagnostics: repeated lines for a SKU are aggregated before per-invoice maxima are computed.
- Graceful Phase 3 completion when a dataset has no usable customer IDs or no merchandise SKUs.
- Historical 90-day inactivity backtest with chronological split, temporal embargo and interpretation limits.
- Source SHA-256, pipeline run IDs and core/Phase 3 manifest consistency checks.
- Output-level SHA-256 manifests for generated core exports and Phase 3 tables, reports, summaries and figures.
- Standalone scripts/verify_outputs.py command for machine-readable checksum and cross-manifest validation.
- Phase 3 rejects modified core exports; the dashboard verifies both output manifests before enabling advanced panels.
- Nine-section Streamlit dashboard, including the evidence-based Decision Brief, repeat-purchase Scenario Lab and Customer Value Studio.
- Non-root Docker deployment with read-only data mounts and health-check CI.
- DuckDB SQL examples, notebook walkthrough, executive report and 11-slide presentation.

## Validation evidence

The v1.5.0 release merge commit `86b61c8d34286d4a9886b887ae1b2d47cd7105e6` passed the following post-merge checks:

| Validation | Result |
|---|---|
| Python 3.11 | 107 passed |
| Python 3.12 | 107 passed |
| Python 3.13 | 107 passed |
| Python 3.14 | 107 passed |
| Python 3.14 package build | Source distribution and wheel built successfully |
| Synthetic Phase 3 pipeline | Passed; generated the experiment-compatible dashboard inputs |
| Output verification | 6 checks passed; 13 core and 28 Phase 3 artifacts verified against SHA-256 manifests |
| Docker build and dashboard health | Passed; Streamlit health endpoint responded successfully |
| CodeQL Python analysis | Passed |
| Dependency vulnerability audit | Passed |

The pre-merge PR checks and the post-merge `main` checks both passed. The Python matrix jobs retain JUnit artifacts in GitHub Actions. The full UCI workbook is not stored in GitHub; GitHub Actions therefore validates the synthetic pipeline, while the separate full-workbook validation remains an operator-run check.

The previous v1.4.0 release validation is retained in the repository history and its merge commit was separately validated on Python 3.11–3.14, synthetic Phase 3 generation, Docker health, CodeQL and dependency audit.

## Data and model boundaries

- Dataset findings refer to 1 December 2009–9 December 2011. They are not current retailer performance.
- Revenue is not profit. The Customer Value Studio reports observed historical gross-revenue yield, not projected customer lifetime value (CLV), a forecast or customer profitability.
- The 12-month comparison requires 12 complete observed calendar months. Future periods are not imputed, and incomplete final calendar periods are excluded from mature-cohort comparisons.
- Anonymous sales are excluded from identified-customer cohort analysis.
- The historical inactivity score is not a production churn probability.
- Business insights are transparent diagnostic heuristics and require human review and controlled experiments.
- SHA-256 output manifests detect accidental or uncoordinated changes; they are not signed attestations and do not protect against an actor who can alter both an artifact and its manifest.
- Existing outputs created before v1.2.0 must be rebuilt once to generate the checksum manifests.

## Remaining administrator actions

The repository's main branch remains unprotected and has no configured rulesets. [Issue #14](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/issues/14) tracks the recommended branch protection, required status checks, blocked force pushes/deletions and private vulnerability reporting.

A number of historical feature branches remain. Their changes are represented in the main history; pruning old branch references is a separate GitHub repository-maintenance task.

No GitHub Release or version tag has been published for v1.4.0. The version and changelog are committed to main.

## Reliability hardening retained from earlier releases

- PR [#16](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/16) added shared finite-value validation to transparent decision rules. Percentages outside the inclusive 0–100 range, NaN/infinity, booleans, negative counts and fractional counts are treated as unavailable rather than triggering an insight.
- PR [#17](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/17) added the repeat-purchase Scenario Lab. Its conservative/base/stretch outputs are illustrative assumption-driven scenarios, not a forecast, causal estimate or profit calculation.
