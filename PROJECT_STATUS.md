# RetailPulse — Project Status

**Version:** 1.2.0  
**Merged to main:** 15 November 2026  
**Repository:** [archivesofkrish/retailpulse-ecommerce-analytics](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics)  
**Main commit:** `e3c2586e8a875d08783718bb9e26abf46e45a1c2`  
**Status:** v1.2.0 plus the decision-metric reliability hardening are merged to the default branch. Pre-merge Python, end-to-end, output-integrity, Docker, CodeQL and dependency-audit workflows passed for the hardening change. Post-merge workflows are recorded in GitHub Actions. A GitHub Release/tag has not yet been published.

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
- Standalone `scripts/verify_outputs.py` command for machine-readable checksum and cross-manifest validation.
- Phase 3 rejects modified core exports; the dashboard verifies both output manifests before enabling advanced panels.
- Seven-section Streamlit dashboard, including an evidence-based Decision Brief.
- Non-root Docker deployment with read-only data mounts and health-check CI.
- DuckDB SQL examples, notebook walkthrough, executive report and 11-slide presentation.

## Engineering controls

- Python 3.11–3.14 CI matrix, strict deprecation-warning tests, package build and dependency consistency checks.
- 45 automated tests passing on each supported Python version (180 test executions).
- Synthetic end-to-end analytics tests, including anonymous-only and operational-only data.
- CI runs the synthetic core pipeline, generates Phase 3 outputs and executes the public output-verification CLI.
- JUnit test-result artifacts retained in GitHub Actions.
- CodeQL static analysis, pip-audit vulnerability scanning, and Dependabot proposals for Python, GitHub Actions and Docker.
- GitHub Actions updated to Node 24-compatible checkout and artifact-upload releases.
- Documented security boundaries and data-handling rules.

## Validation evidence

The merged `main` commit `be1ac79` passed all checks:

| Validation | Result |
|---|---|
| Python 3.11 | 45 passed |
| Python 3.12 | 45 passed |
| Python 3.13 | 45 passed |
| Python 3.14 | 45 passed; source and wheel distributions built |
| Synthetic output-verification CLI | 6 checks passed; 13 core and 27 Phase 3 artifacts verified |
| Docker build and dashboard health | Passed |
| CodeQL Python analysis | Passed |
| Dependency vulnerability audit | Passed |

The full UCI workbook validator was previously run by the project owner against a local workbook. The workbook is not stored in GitHub, so GitHub Actions does not freshly rerun that full-data validation.

## Data and model boundaries

- Dataset findings refer to 1 December 2009–9 December 2011. They are not current retailer performance.
- Revenue is not profit; historical spend is not projected CLV; and the inactivity score is not a production churn probability.
- Business insights are transparent diagnostic heuristics and require human review and controlled experiments.
- SHA-256 output manifests detect accidental or uncoordinated changes; they are not signed attestations and do not protect against an actor who can alter both the artifact and its manifest.
- Existing outputs created before v1.2.0 must be rebuilt once to generate the new checksum manifests.

## Remaining administrator actions

The repository's `main` branch is still unprotected and has no configured rulesets. [Issue #14](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/issues/14) tracks the recommended branch protection, required status checks, blocked force pushes/deletions and private vulnerability reporting.

A number of historical feature branches remain. Their changes are represented in the main history; pruning old branch references is a separate GitHub repository-maintenance task.

## Reliability hardening merged after v1.2.0

PR [#16](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/16) adds shared finite-value validation to the transparent decision rules. Percentages outside the inclusive 0–100 range, NaN/infinity, booleans, negative counts and fractional counts are treated as unavailable rather than triggering an insight. Regression tests cover these boundaries and the valid historical insight behaviour remains unchanged. This is a post-v1.2.0 reliability improvement; the project version is not changed by this maintenance patch.
