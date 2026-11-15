# RetailPulse Portfolio Showcase Guide

## 30-second project summary

RetailPulse is an end-to-end business intelligence project using UCI Online Retail II (1.067M invoice-line rows, Dec 2009–Dec 2011). It combines a Python data pipeline, SQL analysis, customer RFM segmentation, cohort activity, product and country concentration, a time-ordered historical inactivity backtest, basket associations, a transparent business decision brief, a configurable repeat-purchase Scenario Lab, source-to-output lineage checks, and a ten-section Streamlit/Plotly dashboard.

## What to demonstrate

1. **Data engineering:** show raw-to-processed pipeline, row classification and revenue reconciliation.
2. **Customer analytics:** explain RFM and the gap between mean (£3,018.62) and median (£898.92) historical customer revenue.
3. **Concentration:** show that the top 10% of identified customers generate 63.9% of identified revenue; explain the business risk and opportunity.
4. **Retention:** explain the 90-day second-purchase rate among eligible first-time customers (47.1%) and how cohort right-censoring is handled.
5. **Product intelligence:** compare customer concentration with less concentrated merchandise stock-code revenue; discuss the unusual single-invoice bulk line.
6. **Decision intelligence:** demonstrate how historical customer, country, repeat-purchase and product metrics trigger auditable recommendations, each with an evidence statement, threshold and guardrail.
7. **Commercial scenario planning:** use the Scenario Lab to change the assumed 90-day repeat-rate uplift and average order value; compare conservative, base and stretch outcomes, then explain why the resulting gross-revenue values are scenarios rather than forecasts.
8. **Experiment design:** use Experiment Studio to calculate a two-arm sample-size requirement, inspect how the minimum detectable effect changes the required sample, then enter completed experiment counts to review the p-value, confidence interval and sample-ratio diagnostic. Change the expected allocation to demonstrate that a planned 90/10 split is different from an unexpected 60/40 split. Explain the randomisation, independent-observation, low-count and no-peeking assumptions.
9. **Model governance:** explain the 90-day inactivity proxy, chronological split, 90-day embargo and temporal prevalence shift. Do not call it a production churn predictor.

## Honest limitations to state

- Historical data ends 9 December 2011; it is not current data.
- Revenue is not profit; margin, COGS, marketing cost and delivery expense are absent.
- 15.4% of sales revenue has no customer ID.
- RFM labels are heuristic; historical revenue is not projected CLV.
- Inactivity is not permanent churn; model probabilities are not calibrated for financial forecasting.
- The decision brief uses transparent heuristics; it is not an autonomous decision maker or a causal model.
- The product bulk transaction should be verified from the original source document.
- Experiment Studio is a normal-approximation planning/evaluation calculator, not a randomisation service or live experiment monitor. Statistical significance does not certify implementation quality or causal validity.
- The sample-ratio diagnostic uses a chi-square approximation and is a warning signal for allocation imbalance, not proof of an assignment or instrumentation defect.

## Suggested portfolio description

**RetailPulse — E-commerce Business Intelligence:** Built a reproducible Python/SQL analytics pipeline and ten-section interactive Streamlit dashboard over 1.067M retail invoice lines. Delivered revenue reconciliation, customer RFM segmentation, Pareto concentration, repeat-purchase and right-censored cohort analysis, merchandise classification, geographic concentration, an assumption-driven repeat-purchase Scenario Lab, a two-proportion A/B-test Experiment Studio, and a time-ordered 90-day inactivity backtest with a 90-day embargo. Added automated validation, output-integrity controls, regression tests, executive reporting and explicit governance of data/model limitations.
