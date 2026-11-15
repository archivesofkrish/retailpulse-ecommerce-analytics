# Final Methodology, Validation and Limitations

## Data source and period

RetailPulse uses UCI Online Retail II, covering 1 December 2009 to 9 December 2011. The source contains 1,067,371 invoice-line rows. The data is historical and must not be represented as current retailer performance.

## Row classification and revenue

Core validation rejects five malformed rows. The remaining 1,067,366 rows reconcile to 1,041,670 sales lines, 22,951 return/cancellation lines and 2,745 other valid rows. Sales revenue is quantity multiplied by unit price on positive-quantity, positive-price lines not on cancellation invoices. Return/cancellation value is reported separately; it is not assumed to be a definitive accounting net-sales adjustment.

## Customer metrics

Customer metrics require an identified customer ID. Historical revenue means total observed sales during the dataset period. It is not projected customer lifetime value. RFM scores are relative quintiles in this dataset; rule-based segment labels are heuristic.

## Retention

Repeat-purchase windows use only first-time customers with full follow-up availability for the relevant horizon. The cohort heatmap shows the fraction of a first-purchase-month cohort active in a particular later calendar month. It is a point-in-time activity metric, not cumulative survival. For a cohort with `m` months of follow-up, columns beyond `m` are NA (right-censored); observed months with no active customers are zero.

## Products and countries

Operational/non-merchandise stock codes are excluded from merchandise ranking but remain in total gross sales revenue. A one-invoice bulk line (stock code 23843) is flagged for source-document review and remains in all revenue totals pending verification. Revenue is not gross margin or profit. Country concentration is descriptive and should not be used as market-entry guidance without costs and returns.

## Historical inactivity model

Target: no identified-customer invoice in the 90 days after a monthly snapshot. Features are built from data available on or before the snapshot. Training snapshots end 31 October 2010. The last training outcome window ends 29 January 2011. A 90-day temporal embargo is imposed, and the held-out period starts 31 January 2011. The test period ends 31 August 2011.

Test rows repeat customers and adjacent 90-day outcome windows can overlap; rows are not independent observations. The test inactivity prevalence differs materially from training. Predicted scores are not sufficiently calibrated for direct use as probabilities, expected churn losses, or campaign ROI. This model is retrospective ranking proof-of-concept only and cannot estimate 2026 customer risk.

## Validation completed in the build environment

- Full Phase 3 script completed successfully on the processed 1.067M-row dataset extract.
- 12 automated tests passed with `DeprecationWarning` treated as an error.
- The real-data reconciliation validator previously passed 8/8 checks against the original workbook.
- A regression test verifies that Phase 3 cohort outputs distinguish observed zero activity from unobserved future months.
- Dashboard source passes Python syntax compilation. User should run it locally against their full raw workbook to confirm their installation.

## Reproduce locally

```bash
source .venv/bin/activate
python scripts/run_analysis.py
python scripts/validate_real_data.py
python scripts/run_phase3_analysis.py
python -W error::DeprecationWarning -m pytest -q
streamlit run dashboard/app.py
```
