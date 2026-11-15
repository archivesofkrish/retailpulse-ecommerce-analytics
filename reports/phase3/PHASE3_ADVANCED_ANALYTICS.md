# RetailPulse — Phase 3 Advanced Analytics Report

**Dataset:** UCI Online Retail II (processed sale-line extract)
**Observation window:** 2009-12-01 to 2011-12-09
**Source sale lines:** 1,041,670
**Currency:** GBP (£), as recorded in the source

> This report analyses historical transactions. Revenue is not profit. Historical customer spend is not a forward-looking customer lifetime value (CLV) estimate. The churn-risk model predicts a defined 90-day inactivity proxy, not permanent churn.

## Executive summary

- Gross sales-line revenue is **£20,972,594.57**. The identified-customer RFM file reconciles to **£17,743,429.18**; approximately **84.6%** of sales revenue is attributable to identified customer IDs.
- The top **10%** of identified customers generate **63.9%** of identified-customer revenue; the top **20%** generate **77.3%**.
- **72.4%** of identified customers made at least two purchases within the dataset window. Among customers with a full 90-day follow-up window, **47.1%** made a second purchase within 90 days.
- The **United Kingdom** accounts for **85.2%** of gross sales-line revenue; the top five countries account for **94.8%**.
- Merchandise revenue totals **£20,112,163.17** after excluding operational/non-merchandise codes; operational/non-merchandise revenue is **£860,431.40**. A single-invoice product anomaly is flagged for audit rather than removed.
- The processed file contains **236,121 sales lines with no customer ID**, representing **15.4%** of sales revenue.
- A historical random-forest model achieved a holdout ROC-AUC of **0.791** for 90-day inactivity. Treat this as a retrospective ranking proof-of-concept, not a deployable churn probability.

## 0. Data scope and reconciliation

The source workbook has **1,067,371** rows. Five rows fail core validation, leaving **1,067,366**. The processed extract classifies **1,041,670** sale lines, **22,951** return/cancellation lines and **2,745** other valid rows. These categories reconcile to the validated-row total.
There are **236,121** sales lines without customer IDs, representing **15.4%** of gross sales-line revenue. Identified and unidentified sales revenue reconcile to gross sales-line revenue.

## 1. Customer value and concentration

Identified customers: **5,878**. Mean historical spend per identified customer is **£3,018.62**, while the median is **£898.91**. The gap shows a strongly right-skewed spend distribution; the median is more representative of a typical customer.
The customer revenue Gini coefficient is **0.742** (0 = equal distribution; 1 = maximum concentration). The top 1% contribute **31.9%** of identified revenue, and the top 5% contribute **52.0%**.

### RFM segment priorities

| Segment | Customers | Customer share | Historical revenue | Revenue share | Average recency (days) | Average orders |
|---|---:|---:|---:|---:|---:|---:|
| Champions | 1,271 | 21.6% | £12,062,615.48 | 68.0% | 20.2 | 17.36 |
| Loyal Customers | 606 | 10.3% | £1,810,967.09 | 10.2% | 86.7 | 8.35 |
| Cannot Lose Them | 203 | 3.5% | £970,135.35 | 5.5% | 339.3 | 9.51 |
| Potential Loyalists | 711 | 12.1% | £878,051.54 | 4.9% | 25.9 | 2.88 |
| Hibernating | 1,644 | 28.0% | £739,636.71 | 4.2% | 456.2 | 1.31 |
| Needs Attention | 701 | 11.9% | £607,180.18 | 3.4% | 109.7 | 2.24 |
| At Risk | 505 | 8.6% | £593,850.40 | 3.3% | 370.4 | 3.79 |
| New Customers | 237 | 4.0% | £80,992.41 | 0.5% | 30.5 | 1.00 |

The combined Hibernating, At Risk and Cannot Lose Them groups contain **2,352 customers** and represent **40.0%** of the identified base. Their historical spend is **£2,303,622.46** (13.0% of identified-customer revenue). This is historical spend, not expected future revenue at risk.

## 2. Repeat purchasing and retention

The mean number of orders per identified customer is **6.29**, with a median of **3**. **4,255** customers purchased more than once, while **1,623** purchased once in the observed window.
Among customers with at least 90 days of follow-up after their first observed purchase, **47.1%** placed a second order within 90 days. The median interval from first to second order among repeat buyers is **56.0 days**.

| Follow-up window | Eligible first-time customers | Second purchase within window |
|---:|---:|---:|
| 30 days | 5,714 | 23.2% |
| 60 days | 5,509 | 38.2% |
| 90 days | 5,281 | 47.1% |
| 180 days | 4,976 | 62.4% |
| 365 days | 4,309 | 75.1% |

Cohort heatmap values represent the share of each acquisition cohort that was active in a specific calendar month relative to first purchase. They are point-in-time monthly activity rates, not cumulative survival probabilities. A later month can rise above an earlier month because customers can skip a month and return later. Blank cells are unobserved follow-up, not zero retention.

| Months after first purchase | Eligible customers | Active in that exact calendar month |
|---:|---:|---:|
| 1 | 5,850 | 23.1% |
| 2 | 5,659 | 23.3% |
| 3 | 5,438 | 24.5% |
| 6 | 5,041 | 21.8% |
| 9 | 4,716 | 19.0% |
| 12 | 4,342 | 22.3% |
| 18 | 2,973 | 19.5% |
| 24 | 955 | 19.7% |

## 3. Merchandise and product concentration

The merchandise table contains **4,903 stock codes** with total recorded revenue of **£20,112,163.17**. The top 10 stock codes contribute **8.0%** of merchandise revenue. This is a materially less concentrated pattern than customer revenue.

| Merchandise Pareto threshold | Stock codes required | Share of merchandise codes |
|---:|---:|---:|
| 50% of merchandise revenue | 284 | 5.8% |
| 80% of merchandise revenue | 1,036 | 21.1% |
| 90% of merchandise revenue | 1,698 | 34.6% |

### Product record requiring manual review

Stock code **23843** (PAPER CRAFT , LITTLE BIRDIE) records **80,995 units**, **1 distinct invoice(s)** and **£168,469.60** revenue. The source transaction export shows a single invoice for 80,995 units (invoice 581483, dated 9 December 2011). It has been retained in revenue totals and flagged for source-document review; it has not been deleted as an error.

Operational/non-merchandise codes are excluded from merchandise rankings, but their sales-line revenue remains part of gross sales. No product cost or gross margin data is present, so high revenue must not be interpreted as high profitability.

### Top merchandise stock codes

| Stock code | Product description | Revenue | Distinct invoices | Units |
|---|---|---:|---:|---:|
| 22423 | REGENCY CAKESTAND 3 TIER | £344,563.25 | 3,918 | 27,577 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | £263,109.67 | 5,365 | 96,147 |
| 85099B | JUMBO BAG RED RETROSPOT | £183,454.83 | 3,989 | 98,349 |
| 23843 | PAPER CRAFT , LITTLE BIRDIE | £168,469.60 | 1 | 80,995 |
| 47566 | PARTY BUNTING | £149,187.05 | 2,674 | 28,378 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | £132,187.92 | 2,807 | 81,809 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | £123,141.54 | 2,018 | 36,581 |
| 79321 | CHILLI LIGHTS | £85,489.91 | 1,135 | 16,840 |
| 23166 | MEDIUM CERAMIC TOP STORAGE JAR | £81,700.92 | 247 | 78,033 |
| 22197 | SMALL POPCORN HOLDER | £80,920.64 | 2,322 | 89,898 |

## 4. Country concentration

The source includes **43 countries**. United Kingdom contributes **85.2%** of total sales-line revenue, and the top five countries contribute **94.8%**. This indicates substantial geographic concentration.

| Country | Revenue | Revenue share | Orders | Identified customers |
|---|---:|---:|---:|---:|
| United Kingdom | £17,870,977.78 | 85.21% | 36,535 | 5,350 |
| EIRE | £664,431.78 | 3.17% | 626 | 5 |
| Netherlands | £554,232.34 | 2.64% | 228 | 22 |
| Germany | £431,262.46 | 2.06% | 789 | 107 |
| France | £356,944.60 | 1.70% | 622 | 95 |
| Australia | £169,968.11 | 0.81% | 95 | 15 |
| Spain | £109,178.53 | 0.52% | 154 | 41 |
| Switzerland | £101,011.29 | 0.48% | 93 | 22 |
| Sweden | £91,903.72 | 0.44% | 105 | 19 |
| Denmark | £69,862.19 | 0.33% | 43 | 12 |

## 5. Historical 90-day inactivity model

A Random Forest model was trained on monthly customer snapshots up to **2010-10-31**. The latest training label window ends **2011-01-29**. A 90-day temporal embargo is applied; held-out snapshots begin **2011-01-31** and run through **2011-08-31**. There were **24,188** training and **38,821** test customer-snapshot observations. The 90-day inactivity rate was **48.1%** in training and **64.1%** in test, showing temporal distribution shift.

| Metric | Historical holdout result |
|---|---:|
| ROC-AUC | 0.791 |
| Average precision | 0.843 |
| Brier score | 0.191 |
| Accuracy at 0.50 threshold | 72.2% |
| Precision at 0.50 threshold | 81.7% |
| Recall at 0.50 threshold | 72.9% |
| Inactivity rate in top 20% risk-ranked snapshots | 89.9% |
| Lift in top 20% vs. test prevalence | 1.40x |

The strongest feature importances are lifetime order count, 180-day revenue/orders and 365-day order/revenue history. The model is useful as a retrospective proof of concept for prioritising historical snapshots, but it is not ready for operational deployment.

### Model limitations

- The target is no recorded order within 90 days, not permanent customer loss. For an intermittent retailer, 90 days of inactivity may be normal.
- A 90-day embargo ensures the final training snapshot's inactivity label is observable before the first held-out snapshot; test snapshots still overlap one another in their 90-day outcome windows.
- Customer-month snapshots repeatedly include the same people; rows are correlated, so row counts should not be interpreted as independent customers.
- The training and test inactivity rates differ materially, indicating temporal/seasonal distribution shift.
- Predicted scores are not calibrated for expected revenue loss or campaign economics.
- This historical dataset ends on 9 December 2011; it cannot estimate current customer risk in 2026.

## 6. Recommended business actions

1. **Protect the Champions segment.** Use service and loyalty experiments, measure incremental repeat revenue and margin, and avoid assuming all Champions need discounts.
2. **Create a win-back test for Cannot Lose Them and At Risk.** Prioritise historically valuable customers with long recency, but use a randomised control group to measure incremental reactivation.
3. **Improve second-purchase conversion.** Test onboarding, replenishment reminders and product recommendations during the first 30–90 days.
4. **Investigate anonymous sales.** Customer IDs are missing from 236,121 sales lines in the processed dataset. Better customer identification would improve retention and lifetime-value analysis.
5. **Audit the one-invoice bulk product record.** Validate the Paper Craft, Little Birdie transaction before using its one-off volume as a demand forecast.
6. **Reduce geographic dependence carefully.** Evaluate international markets using margin, shipping, returns, customer repeat rates and acquisition costs—not revenue alone.
7. **Add cost and margin data.** Product profitability and economic CLV cannot be calculated from sales prices alone.

## 7. Definitions and caveats

- **Gross sales-line revenue:** Sum of included positive-quantity, positive-price sales-line values. It is not profit and is not net of recorded returns/cancellations.
- **Historical customer revenue:** Recorded sales revenue associated with a known customer ID over the source period. It is not a forecast of future lifetime value.
- **Repeat purchase:** A second distinct invoice associated with the same customer ID.
- **90-day inactivity:** No identified-customer invoice during the 90 days following a historical monthly snapshot.
- **RFM segments:** Rule-based recency/frequency/monetary groups; the segment label is not itself a churn probability.
- **Merchandise stock-code concentration:** Product revenue aggregated to one row per stock code after excluding operational/non-merchandise types.

## 8. Reproducibility

Run from the RetailPulse project root:
```bash
source .venv/bin/activate
python scripts/run_phase3_analysis.py
```
Outputs are written to `reports/phase3/`. The script uses the processed exports already generated by the main RetailPulse pipeline.
