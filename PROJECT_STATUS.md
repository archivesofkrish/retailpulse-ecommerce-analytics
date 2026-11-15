# RetailPulse — Release Status

**Release candidate:** v1.0.0\
**Prepared:** 15 November 2026\
**Status:** Portfolio release package prepared; GitHub publication not yet performed.

## Delivered

- End-to-end UCI Online Retail II ingestion and processing pipeline.
- Transaction classification and revenue/customer reconciliation.
- RFM segmentation with tie-safe scoring.
- Merchandise vs operational/non-merchandise classification.
- Repeat-purchase, right-censored cohort, customer concentration, product and country analysis.
- Chronological 90-day inactivity-model backtest with a 90-day embargo and explicit limitations.
- Six-section Streamlit dashboard.
- DuckDB SQL examples and guided Jupyter notebook.
- Consolidated executive report, detailed Phase 3 report and 11-slide executive presentation.
- Automated tests, eight-check full-workbook validator and CI workflow.

## Validation evidence

- Project-owner terminal output: 11 tests passed with `DeprecationWarning` treated as an error after the Phase 3 warning fix.
- Project-owner full-workbook validation: 8 checks passed, 0 failed, 0 skipped.
- Project-owner browser review: all six Professional Edition dashboard sections were opened and visually reviewed.
- Release assembly environment: final code test suite and syntax checks are recorded in `test-results/RELEASE_VALIDATION.md`.
- Executive PowerPoint: 11 slides rendered and passed the slide overflow test.

## Release boundaries

- The source workbook is downloaded separately from UCI; it is not committed.
- Processed transaction extracts, customer-level CSVs, machine-specific outputs and validation JSON are generated locally and ignored by Git.
- Findings describe the UCI 2009–2011 historical dataset; not current retail performance.
- The inactivity model is a retrospective ranking proof of concept, not a calibrated or production churn model.
- No public GitHub repository has been created or pushed as part of this release preparation.
