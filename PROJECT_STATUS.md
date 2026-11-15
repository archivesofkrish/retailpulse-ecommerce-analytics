# RetailPulse — Project Status

**Version:** 1.1.0 development release candidate  
**Updated:** 15 November 2026  
**Repository:** [archivesofkrish/retailpulse-ecommerce-analytics](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics)  
**Status:** Public repository; reliability, lineage, analytics, decision-intelligence and container changes are merged to main. Security automation and Python support-policy hardening are in progress.

## Delivered capabilities

- Reproducible UCI Online Retail II ingestion and transaction classification.
- Strict source-schema, customer-identifier and finite-number validation.
- Revenue/customer reconciliation and explicit row-classification diagnostics.
- RFM segmentation, repeat-purchase and right-censored cohort analytics.
- Merchandise/operational classification, SKU and country concentration.
- Invoice-level product affinity with support, confidence and lift.
- Historical 90-day inactivity backtest with chronological split, temporal embargo and interpretation limits.
- Source SHA-256, pipeline run IDs and core/Phase 3 manifest consistency checks.
- Seven-section Streamlit dashboard, including an evidence-based Decision Brief.
- Non-root Docker deployment with read-only data mounts and health-check CI.
- DuckDB SQL examples, notebook walkthrough, executive report and 11-slide presentation.

## Engineering controls

- Python package metadata and reproducible install configuration.
- Python 3.11–3.14 CI matrix, strict deprecation-warning tests, package build and dependency consistency checks.
- Synthetic end-to-end analytics integration test.
- Docker image build and Streamlit health smoke test.
- JUnit test-result artefacts retained in GitHub Actions.
- CodeQL static analysis, pip-audit vulnerability scanning, and Dependabot proposals for Python, GitHub Actions and Docker.
- Documented security boundaries and data-handling rules.

## Validation boundaries

- The latest full-workbook reconciliation was previously run by the project owner against the local UCI workbook; generated source data are not available in the public repository.
- GitHub Actions validates the synthetic integration path. It does not reproduce a fresh local run of the full UCI workbook unless the owner supplies/downloads that data in a controlled environment.
- Dataset findings refer to 1 December 2009–9 December 2011. They are not current retailer performance.
- Revenue is not profit; historical spend is not projected CLV; and the inactivity score is not a production churn probability.
- Business insights are transparent diagnostic heuristics and require human review and controlled experiments.

## Remaining repository-administrator actions

The GitHub main branch is not yet protected. An administrator should enable branch protection requiring pull requests and the Python 3.11, 3.12, 3.13, 3.14, Docker health, CodeQL and dependency-audit checks, while blocking force-pushes and branch deletion. Private vulnerability reporting should also be enabled in repository security settings.
