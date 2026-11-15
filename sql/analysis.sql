-- RetailPulse analytical SQL (DuckDB).
-- Run from the project root after `python scripts/run_analysis.py`.
-- The CSVs are materialised by the Python pipeline to keep SQL and Python results consistent.

CREATE OR REPLACE VIEW sales_lines AS
SELECT * FROM read_csv_auto('data/processed/sales_lines.csv', header=true);

CREATE OR REPLACE VIEW customer_rfm AS
SELECT * FROM read_csv_auto('data/processed/customer_rfm.csv', header=true);

-- 1. Monthly revenue and order-value trend.
SELECT order_month,
       ROUND(SUM(line_value), 2) AS gross_revenue_gbp,
       COUNT(DISTINCT invoice) AS orders,
       ROUND(SUM(line_value) / NULLIF(COUNT(DISTINCT invoice), 0), 2) AS average_order_value_gbp
FROM sales_lines
GROUP BY order_month
ORDER BY order_month;

-- 2. Top ten products by gross revenue.
SELECT stock_code, description,
       ROUND(SUM(line_value), 2) AS gross_revenue_gbp,
       SUM(quantity) AS units_sold,
       COUNT(DISTINCT invoice) AS orders
FROM sales_lines
GROUP BY stock_code, description
ORDER BY gross_revenue_gbp DESC
LIMIT 10;

-- 3. Customer segment contribution.
SELECT rfm_segment,
       COUNT(*) AS customers,
       ROUND(SUM(monetary), 2) AS gross_revenue_gbp,
       ROUND(AVG(recency_days), 1) AS average_recency_days
FROM customer_rfm
GROUP BY rfm_segment
ORDER BY gross_revenue_gbp DESC;

-- 4. Country-level performance.
SELECT country,
       ROUND(SUM(line_value), 2) AS gross_revenue_gbp,
       COUNT(DISTINCT invoice) AS orders,
       COUNT(DISTINCT customer_id) AS identified_customers
FROM sales_lines
GROUP BY country
ORDER BY gross_revenue_gbp DESC;
