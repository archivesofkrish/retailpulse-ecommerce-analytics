# RetailPulse — Project Status

**Version:** 1.2.0 release candidate  
**Updated:** 15 November 2026  
**Repository:** https://github.com/archivesofkrish/retailpulse-ecommerce-analytics  
**Status:** The v1.2.0 integrity feature is merged to main; release metadata and validation records are being aligned in this release-candidate change.

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
- Output-level SHA-256 manifests for generated core exports and Phase 3 tables, reports, summaries and figures.
- Phase 3 rejects modified core exports; the dashboard verifies both output manifests before enabling advanced panels.
- Seven-section Streamlit dashboard, including an evidence-based Decision Brief.
- Non-root Docker deployment with read-only data mounts and health-check CI.
- DuckDB SQL examples, notebook walkthrough, executive report and 11-slide presentation.

## Engineering controls

- Python package metadata and supported-runtime configuration.
- Python 3.11–3.14 CI matrix, strict deprecation-warning tests, package build and dependency consistency checks.
- 41 automated tests passing on each supported Python version in PR #12 (164 test executions).
- Synthetic end-to-end analytics tests, including anonymous-only and operational-only data.
- Docker image build and Streamlit health smoke test.
- JUnit test-result artifacts retained in GitHub Actions.
- CodeQL static analysis, pip-audit vulnerability scanning, and Dependabot proposals for Python, GitHub Actions and Docker.
- Documented security boundaries and data-handling rules.

## Validation evidence

- PR #12 passed all eight checks before merge: four Python test/build jobs, Docker health, CodeQL, dependency audit and the CodeQL analysis check.
- The complete UCI workbook validator was previously run by the project owner against a local workbook. The workbook is not stored in GitHub, so GitHub Actions does not freshly rerun that full-data validation.
- The latest merged main-branch workflows are rerunning after the merge; consult GitHub Actions for final default-branch results.

## Data and model boundaries

- Dataset findings refer to 1 December 2009–9 December 2011. They are not current retailer performance.
- Revenue is not profit; historical spend is not projected CLV; and the inactivity score is not a production churn probability.
- Business insights are transparent diagnostic heuristics and require human review and controlled experiments.
- SHA-256 output manifests detect accidental or uncoordinated changes; they are not signed attestations and do not protect against an actor who can alter both the artifact and its manifest.
- Existing outputs created before v1.2.0 must be rebuilt once to generate the new checksum manifests.

## Remaining repository-administrator actions

The GitHub main branch is not yet protected and repository rulesets are empty. An administrator should enable branch protection requiring pull requests and the Tests (Python 3.11), Tests (Python 3.12), Tests (Python 3.13), Tests (Python 3.14), Docker health, CodeQL and dependency-audit checks. Block force-pushes and branch deletion. Enable private vulnerability reporting in repository security settings.

Several historical feature branches remain after their work was merged. They are not required for the current main branch; prune them through GitHub after confirming they are no longer needed for audit/history.
