# RetailPulse — Executive Business Intelligence Report

**Project:** RetailPulse Professional Edition\
**Dataset:** UCI Online Retail II\
**Observation window:** 1 December 2009 – 9 December 2011\
**Source rows:** 1,067,371\
**Currency:** GBP (£), as recorded in the source\
**Prepared:** 15 November 2026

> **Scope note:** This is a retrospective analysis of a historical UK non-store retailer. The figures describe the supplied 2009–2011 observation window; they are not current trading results. Revenue is not profit. Historical customer spend is not projected customer lifetime value. The inactivity model is a historical proof of concept, not an operational churn score.

## Executive summary

The retailer generated **£20,972,594.57** in gross sales-line revenue across **1,041,670 sale lines**. Of that revenue, **£17,743,429.18 (84.6%)** is linked to an identified customer ID and **£3,229,165.39 (15.4%)** is linked to sales rows without a customer ID. The processed source contains **5,878 identified customers**, **40,077 distinct sales invoices**, **4,903 merchandise stock codes**, and **43 countries**.

Customer revenue is highly concentrated: the top 10% of identified customers contribute **63.9%** of identified-customer revenue, while the top 20% contribute **77.3%**. **72.4%** of identified customers made at least two purchases during the observation window. Among customers with a full 90-day follow-up opportunity, **47.1%** made a second purchase within 90 days.

The United Kingdom represents **85.2%** of gross sales-line revenue; the top five countries represent **94.8%**. Merchandise contributes **£20.11M** after excluding classified operational/non-merchandise codes from merchandise ranking. A potentially anomalous one-invoice bulk product record is retained and flagged for review.

A time-ordered Random Forest backtest achieved a holdout ROC-AUC of **0.791** for a defined 90-day inactivity proxy after a 90-day temporal embargo. Its test-period inactivity prevalence was **64.1%**, versus **48.1%** in training. This shift and an underprediction of average test prevalence mean the score is suitable only as a historical ranking proof of concept, not as a calibrated probability or present-day churn forecast.

## 1. Business performance and data reconciliation

| Measure | Result |
|---|---:|
| Original source rows | 1,067,371 |
| Rows failing core validation | 5 |
| Rows after core validation | 1,067,366 |
| Sale lines | 1,041,670 |
| Return/cancellation lines | 22,951 |
| Other valid rows (not sale or return/cancellation) | 2,745 |
| Distinct sales invoices | 40,077 |
| Gross sales-line revenue | £20,972,594.57 |
| Recorded return/cancellation value | £1,527,415.00 |
| Identified-customer sales revenue | £17,743,429.18 |
| Unidentified-customer sales revenue | £3,229,165.39 |

The three mutually exclusive valid-row classes reconcile to the 1,067,366 rows remaining after core validation. Identified and unidentified sales revenue reconcile to gross sales-line revenue. Return/cancellation value is shown separately; the source extract does not provide a complete accounting reconciliation for treating it as a definitive net-sales or refund figure.

## 2. Customer value and concentration

There are **5,878 identified customers**. Mean historical revenue per customer is **£3,018.62**, while the median is **£898.91**. The large mean–median gap shows a strongly right-skewed customer-spend distribution. The customer revenue Gini coefficient is **0.742** (0 represents equality; values closer to 1 indicate greater concentration).

| Customer group by historical revenue rank | Customers | Share of identified revenue |
|---|---:|---:|
| Top 1% | 59 | 31.9% |
| Top 5% | 294 | 52.0% |
| Top 10% | 588 | 63.9% |
| Top 20% | 1,176 | 77.3% |
| Customers needed to reach 80% revenue | 1,353 | 23.0% of customer base |

### RFM segment priorities

| Segment | Customers | Customer share | Historical revenue | Revenue share | Avg. recency (days) | Avg. orders/customer |
|---|---:|---:|---:|---:|---:|---:|
| Champions | 1,271 | 21.6% | £12,062,615.49 | 68.0% | 20.2 | 17.36 |
| Loyal Customers | 606 | 10.3% | £1,810,967.10 | 10.2% | 86.7 | 8.35 |
| Cannot Lose Them | 203 | 3.5% | £970,135.35 | 5.5% | 339.3 | 9.51 |
| Potential Loyalists | 711 | 12.1% | £878,051.54 | 4.9% | 25.9 | 2.88 |
| Hibernating | 1,644 | 28.0% | £739,636.71 | 4.2% | 456.2 | 1.31 |
| Needs Attention | 701 | 11.9% | £607,180.18 | 3.4% | 109.7 | 2.24 |
| At Risk | 505 | 8.6% | £593,850.40 | 3.3% | 370.4 | 3.79 |
| New Customers | 237 | 4.0% | £80,992.41 | 0.5% | 30.5 | 1.00 |

Champions represent about one-fifth of customers but contribute about two-thirds of identified-customer revenue. Hibernating, At Risk and Cannot Lose Them together represent **2,352 customers (40.0%)** and **£2.30M** of historical spend. That amount is historic spend, not forecast revenue at risk. RFM segments are relative, rule-based categories—not ground-truth labels or churn probabilities.

## 3. Repeat purchasing and cohort activity

**4,255 customers (72.4%)** placed more than one distinct invoice within the overall observation window; **1,623 (27.6%)** placed one. The median interval from first to second purchase among repeat buyers is **56.0 days**.

| Follow-up window | Eligible first-time customers | Second purchase within window |
|---:|---:|---:|
| 30 days | 5,714 | 23.2% |
| 60 days | 5,509 | 38.2% |
| 90 days | 5,281 | 47.1% |
| 180 days | 4,976 | 62.4% |
| 365 days | 4,309 | 75.1% |

Eligibility restricts the denominator to customers with that full period of observable follow-up. These rates are not derived from a survival model.

Cohort heatmap cells represent the share of each acquisition-month cohort active in the exact calendar month offset from first purchase. They are **point-in-time activity rates, not cumulative survival probabilities**. A customer can skip a month and return later, so a later cell can exceed an earlier one. Observed months with no activity are zero; months beyond the source end are blank/NA (right-censored), not zero.

## 4. Merchandise and product concentration

After classification of operational/non-merchandise stock codes, merchandise revenue is **£20,112,163.17** across **4,903 stock codes**. Operational/non-merchandise revenue totals **£860,431.40**. The top ten merchandise stock codes account for **8.0%** of merchandise revenue, substantially less concentrated than customer revenue.

The top merchandise stock code by recorded revenue is **22423 — REGENCY CAKESTAND 3 TIER (£344,563.25)**. A significant source record needs manual review: stock code **23843 — PAPER CRAFT , LITTLE BIRDIE** records **80,995 units** on one distinct invoice (invoice 581483, 9 December 2011) for **£168,469.60**. It remains in revenue totals pending source-document review; it has not been silently removed as an error.

Product revenue is not product profitability. The source contains no cost of goods, gross margin, inventory carrying cost, or fulfilment expense.

## 5. Geographic concentration

The source contains **43 countries**. United Kingdom contributes **85.21%** of gross sales-line revenue; the top five countries contribute **94.78%**. This is a high level of geographic concentration. International growth decisions should consider margin, shipping, returns, local acquisition cost and repeat purchase—not recorded revenue alone.

## 6. Historical 90-day inactivity model

A Random Forest model predicts whether an identified customer has **no invoice during the 90 days after a monthly snapshot**. Training snapshots end **2010-10-31**; their label-observation window ends **2011-01-29**. A 90-day embargo is applied before held-out snapshots begin **2011-01-31**. Held-out snapshots end **2011-08-31**.

| Measure | Chronological holdout |
|---|---:|
| Training customer-snapshot observations | 24,188 |
| Test customer-snapshot observations | 38,821 |
| Training inactivity prevalence | 48.1% |
| Test inactivity prevalence | 64.1% |
| ROC-AUC | 0.791 |
| Average precision | 0.843 |
| Brier score | 0.191 |
| Accuracy at 0.50 threshold | 72.2% |
| Precision at 0.50 threshold | 81.7% |
| Recall at 0.50 threshold | 72.9% |
| Inactivity rate in top 20% risk-ranked observations | 89.9% |
| Lift of top 20% vs. test prevalence | 1.40× |

The prevalence shift from **48.1%** in training to **64.1%** in test is a material temporal stability warning. The mean predicted score is **0.499**, below the test prevalence; do not interpret the scores as calibrated event probabilities. The model is useful only as evidence that historical feature patterns can rank observations in this particular retrospective holdout.

Additional limitations: customer-month rows repeat the same people and are not independent; adjacent outcome windows may overlap within the held-out period; 90-day inactivity is not permanent churn; the dataset ends in 2011 and cannot score present-day customers; anonymous transactions are excluded from customer-level modeling; and probabilities are not calibrated to margin or expected revenue loss.

## 7. Recommended business actions

1. **Protect Champions without blanket discounting.** Test service, convenience and loyalty treatments; measure incremental contribution margin and repeat revenue against a holdout group.
2. **Test win-back for historically valuable inactive customers.** Start with Cannot Lose Them and At Risk, but randomise campaign eligibility to measure incremental reactivation rather than assuming all lapsed customers are recoverable.
3. **Improve second-purchase conversion.** Test onboarding, product discovery and relevant replenishment reminders during the first 30–90 days. Track conversion and margin, not just clicks.
4. **Improve customer identification.** Investigate the 236,121 sale lines without a customer ID (15.4% of sales revenue). Better identity resolution would strengthen retention and customer value analysis.
5. **Audit unusual bulk transactions.** Validate invoice 581483 / stock code 23843 before using the 80,995-unit line as a demand signal.
6. **Reduce geographic dependence carefully.** Evaluate candidate markets with net contribution, fulfilment costs, return rates, repeat behaviour and customer support load.
7. **Add cost and margin data before profitability or CLV claims.** A defensible economic CLV requires contribution margin, acquisition cost and a forward-looking retention/value model; these are not available here.

## 8. Method and reproducibility

1. Retrieve the UCI Online Retail II workbook and record the source URL, timestamp, file size and checksum.
2. Validate required fields; parse dates and numeric columns; classify each core-valid row as sale, return/cancellation or other.
3. Build customer RFM metrics from identified-customer sales and apply relative quintile scores with ties treated consistently.
4. Build cohort activity as a calendar-month matrix, retaining NA for unobserved future months.
5. Aggregate merchandise by stock code after removing classified operational codes from product ranking only.
6. Build historical monthly customer snapshots; define 90-day inactivity; train through 31 October 2010; purge the 90-day outcome window; evaluate on later snapshots.
7. Save processed CSVs, JSON metrics, charts and report outputs under `data/processed/` and `reports/phase3/`.

Reproduce from the project root:

```bash
source .venv/bin/activate
python scripts/run_analysis.py
python scripts/validate_real_data.py
python scripts/run_phase3_analysis.py
python -W error::DeprecationWarning -m pytest -q
streamlit run dashboard/app.py
```

## 9. Sources, licence and boundaries

Dataset: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. Dataset licence: CC BY 4.0; retain attribution to the creator and UCI when redistributing data or derived extracts. Project source code is licensed under MIT (see `LICENSE`).

This analysis is descriptive and retrospective. It does not establish causal effects, profitability, current customer status, or current market conditions.
