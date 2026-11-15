# RetailPulse v1.1.0 — Release Notes

**Release candidate date:** 15 November 2026

## Highlights

- Hardened transaction ingestion, schema validation, customer-ID handling and finite numeric checks.
- Added source SHA-256 fingerprints, pipeline run IDs and freshness validation across core analytics, Phase 3, SQL and Streamlit.
- Added synthetic end-to-end integration coverage and explicit handling of model-skipped demo datasets.
- Added invoice-level merchandise co-purchase analysis with support, confidence and lift.
- Added the Decision Brief dashboard section with six transparent business-insight rules, evidence, thresholds, recommended actions and guardrails.
- Added a non-root Docker dashboard image, read-only data mounts and automated container health smoke test.
- Expanded CI to a supported Python runtime matrix, with package builds and downloadable JUnit reports.
- Added CodeQL, Dependabot, security guidance and updated project status documentation.

## Runtime support

RetailPulse requires Python 3.11 or newer. Python 3.10 is no longer supported by the upstream Python project as of 1 October 2026. The CI matrix validates Python 3.11, 3.12 and 3.13. The Docker dashboard runtime uses Python 3.12.

## Important data and model limitations

The source dataset ends on 9 December 2011. Revenue is not profit; historical spend is not projected customer lifetime value; cohort activity is not cumulative survival; and 90-day inactivity is not permanent churn. Product affinity and business insight thresholds are descriptive diagnostics, not causal effects or automatic policies.

The full UCI workbook is not included. Retrieve it separately with python scripts/download_data.py under the dataset's CC BY 4.0 attribution requirements.

## Validation record

See test-results/RELEASE_VALIDATION.md for CI run links, test counts, container-health evidence and the scope of full-workbook validation.
