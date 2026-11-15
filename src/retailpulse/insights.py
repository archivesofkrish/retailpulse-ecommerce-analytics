"""Transparent, evidence-backed business insight rules for RetailPulse.

These rules surface historical patterns for investigation. They do not infer
causality, profitability or expected financial returns.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from retailpulse.metric_validation import finite_number, non_negative_count, percentage

INSIGHT_COLUMNS = [
    "insight_id",
    "priority",
    "area",
    "headline",
    "evidence",
    "trigger_rule",
    "recommended_action",
    "guardrail",
]


def _number(value: Any) -> float | None:
    """Return a finite float, or None for absent/invalid/non-finite inputs."""
    return finite_number(value)


def _find_record(
    records: Sequence[Mapping[str, Any]],
    key: str,
    expected: float,
) -> Mapping[str, Any] | None:
    for record in records:
        value = _number(record.get(key))
        if value is not None and math.isclose(value, expected, abs_tol=1e-9):
            return record
    return None


def generate_business_insights(
    *,
    kpis: Mapping[str, Any],
    customer_metrics: Mapping[str, Any],
    country_metrics: Mapping[str, Any],
    product_metrics: Mapping[str, Any],
    repeat_purchase_windows: Sequence[Mapping[str, Any]],
    affinity_rules: Sequence[Mapping[str, Any]],
    minimum_repeat_eligible_customers: int = 20,
    minimum_affinity_joint_orders: int = 20,
) -> list[dict[str, str]]:
    """Return a stable list of triggered recommendations with explicit evidence.

    The thresholds are diagnostic heuristics, not statistical significance
    tests. They are deliberately conservative and recorded in each result.
    """
    insights: list[dict[str, str]] = []

    def add(
        insight_id: str,
        priority: str,
        area: str,
        headline: str,
        evidence: str,
        trigger_rule: str,
        recommended_action: str,
        guardrail: str,
    ) -> None:
        insights.append({
            "insight_id": insight_id,
            "priority": priority,
            "area": area,
            "headline": headline,
            "evidence": evidence,
            "trigger_rule": trigger_rule,
            "recommended_action": recommended_action,
            "guardrail": guardrail,
        })

    # 1. Customer identity coverage: anonymous lines weaken customer economics.
    anonymous_share = percentage(kpis.get("unidentified_customer_revenue_share_pct"))
    if anonymous_share is not None and anonymous_share >= 10.0:
        priority = "High" if anonymous_share >= 20.0 else "Medium"
        add(
            "customer_identity_gap",
            priority,
            "Customer data",
            "A material share of sales revenue is not linked to a customer ID",
            f"{anonymous_share:.1f}% of gross sales-line revenue is associated with unidentified customers.",
            "Trigger when unidentified-customer revenue share is at least 10%; High priority at 20% or more.",
            "Audit the checkout and customer-identification process, quantify where IDs are missing, and test improvements to capture or match rates.",
            "Do not infer that anonymous buyers are all distinct people. Historical customer revenue and retention metrics cover identified customers only.",
        )

    # 2. Geographic concentration: high dependence deserves market-risk review.
    country_share = percentage(country_metrics.get("top_country_revenue_share_pct"))
    top_country = country_metrics.get("top_country")
    if country_share is not None and top_country and country_share >= 75.0:
        priority = "High" if country_share >= 85.0 else "Medium"
        add(
            "geographic_concentration",
            priority,
            "Market exposure",
            f"Sales are highly concentrated in {top_country}",
            f"{top_country} contributes {country_share:.1f}% of gross sales-line revenue.",
            "Trigger when the leading country contributes at least 75%; High priority at 85% or more.",
            "Review the exposure alongside country-level margin, shipping cost, returns, customer repeat rates and service constraints before setting diversification priorities.",
            "Revenue share alone does not establish market profitability, addressable demand or the attractiveness of another country.",
        )

    # 3. Customer concentration: protect revenue relationships without assuming causality.
    top20 = _find_record(
        customer_metrics.get("top_customer_concentration", []),
        "top_customer_share_pct",
        20.0,
    )
    top20_share = percentage(top20.get("identified_revenue_share_pct")) if top20 else None
    if top20_share is not None and top20_share >= 50.0:
        priority = "High" if top20_share >= 60.0 else "Medium"
        customer_count = non_negative_count(top20.get("customers")) or 0
        add(
            "customer_revenue_concentration",
            priority,
            "Customer portfolio",
            "A relatively small customer group contributes a large share of identified revenue",
            f"The top 20% of identified customers ({customer_count:,} customers) account for {top20_share:.1f}% of identified-customer revenue.",
            "Trigger when the top 20% of identified customers account for at least 50%; High priority at 60% or more.",
            "Design a retention and service review for high-value customer cohorts, and measure incremental outcomes with a holdout group.",
            "This is historical revenue concentration, not a forecast of future revenue at risk or customer profitability.",
        )

    # 4. Repeat purchase friction: only surface with a meaningful eligible base.
    repeat90 = _find_record(repeat_purchase_windows, "follow_up_days", 90)
    if repeat90:
        repeat_rate = percentage(repeat90.get("second_order_within_window_pct"))
        eligible = non_negative_count(repeat90.get("eligible_customers")) or 0
        if repeat_rate is not None and eligible >= minimum_repeat_eligible_customers and repeat_rate <= 40.0:
            priority = "High" if repeat_rate <= 25.0 else "Medium"
            add(
                "second_purchase_conversion",
                priority,
                "Retention journey",
                "Second-purchase conversion is low among customers with full 90-day follow-up",
                f"{repeat_rate:.1f}% of {eligible:,} eligible first-time customers placed a second order within 90 days.",
                f"Trigger when 90-day second-purchase rate is at most 40% and at least {minimum_repeat_eligible_customers} customers have a complete 90-day observation window; High priority at 25% or less.",
                "Map the post-first-purchase journey and run controlled tests of product discovery, onboarding and replenishment communications.",
                "This is an observed historical repeat-purchase rate, not a current conversion benchmark. Customers have different purchase cycles; test interventions before attributing effects.",
            )

    # 5. Basket associations: surface only patterns with more than a handful of invoices.
    qualified_rules = []
    for rule in affinity_rules:
        lift = _number(rule.get("lift"))
        joint = non_negative_count(rule.get("joint_orders")) or 0
        if lift is not None and joint >= minimum_affinity_joint_orders:
            qualified_rules.append((lift, joint, rule))
    if qualified_rules:
        lift, joint, rule = max(
            qualified_rules,
            key=lambda item: (item[0], item[1], str(item[2].get("antecedent_stock_code", ""))),
        )
        if lift >= 1.5:
            confidence = percentage(rule.get("confidence_pct"))
            support = percentage(rule.get("support_pct"))
            anchor = f"{rule.get('antecedent_stock_code', '')} — {rule.get('antecedent_description', 'Product')}"
            paired = f"{rule.get('consequent_stock_code', '')} — {rule.get('consequent_description', 'Product')}"
            confidence_text = f", confidence {confidence:.1f}%" if confidence is not None else ""
            support_text = f", support {support:.3f}%" if support is not None else ""
            add(
                "product_cross_sell_candidate",
                "Medium",
                "Merchandising",
                "A product pair shows above-baseline co-purchase",
                f"{anchor} and {paired} appear together on {joint:,} invoices (lift {lift:.2f}x{confidence_text}{support_text}).",
                f"Trigger when at least {minimum_affinity_joint_orders} invoices contain the pair and lift is at least 1.5.",
                "Treat the pair as a candidate for a merchandising or recommendation experiment; compare incremental conversion and gross margin against a control group.",
                "Association is not causation. Lift does not establish that a promotion or recommendation will create incremental sales or profit.",
            )

    # 6. Product assortment concentration: only compare meaningful catalogues.
    sku_count = non_negative_count(product_metrics.get("merchandise_stock_codes")) or 0
    top10_share = percentage(product_metrics.get("top_10_merchandise_stock_code_revenue_share_pct"))
    if sku_count >= 20 and top10_share is not None and top10_share >= 60.0:
        priority = "High" if top10_share >= 75.0 else "Medium"
        add(
            "merchandise_assortment_concentration",
            priority,
            "Merchandise portfolio",
            "Merchandise revenue is concentrated in a small set of stock codes",
            f"The top 10 stock codes contribute {top10_share:.1f}% of merchandise revenue across {sku_count:,} merchandise stock codes.",
            "Trigger when at least 20 merchandise stock codes exist and the top 10 contribute at least 60% of merchandise revenue; High priority at 75% or more.",
            "Review stock availability, supplier dependency, substitution options and category strategy for the leading products.",
            "Revenue concentration is not profitability or supply-chain risk by itself; validate with margin, stock-out, supplier and lead-time data.",
        )

    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(
        insights,
        key=lambda item: (priority_order.get(item["priority"], 9), item["area"], item["insight_id"]),
    )
