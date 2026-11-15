# Customer Value Studio

## Purpose

The Customer Value Studio connects cohort activity with the gross revenue observed from those cohorts. It answers a narrow historical question: how much recorded sales revenue did an acquisition cohort generate per originally identified customer as the cohort aged through the source observation window?

It does not estimate future spend, projected customer lifetime value (CLV), margin, customer profitability or campaign return.

## Cohort construction

Each identified customer is assigned to the calendar month of their first observed invoice. Invoice lines are first aggregated to distinct customer-invoice orders, then orders are placed into calendar-month age periods relative to the first-purchase cohort.

- Age month 0 is the first-purchase calendar month.
- Age month 1 is the next calendar month.
- Customers remain in their original cohort even when they do not order in a later month.
- Anonymous sales are excluded from customer-cohort analysis and remain part of sales-level reporting elsewhere in RetailPulse.

## Metrics

For a cohort with original size N, month age t, active customers A(t), and observed gross sales revenue R(t):

- Monthly active share = A(t) / N × 100.
- Monthly revenue yield = R(t) / N.
- Cumulative observed revenue yield = sum of R(j) from j = 0 through t, divided by N.
- Revenue per active customer = R(t) / A(t), when A(t) is positive.

Revenue yield always uses the original cohort size as its denominator. Revenue per active customer is supplementary and is not a substitute for that cohort denominator.

## Right-censoring and mature comparisons

The panel includes rows only for calendar months that have occurred by the last observed sale date. It does not create future months or extrapolate values. Calendar months with no activity are represented as zero, not missing. The final calendar month is flagged as partial when the source ends before the last day of that month.

The 12-calendar-month comparison uses age months 0 through 11 and includes only cohorts whose age-month 11 period is fully observed. The dashboard excludes the partial final month from this comparison. Cohorts without 12 complete periods remain visible in the full heatmap but do not enter the mature-cohort comparison.

The cumulative revenue-per-customer curve uses a fixed set of fully mature cohorts when available, so the cohort mix does not change from one month-age point to the next. When no mature cohorts exist (for example, a small synthetic sample), the dashboard shows the available observed curve and indicates that the cohort base varies by age.

## Interpretation guardrails

1. Revenue is gross recorded sales revenue, not profit or contribution.
2. Historical cohort yield is not projected lifetime value. No future months are modelled.
3. The source period is 1 December 2009 through 9 December 2011; findings are not current retailer performance.
4. Customers without usable IDs are not included in customer cohorts.
5. No COGS, margin, acquisition cost, paid-media spend, fulfilment cost or returns-adjusted accounting measure is available.
6. Cohort revenue is descriptive. A causal claim about a campaign or product change requires a controlled experiment.

## Reproduction

Run the core pipeline followed by Phase 3:

    python scripts/run_analysis.py
    python scripts/run_phase3_analysis.py
    python -m pytest -q
    streamlit run dashboard/app.py

The Phase 3 runner writes the customer cohort value CSV under reports/phase3. The generated file is included in the Phase 3 SHA-256 output manifest and is verified before advanced dashboard panels are enabled.
