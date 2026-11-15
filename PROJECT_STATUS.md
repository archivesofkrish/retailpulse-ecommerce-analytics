# RetailPulse — Project Status

**Version:** 1.1.0 development release candidate  
**Updated:** 15 November 2026  
**Repository:** [archivesofkrish/retailpulse-ecommerce-analytics](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics)  
**Status:** All planned v1.1.0 engineering increments described below are merged to main. Final repository-administrator settings remain outstanding.

## Delivered capabilities

- Reproducible UCI Online Retail II ingestion and transaction classification.
- Strict source-schema, customer-identifier and finite-number validation.
- Revenue/customer reconciliation and explicit row-classification diagnostics.
- RFM segmentation, repeat-purchase and right-censored cohort analytics.
- Merchandise/operational classification, SKU and country concentration.
- Invoice-level product affinity with support, confidence and lift.
- Customer ID integrity across Phase 3: zero-padded and alphanumeric identifiers remain distinct.
- Correct invoice-level SKU diagnostics: repeated lines for a SKU are aggregated before per-invoice maxima are computed.
- Graceful Phase 3 completion when a dataset has no usable customer IDs or no merchandise SKUs.
- Historical 90-day inactivity backtest with chronological split, temporal embargo and interpretation limits.
- Source SHA-256, pipeline run IDs and core/Phase 3 manifest consistency checks.
- Seven-section Streamlit dashboard, including an evidence-based Decision Brief.
- Non-root Docker deployment with read-only data mounts and health-check CI.
- DuckDB SQL examples, notebook walkthrough, executive report and 11-slide presentation.

## Engineering controls

- Python package metadata and reproducible install configuration.
- Python 3.11–3.14 CI matrix, strict deprecation-warning tests, package build and dependency consistency checks.
- 36 automated tests passing on each supported Python version in the latest full suite.
- Synthetic end-to-end analytics integration tests, including anonymous-only and operational-only data.
- Docker image build and Streamlit health smoke test.
- JUnit test-result artefacts retained in GitHub Actions.
- CodeQL static analysis, pip-audit vulnerability scanning, and Dependabot proposals for Python, GitHub Actions and Docker.
- Documented security boundaries and data-handling rules.

## Validation boundaries

- The latest GitHub Actions synthetic/regression suite passed on Python 3.11, 3.12, 3.13 and 3.14; Docker health, CodeQL and dependency audit checks also passed on the latest merged increment.
- The full UCI workbook validator was previously run by the project owner against a local workbook. The workbook is not stored in GitHub, so GitHub Actions does not freshly re-run that full-data validation.
- Dataset findings refer to 1 December 2009–9 December 2011. They are not current retailer performance.
- Revenue is not profit; historical spend is not projected CLV; and the inactivity score is not a production churn probability.
- Business insights are transparent diagnostic heuristics and require human review and controlled experiments.

## Remaining repository-administrator actions

The GitHub main branch is not yet protected and repository rulesets are empty. An administrator should enable branch protection requiring pull requests and the Tests (Python 3.11), Tests (Python 3.12), Tests (Python 3.13), Tests (Python 3.14), Docker health, CodeQL and dependency-audit checks. Block force-pushes and branch deletion. Enable private vulnerability reporting in repository security settings.

Several historical feature branches remain after their work was merged. They are not required for the current main branch; prune them through GitHub after confirming they are no longer needed for audit/history.
