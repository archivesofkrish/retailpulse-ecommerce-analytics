# Analytical methods and metric definitions

## 1. Grain of the data

The input is at **invoice-line level**: one row represents one product line on an invoice. Several rows may belong to the same invoice. Therefore revenue is summed across lines, while orders are counted using distinct invoice IDs.

## 2. Transaction classification

- **Sale line:** invoice does not start with `C`, quantity is positive, and unit price is positive.
- **Return/cancellation line:** invoice starts with `C` or quantity is negative.
- **Invalid core row:** missing invoice, stock code, timestamp, quantity, or price, or negative unit price.
- **Other valid non-sale/non-return line:** a row that passes core validation but does not meet either positive-sale or return/cancellation rules (for example, a zero-quantity or zero-price line). These rows are retained and exported separately so the row-count reconciliation is complete.
- A missing customer ID does not invalidate a sale for sales reporting, but that line is excluded from customer-level metrics.

## 3. Revenue and order metrics

For invoice line \(i\):

\[
\text{Line Value}_i = \text{Quantity}_i \times \text{Unit Price}_i
\]

Gross sales revenue is the sum of line value across included sale lines. Average order value (AOV) is:

\[
\text{AOV} = \frac{\text{Gross Sales Revenue}}{\text{Distinct Sales Invoices}}
\]

Revenue is not profit. The source does not contain product cost, marketing cost, shipping cost, or operating expenses.

## 4. RFM segmentation

- **Recency:** number of days since the customer's last purchase, relative to one day after the latest observed sales timestamp.
- **Frequency:** count of distinct invoices for the customer.
- **Monetary:** total gross sales value associated with that customer.

Each variable is converted to a relative 1–5 score. More recent customers receive higher R scores; customers with more invoices or higher spend receive higher F and M scores. Average percentile ranking gives customers with tied metric values the same score rather than assigning different scores based on input row order.

The segment names are rule-based heuristics. They describe relative customer behaviour in this dataset; they are not a prediction of future customer activity.

## 5. Cohort retention

The cohort month is the month of a customer's first observed purchase. For each cohort and elapsed month, retention is:

\[
\text{Retention}_{c,t} = \frac{\text{Distinct customers from cohort }c\text{ purchasing in month }t}{\text{Customers in cohort }c\text{ at month }0}
\]

Month 0 is 100% by construction. Recent cohorts have fewer observable future months, a form of right-censoring.

## 6. Interpretation guardrails

- Do not net return and cancellation values into a claimed accounting net-sales figure without validating the retailer's accounting rules.
- Do not compare country totals without considering customer count and order count.
- Do not call a high-revenue product profitable without cost data.
- Do not infer that an intervention caused a change from descriptive time-series or cohort patterns.


## Phase 2 refinements

### Merchandise versus operational codes

The product analysis tags 13 source stock codes as operational/non-merchandise: `M`, `m`, `DOT`, `POST`, `AMAZONFEE`, `C2`, `B`, `ADJUST`, `ADJUST2`, `BANK CHARGES`, `D`, `S`, and `PADS`. These lines remain in gross sales so the KPI reconciles to the source transaction definition, but they are excluded from merchandise rankings. The classification is an analytical convention and should be reviewed if the retailer's chart of accounts or product master becomes available.

### Cohort censoring

A cohort's Month 0 is the first observed purchase month and has 100% retention. For each cohort, only months up to the final month present in the source data are observable. Within that window, a zero indicates no cohort member purchased in that month. Months after the final observed month are `NaN`/blank, not zero. This avoids making recent cohorts appear to have zero retention in months that have not yet occurred.

## 7. Input validation and identifier handling

The ingestion layer rejects blank invoice and stock-code identifiers, unparseable dates, missing numeric transaction values, non-finite quantities or prices, negative unit prices, and line values that overflow to a non-finite result. This prevents malformed numeric data from contaminating revenue aggregates.

Header names are normalised against explicit aliases. If two input columns map to the same canonical field, ingestion fails with an actionable error rather than silently selecting one. Customer identifiers are optional for sales reporting. Numeric integral identifiers are normalised consistently across common Excel/CSV representations, digit-only string identifiers retain leading zeroes, non-integral numeric identifiers are treated as unavailable, and non-numeric identifiers are preserved as strings.

## 8. Product affinity and market-basket analysis

Product affinity is calculated at **invoice level**, not line level. Within each invoice, duplicate lines for the same stock code are collapsed to one basket item. Only records classified as merchandise are included; postage, fees, adjustments and other operational codes are excluded.

For merchandise items (A) and (B):

- **Support** = invoices containing both (A) and (B) divided by all invoices containing at least one merchandise item.
- **Confidence** (A → B) = invoices containing both (A) and (B) divided by invoices containing (A).
- **Lift** (A → B) = confidence (A → B) divided by the baseline support of (B).

A lift above 1 indicates the two items co-occur more frequently than expected under independence in this dataset. The association is descriptive, not causal. It does not demonstrate that displaying, bundling or discounting one product will increase the sales or profit of another.

To reduce unstable one-off patterns, a pair must occur in at least `max(5, ceil(0.01% × merchandise invoice count))` distinct invoices. Both rule directions are reported because (A → B) and (B → A) have different confidence values. Revenue, gross margin, stock availability, promotion exposure and randomised experiment results are not part of the association calculation.
