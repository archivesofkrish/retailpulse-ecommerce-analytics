# Phase 3 methodology update

## Historical 90-day inactivity model

The target is whether an identified customer has no recorded order in the 90 days after a monthly snapshot. This is a 90-day inactivity proxy, not permanent churn.

Features are computed only from transactions at or before the snapshot. The chronological model split trains on snapshots through 2010-10-31. Because the label requires observing the subsequent 90 days, the latest training label window ends 2011-01-29. Test snapshots therefore begin on 2011-01-31, after the full training-label horizon is observable. This 90-day embargo avoids using training outcomes that would not yet have been known at the first held-out snapshot.

Test snapshots still repeat the same customers over time, and adjacent snapshots have overlapping 90-day outcomes. Metrics are descriptive historical backtest metrics, not independent-observation confidence estimates. The training/test inactivity prevalence shift is reported as a stability warning. Scores are not calibrated for expected revenue loss or campaign economics and are not suitable as current operational churn probabilities.

## Other Phase 3 definitions

- Customer revenue is historical identified-customer revenue, not projected lifetime value.
- Repeat purchase means a second distinct invoice associated with the same customer ID.
- Cohort retention is point-in-time monthly activity among identified customers; it is not cumulative survival. Observed months with no activity are zero; months beyond source follow-up are NA/right-censored.
- Merchandise concentration excludes codes labelled operational/non-merchandise. Product revenue is not profit because cost and margin are unavailable.
- Country concentration is based on recorded sales-line revenue and should be supplemented with shipping, cost and returns data before commercial allocation decisions.
