# RetailPulse business insight rules

## Purpose

The Decision Brief converts validated historical metrics into structured investigation prompts. It is deliberately deterministic and auditable. It does not use a generative model, make decisions on behalf of a retailer, estimate causal lift, or forecast financial returns.

Each triggered finding includes:
- Priority and analytical area.
- A plain-language statement of the pattern.
- The observed metric and evidence base.
- The trigger threshold that was crossed.
- A recommended next action.
- A guardrail describing what the evidence does not establish.

## Rules and thresholds

| Rule | Trigger | Higher priority | Suggested investigation |
|---|---|---|---|
| Customer identity gap | Unidentified-customer revenue share ≥10% | High at ≥20% | Audit customer-ID capture and matching |
| Geographic concentration | Leading country revenue share ≥75% | High at ≥85% | Review country exposure alongside margin, shipping, returns and repeat behaviour |
| Customer revenue concentration | Top 20% of identified customers contribute ≥50% of identified revenue | High at ≥60% | Review customer retention and service; test interventions with a holdout |
| Second-purchase conversion | 90-day repeat rate ≤40%, with at least 20 eligible customers | High at ≤25% | Map the post-first-purchase journey and experiment with onboarding or replenishment |
| Product cross-sell candidate | Lift ≥1.5 and at least 20 joint invoices | Medium | Test product recommendations or bundles against a control |
| Merchandise assortment concentration | Top 10 stock codes contribute ≥60% of merchandise revenue, with at least 20 merchandise SKUs | High at ≥75% | Review stock availability, supplier dependency and category exposure |

The source data covers December 2009 to December 2011. Values in the Decision Brief therefore describe that historical sample; they must not be presented as current retailer performance.

## Definitions

- **Unidentified-customer revenue share**: share of included gross sales-line revenue attached to rows without an identified customer ID.
- **Leading-country revenue share**: share of gross sales-line revenue recorded in the highest-revenue country.
- **Top-20% customer revenue share**: share of identified-customer revenue attributed to the top 20% of identified customers by historical spend. Customer count is rounded up.
- **90-day second-purchase rate**: proportion of first-time identified customers with a complete 90-day observation window who made a second distinct invoice within 90 days.
- **Lift**: co-purchase confidence divided by the paired product's baseline purchase rate. Lift above 1 means above-baseline co-occurrence in the observed baskets.
- **Top-10 SKU share**: share of merchandise revenue attributed to the ten highest-revenue merchandise stock codes.

## Interpretation and use

These thresholds are diagnostic heuristics, not statistical significance tests and not universal industry benchmarks. A triggered rule should prompt an investigation, not an automatic pricing, inventory, marketing or market-entry decision.

Historical customer spend is not projected customer lifetime value. Revenue is not profit. Co-purchase association is not evidence that a bundle causes incremental sales. A country or SKU with high revenue share is not necessarily profitable or operationally risky. Validate commercial actions with cost, margin, shipping, returns, stock availability and controlled experiments.

The historical inactivity model is intentionally excluded from these business rules because it is a retrospective 2010–2011 proof of concept and must not be used to assign current customer risk.
