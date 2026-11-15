# RetailPulse v1.2.0 — Validation Record

**Updated:** 15 November 2026  
**Dataset:** UCI Online Retail II, 1,067,371 source rows; 1 December 2009–9 December 2011.

## Automated GitHub Actions validation

The latest artifact-integrity increment (PR #12) was merged only after all eight check runs passed for commit 67337cd6cd30bb3c55724b1d50fef58ec7e12eda.

| Validation | Result | Evidence |
|---|---:|---|
| Python 3.11 | 41 passed | [CI workflow](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434274) |
| Python 3.12 | 41 passed | [CI workflow](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434274) |
| Python 3.13 | 41 passed | [CI workflow](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434274) |
| Python 3.14 | 41 passed; package build and dependency consistency passed | [CI workflow](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434274) |
| Docker build and dashboard health | PASS | [Container job](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434274) |
| CodeQL Python | PASS | [CodeQL workflow](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434309) |
| Dependency vulnerability audit | PASS | [Dependency audit](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43714434303) |

**PR #12 total:** 164 passing test executions across four supported Python versions, plus Docker, CodeQL and dependency-audit checks.

The v1.2.0 suite covers:
- SHA-256 and byte-size manifests for generated core and Phase 3 artifacts.
- Verification after copying outputs to a different host/container path.
- Detection of same-size edits even when the original modification timestamp is restored.
- Rejection of path traversal entries and symlinked artifacts.
- Rejection of edited core exports before Phase 3 ingestion.
- Detection of modified Phase 3 reports after generation.
- Existing data contracts, RFM, product affinity, customer-ID integrity, empty-dimension behaviour, cohort censoring and model temporal-embargo regressions.

## v1.2.0 release-candidate validation (PR #13)

The release metadata, public verification CLI and end-to-end CI smoke test passed on head commit `0fde9b783203706e9037582c14ab5b1bb8cf105e`.

| Validation | Result | Evidence |
|---|---:|---|
| Python 3.11 | 45 passed | [RetailPulse CI run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768) |
| Python 3.12 | 45 passed | [RetailPulse CI run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768) |
| Python 3.13 | 45 passed | [RetailPulse CI run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768) |
| Python 3.14 | 45 passed; sdist/wheel build and dependency consistency passed | [RetailPulse CI run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768) |
| Public output-verification CLI | PASS — 6 checks, 0 failed | [Python 3.14 job log](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768/job/132814910575) |
| Core artifact manifest | 13 artifacts verified | Same CLI smoke test |
| Phase 3 artifact manifest | 27 artifacts verified | Same CLI smoke test |
| Docker build and Streamlit health | PASS | [RetailPulse CI run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134768) |
| CodeQL Python | PASS | [CodeQL run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134729) |
| Dependency vulnerability audit | PASS | [Dependency audit run](https://github.com/archivesofkrish/retailpulse-ecommerce-analytics/actions/runs/43715134767) |

**PR #13 total:** 180 passing test executions across four Python versions. The Python 3.14 workflow builds the synthetic core and Phase 3 outputs, then runs `python scripts/verify_outputs.py`; the command returns `PASS` after verifying the two manifests, all 40 artifacts, shared run ID and matching source fingerprint.

The CI workflow also now uses Node 24-compatible releases of checkout and upload-artifact, removing the prior Node 20 deprecation warnings from those steps.

## Previous automated feature increments

| Change set | Automated test result | Additional evidence |
|---|---:|---|
| PR #1 — ingestion and CI hardening | 17 passed per Python runtime | Package build and dependency check |
| PR #2 — data lineage and freshness | 22 passed per Python runtime | Package build and dependency check |
| PR #3 — end-to-end smoke test | 24 passed per Python runtime | Synthetic core-to-Phase-3 pipeline |
| PR #4 — product affinity | 26 passed per Python runtime | Support/confidence/lift regression tests |
| PR #5 — Docker deployment | 28 passed per Python runtime | Docker image, container startup and Streamlit health probe |
| PR #6 — business decision brief | 32 passed per Python runtime | Six rules, missing-data gates, full integration and Docker health probe |
| PR #8 — runtime and security baseline | All required checks passed | Python 3.11–3.14, Docker health, CodeQL and dependency audit |
| PR #9 — customer identity and invoice-level SKU correctness | 34 passed per Python runtime | Python 3.11–3.14, Docker health, CodeQL and dependency audit |
| PR #10 — empty-dimension resilience | 36 passed per Python runtime | Anonymous-only and operational-only end-to-end cases |
| PR #12 — output-level artifact integrity | 41 passed per Python runtime | Four runtime jobs, Docker health, CodeQL and dependency audit |

PR #1–#6 were validated on the then-current Python 3.10, 3.11 and 3.12 matrix. Python 3.10 reached upstream end-of-life on 1 October 2026. PR #8 replaced it in CI with Python 3.11, 3.12, 3.13 and 3.14.

## Previously reported full-workbook checks

These results were supplied from the project owner's local environment during the v1.0.0 release preparation. They are preserved as historical evidence and have **not** been rerun in the GitHub Actions environment.

| Check | Previously reported result | Evidence scope |
|---|---|---|
| Full UCI workbook validator | 8 passed, 0 failed, 0 skipped | Local data/raw/online_retail_II.xlsx |
| Project-owner warning-strict test run | 11 passed | v1.0.0 local environment |
| Project-owner Phase 3 runner | SUCCESS | Previously generated full-data extracts |
| Project-owner dashboard review | All six original sections visually reviewed | Owner-supplied browser screenshots |
| Executive presentation | 11 slides rendered; overflow test passed | v1.0.0 portfolio artefact |

## Current validation scope and upgrade note

The GitHub Actions pipeline compiles application and test modules, runs the synthetic/regression suite with deprecation warnings treated as errors, builds source and wheel distributions on Python 3.14, checks dependency consistency, uploads JUnit reports, runs CodeQL and pip-audit, builds the Docker image and checks the Streamlit health endpoint.

The synthetic integration path validates core ingestion through Phase 3. It does not replace a fresh full-workbook validation against the original UCI file.

Existing generated outputs created before v1.2.0 do not contain artifact checksum manifests. Rebuild them once after upgrading:

    python scripts/run_analysis.py
    python scripts/run_phase3_analysis.py

SHA-256 output manifests detect missing or modified artifacts, but they are not signed attestations. An actor who can change both an output and its manifest can recompute the checksum; keep data directories and manifests access-controlled.

## Reproduced historical findings

The following figures are inherited from the previously validated full UCI workbook:

- 5,878 identified customers; 72.39% made at least two purchases in the observation window.
- Customer revenue Gini: 0.742.
- Top 10% of identified customers: 63.9% of identified-customer revenue.
- United Kingdom: 85.21% of gross sales-line revenue; top five countries: 94.78%.
- Merchandise revenue: £20,112,163.17; top 10 stock codes: 8.02% of merchandise revenue.
- Historical inactivity holdout ROC-AUC: 0.791; training/test inactivity prevalence: 48.1% / 64.1%.

## Limitations

- The full workbook is not bundled; retrieve it with python scripts/download_data.py.
- The data period is historical and ends 9 December 2011.
- Revenue is not profit, and return/cancellation value is not a definitive accounting net-sales adjustment.
- RFM segments are heuristics; historical spend is not projected lifetime value.
- Cohort cells are point-in-time monthly activity, not cumulative survival.
- The inactivity model predicts a defined historical 90-day inactivity proxy; it is not a production churn model and its scores are not calibrated financial probabilities.
- Business decision rules are diagnostic thresholds, not statistical significance tests, causal effects or automated policies.
