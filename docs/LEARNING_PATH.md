# Learning path: understand RetailPulse from first principles

This sequence explains why each step exists, not just which command to run.

## Step 1 — Understand the business question

A retailer has lots of receipts but needs decisions. Think of a transaction file as a box of receipts: before asking what sold well, we must understand what one row means and which rows represent real completed sales.

Read: `README.md`, then inspect `data/sample/sample_retail_transactions.csv`.

## Step 2 — Understand the data structure

One row is a product line, not necessarily a whole order. An order with three products may occupy three rows. This is why summing `Quantity × Price` is appropriate for revenue, while counting rows is not a valid order count.

Run the notebook's raw inspection cells.

## Step 3 — Learn cleaning and classification

Cleaning is like sorting receipts before bookkeeping. Missing dates or prices cannot support a trustworthy line value. A cancellation is not a normal completed sale. A missing customer number still leaves a usable product sale, but cannot be used to identify that person later.

Study `prepare_transactions()` in `src/retailpulse/analysis.py`.

## Step 4 — Learn descriptive analytics

Monthly sales explain *when* revenue occurs. Product tables explain *what* sells. Country summaries explain *where* orders originate. AOV adds context to order volume.

Inspect `monthly_sales.csv`, `product_performance.csv`, and `country_performance.csv`.

## Step 5 — Learn customer analytics

RFM is a customer scorecard: Recency asks “how recently?”, Frequency asks “how often?”, and Monetary asks “how much?”. Cohort analysis then follows groups of customers from their first purchase month to see whether they return.

Inspect `customer_rfm.csv`, `rfm_segment_summary.csv`, and `cohort_retention.csv`.

## Step 6 — Learn how analytics becomes a product

The same analysis outputs are reused in a dashboard, SQL queries, and a report. This is a useful engineering pattern: calculate each metric once in a testable pipeline, then make it available to different audiences.

Run the dashboard and review `sql/analysis.sql`.

## Step 7 — Challenge the conclusions

Ask: Is revenue being mistaken for profit? Are missing customer IDs biasing the segment totals? Are new cohorts being judged unfairly because they have less follow-up time? Are segment names being treated as truth rather than heuristics?

These questions are part of good analytics, not optional footnotes.
