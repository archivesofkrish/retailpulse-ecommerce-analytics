# RetailPulse v1.0.0 — Release Validation Record

**Prepared:** 15 November 2026\
**Dataset:** UCI Online Retail II, 1,067,371 source rows; 1 Dec 2009–9 Dec 2011.

## Project-owner checks previously reported

| Check | Result | Evidence scope |
|---|---|---|
| Full UCI workbook validator | 8 passed, 0 failed, 0 skipped | Run locally against `data/raw/online_retail_II.xlsx` |
| Phase 3 warning-strict tests | 11 passed | `python -W error::DeprecationWarning -m pytest -q` after the Phase 3 warning-fix patch |
| Phase 3 runner with warnings strict | SUCCESS | Completed after the warning-fix patch |
| Professional Edition dashboard | Visually reviewed | Owner supplied browser screenshots of all six dashboard sections |

## Final release assembly checks

| Check | Result | Scope |
|---|---|---|
| Python syntax compilation | PASS | `dashboard`, `scripts`, `src`, `tests` |
| Automated pytest suite | PASS — 12 tests | `DeprecationWarning` treated as an error |
| Phase 3 runner | PASS — SUCCESS | Run against the uploaded processed full-data extract (1,041,670 sales lines) |
| Right-censored cohort regression | PASS | Observed zero activity distinguished from unobserved future months |
| 90-day temporal embargo regressions | PASS | Training label horizon precedes held-out snapshot start |
| Executive presentation | PASS — 11 slides | Rendered and passed slide overflow validation |
| Dashboard browser runtime | Owner-verified | Screenshots show all six tabs on the owner’s computer; final banner/table formatting changes were syntax-checked in release assembly |

## Reproduced headline results

- 5,878 identified customers; 72.39% made at least two purchases in the observation window.
- Customer revenue Gini: 0.742.
- Top 10% of identified customers: 63.9% of identified-customer revenue.
- United Kingdom: 85.21% of gross sales-line revenue; top five countries: 94.78%.
- Merchandise revenue: £20,112,163.17; top 10 stock codes: 8.02% of merchandise revenue.
- Historical inactivity holdout ROC-AUC: 0.791; training/test inactivity prevalence: 48.1% / 64.1%.

## Limitations

- The full workbook is not bundled; retrieve it with `python scripts/download_data.py`.
- The data period is historical and ends 9 December 2011.
- Revenue is not profit, and return/cancellation value is not a definitive accounting net-sales adjustment.
- RFM segments are heuristics; historical spend is not projected lifetime value.
- Cohort cells are point-in-time monthly activity, not cumulative survival.
- The inactivity model predicts a defined historical 90-day inactivity proxy; it is not a production churn model and its scores are not calibrated financial probabilities.
