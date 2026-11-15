# RetailPulse Portfolio Showcase Guide

## 30-second project summary

RetailPulse is an end-to-end business intelligence project using UCI Online Retail II (1.067M invoice-line rows, Dec 2009–Dec 2011). It combines a Python data pipeline, SQL analysis, customer RFM segmentation, cohort activity, product and country concentration, a time-ordered historical inactivity backtest, and a Streamlit/Plotly dashboard.

## What to demonstrate

1. **Data engineering:** show raw-to-processed pipeline, row classification and revenue reconciliation.
2. **Customer analytics:** explain RFM and the gap between mean (£3,018.62) and median (£898.92) historical customer revenue.
3. **Concentration:** show that the top 10% of identified customers generate 63.9% of identified revenue; explain the business risk and opportunity.
4. **Retention:** explain the 90-day second-purchase rate among eligible first-time customers (47.1%) and how cohort right-censoring is handled.
5. **Product intelligence:** compare customer concentration with less concentrated merchandise stock-code revenue; discuss the unusual single-invoice bulk line.
6. **Model governance:** explain the 90-day inactivity proxy, chronological split, 90-day embargo and temporal prevalence shift. Do not call it a production churn predictor.

## Honest limitations to state

- Historical data ends 9 December 2011; it is not current data.
- Revenue is not profit; margin, COGS, marketing cost and delivery expense are absent.
- 15.4% of sales revenue has no customer ID.
- RFM labels are heuristic; historical revenue is not projected CLV.
- Inactivity is not permanent churn; model probabilities are not calibrated for financial forecasting.
- The product bulk transaction should be verified from the original source document.

## Suggested portfolio description

**RetailPulse — E-commerce Business Intelligence:** Built a reproducible Python/SQL analytics pipeline and interactive Streamlit dashboard over 1.067M retail invoice lines. Delivered revenue reconciliation, customer RFM segmentation, Pareto concentration, repeat-purchase and right-censored cohort analysis, merchandise classification, geographic concentration and a time-ordered 90-day inactivity backtest with a 90-day embargo. Added automated validation, regression tests, executive reporting and explicit governance of data/model limitations.
