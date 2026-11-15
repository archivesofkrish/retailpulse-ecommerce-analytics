# RetailPulse v1.2.0 — Release Notes

**Release candidate date:** 15 November 2026

## Highlights

- Added portable, output-level SHA-256 manifests for every generated core CSV/KPI export and every Phase 3 table, summary, report and figure.
- Phase 3 verifies core exports before analysis and checks them again before publishing its completion manifest.
- The dashboard verifies source lineage and both output manifests before displaying advanced analytics; modified, missing or incomplete outputs are rejected with a rebuild instruction.
- Manifest verification rejects path traversal and symlinked artifact paths.
- Kept artifact manifests portable across local, copied and container-mounted paths by recording relative names, byte sizes and content digests rather than absolute paths or modification times.
- Preserved the seven-section Streamlit dashboard, evidence-backed Decision Brief, invoice-level product affinity and resilient handling of datasets without customer IDs or merchandise SKUs.
- Retained Python 3.11–3.14 CI, per-runtime JUnit artifacts, CodeQL, strict dependency auditing, Dependabot, non-root Docker and the dashboard health smoke test.
- Modernized package metadata to the PEP 639 SPDX license string and a current setuptools build requirement.

## Validation

Pull request #12 passed all eight required checks before merge:
- 41 tests passed on each of Python 3.11, 3.12, 3.13 and 3.14 (164 test executions).
- Docker image build and Streamlit health probe passed.
- CodeQL Python analysis passed.
- Dependency vulnerability audit passed.

See the release validation record for exact run links, validation scope and historical full-workbook evidence.

## Upgrade note

Existing generated data/processed and reports/phase3 outputs created before v1.2.0 do not contain output checksum manifests. Rebuild them once after upgrading:

    python scripts/run_analysis.py
    python scripts/run_phase3_analysis.py

The dashboard intentionally disables advanced panels until both new manifests and their corresponding outputs are present and verified.

## Runtime support

RetailPulse requires Python 3.11 or newer. CI validates Python 3.11, 3.12, 3.13 and 3.14. The Docker dashboard runtime uses Python 3.12.

## Important data and model limitations

The source dataset ends on 9 December 2011. Revenue is not profit; historical spend is not projected customer lifetime value; cohort activity is not cumulative survival; and 90-day inactivity is not permanent churn. Product affinity and business insight thresholds are descriptive diagnostics, not causal effects or automatic policies.

SHA-256 output manifests detect missing or modified artifacts, but are not signed attestations: an actor who can change both an output and its manifest can also recompute the checksum. The controls are intended to prevent accidental or uncoordinated output drift, not to replace signed provenance, access controls or secure storage.

The full UCI workbook is not included. Retrieve it separately with python scripts/download_data.py under the dataset's CC BY 4.0 attribution requirements.
