# RetailPulse — Project Status

**Current baseline:** RetailPulse v1.0.0 portfolio package, publicly committed to `main`.  
**Last baseline integration:** Decision Brief merged through [PR #6](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/6) on 15 November 2026.  
**Current proposed increment:** Software-supply-chain security improvements in [PR #7](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/7).  
**Status:** Seven-section Business Intelligence dashboard is on `main`; security automation remains under review until PR #7 is merged.

## Delivered on main

- End-to-end UCI Online Retail II ingestion and processing pipeline.
- Transaction classification, explicit data contracts, and revenue/customer reconciliation.
- RFM segmentation with tie-safe scoring.
- Merchandise versus operational/non-merchandise classification.
- Repeat-purchase, right-censored cohort, customer concentration, product and country analysis.
- Invoice-level product affinity and basket-association metrics.
- Source-file provenance, pipeline run manifests and stale-output detection.
- Chronological 90-day inactivity-model backtest with a 90-day embargo and explicit limitations.
- Seven-section Streamlit dashboard, including the transparent Business Decision Brief.
- Decision rules with evidence, thresholds, suggested investigations and interpretation guardrails.
- DuckDB SQL examples, guided Jupyter notebook, reproducible reports and 11-slide executive presentation.
- Non-root Docker image, read-only Compose mounts and container health check.
- Automated Python 3.10–3.12 test matrix, package build checks and Docker health smoke test.

## Proposed in PR #7

- Dependabot updates for Python packages, GitHub Actions and Docker base image.
- CodeQL Python static analysis using security-extended queries.
- Strict `pip-audit` dependency vulnerability scanning.
- Repository security disclosure policy and explicit warnings about the unauthenticated Streamlit application.
- Least-privilege workflow permissions and no new repository secrets.

## Validation evidence

- Baseline CI on main passed after the Decision Brief merge.
- The Decision Brief pull request's Python 3.10, 3.11 and 3.12 jobs and Docker dashboard health smoke test passed before merge.
- The release validation record documents earlier project-owner full-workbook checks and the warning-strict suite. The complete UCI workbook is not committed, so full-data validation must be rerun locally against the downloaded workbook.
- PR #7 is running the standard test matrix, Docker health check, CodeQL and dependency audit; current results are visible in GitHub Actions.

## Data and interpretation boundaries

- The source workbook is retrieved separately from UCI under CC BY 4.0 attribution; it is not stored in Git.
- The source period is 1 December 2009–9 December 2011. Findings are historical and are not current retailer performance.
- Processed transaction extracts, customer-level outputs and machine-specific validation JSON are generated locally and ignored by Git.
- Gross sales-line revenue is not profit; recorded return/cancellation value is not a definitive accounting net-sales adjustment.
- Historical customer spend is not projected customer lifetime value.
- RFM groups and Decision Brief thresholds are diagnostic heuristics, not ground-truth labels or significance tests.
- The inactivity model is a retrospective ranking proof of concept, not a calibrated or production churn model.
- The Docker image contains the synthetic demonstration sample, not the full UCI workbook.
- Streamlit does not provide application authentication in this project. Do not expose port 8501 directly to the public internet or process sensitive production customer data without additional security controls.
