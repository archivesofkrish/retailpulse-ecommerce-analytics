# RetailPulse — Project Status

**Baseline:** v1.0.0 portfolio release package, committed to the public `main` branch on 15 November 2026.  
**Repository:** [archivesofkrish/retailpulse-ecommerce-analytics](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics)  
**Current increment:** Evidence-backed Business Decision Brief proposed in [pull request #6](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/pull/6).  
**Status:** Core baseline is published. The Decision Brief remains a pull request and is not part of `main` until merged.

## Delivered on the current main baseline

- End-to-end UCI Online Retail II ingestion and processing pipeline.
- Transaction classification, data contracts, and revenue/customer reconciliation.
- RFM segmentation with tie-safe scoring.
- Merchandise versus operational/non-merchandise classification.
- Repeat-purchase, right-censored cohort, customer concentration, product and country analysis.
- Invoice-level product affinity and basket-association metrics.
- Source-file provenance, pipeline run manifests and stale-output detection.
- Chronological 90-day inactivity-model backtest with a 90-day embargo and explicit limitations.
- Six-section Streamlit dashboard on the current main baseline.
- DuckDB SQL examples, guided Jupyter notebook, reproducible reports and 11-slide executive presentation.
- Non-root Docker image, read-only Compose mounts and container health check.
- Automated Python 3.10–3.12 test matrix, package build checks and Docker health smoke test.

## Proposed in pull request #6

- Deterministic business insight rules for customer identity coverage, geographic and customer concentration, second-purchase conversion, merchandise affinity and assortment concentration.
- A seventh Streamlit dashboard section: Decision Brief.
- Structured evidence, trigger thresholds, suggested next actions and interpretation guardrails.
- Business insight CSV/JSON outputs, report integration and additional unit/integration coverage.

The PR's Python 3.10, 3.11 and 3.12 jobs and Docker build/health smoke test have passed for its current head commit. The change is not merged while the PR remains a draft.

## Validation evidence

- Project-owner full-workbook validation previously reported: 8 checks passed, 0 failed, 0 skipped.
- The baseline validation record reports a 12-test warning-strict suite and a successful Phase 3 run; see `test-results/RELEASE_VALIDATION.md`.
- Current GitHub Actions evidence for PR #6: all four checks passed (three Python versions and Docker health smoke test).
- The complete UCI workbook is not stored in Git, so full-dataset checks require downloading it locally.

## Release boundaries

- The source workbook is downloaded separately from UCI under CC BY 4.0 attribution; it is not committed.
- Processed transaction extracts, customer-level outputs and machine-specific validation JSON are generated locally and ignored by Git.
- Findings describe the UCI 2009–2011 historical dataset, not current retail performance.
- Revenue is not profit; recorded return/cancellation value is not a definitive accounting net-sales adjustment.
- Historical customer spend is not projected customer lifetime value.
- The inactivity model is a retrospective ranking proof of concept, not a calibrated or production churn model.
- The Docker image includes the synthetic demonstration sample, not the full UCI workbook.
- Streamlit does not provide application authentication in this project; do not expose port 8501 directly to the public internet.
