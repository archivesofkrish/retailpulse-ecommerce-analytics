# Product affinity and basket rules

RetailPulse derives co-purchase associations from historical merchandise invoices.

## Grain and inclusion

One basket is one distinct sales invoice. A stock code is counted at most once within an invoice, even if the invoice contains several lines for that code. The existing merchandise/operational classification is reused: operational codes such as postage and fees are excluded from baskets.

## Metrics

For items A and B:

- **Joint invoices**: number of distinct merchandise invoices containing both.
- **Support**: joint invoices / all merchandise invoices.
- **Confidence A → B**: joint invoices / invoices containing A.
- **Lift A → B**: confidence A → B / (invoices containing B / all merchandise invoices).

Both directional rules are retained because confidence is directional. Lift is symmetric for a pair under this definition.

## Noise control and ranking

A pair is included only if it appears in at least `max(5, ceil(0.01% × merchandise invoice count))` invoices. Rules are ranked by lift, then joint invoice count, then confidence. A high lift based on a small sample should be treated cautiously; the minimum frequency threshold is a basic stability guard, not a statistical significance test.

## Business use and limitations

Associations can inform merchandising hypotheses, product recommendations and bundle experiments. They do not prove causality or incremental revenue. They are sensitive to the source period, product assortment, stock availability, promotions and price. They also do not measure profitability because the source lacks product cost, margin and marketing spend. Use controlled experiments and margin data before making commercial decisions.
