"""Transparent scenario calculations for repeat-purchase planning.

Outputs are assumption-driven revenue scenarios, not forecasts or causal lift estimates.
"""

from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from retailpulse.metric_validation import finite_number, non_negative_count, percentage


def _validated_order_value(value: Any) -> float:
    parsed = finite_number(value)
    if parsed is None or parsed < 0:
        raise ValueError("average_order_value_gbp must be a finite non-negative number")
    if parsed > 1_000_000_000:
        raise ValueError("average_order_value_gbp exceeds the supported upper bound")
    return parsed


def build_repeat_purchase_scenarios(
    *,
    eligible_customers: int,
    baseline_repeat_rate_pct: float,
    average_order_value_gbp: float,
    uplift_scenarios_pp: Mapping[str, float],
) -> dict[str, Any]:
    """Calculate additional second orders and gross revenue under explicit assumptions.

    Each additional repeat customer is assumed to place one additional order
    at the supplied average order value. Expected customer/order counts may be
    fractional because they are scenario expectations, not observed people.
    """
    count = non_negative_count(eligible_customers)
    if count is None or count <= 0 or type(eligible_customers) is not int:
        raise ValueError("eligible_customers must be a positive integer")

    baseline = percentage(baseline_repeat_rate_pct)
    if baseline is None:
        raise ValueError("baseline_repeat_rate_pct must be finite and between 0 and 100")

    order_value = _validated_order_value(average_order_value_gbp)
    if not isinstance(uplift_scenarios_pp, Mapping) or not uplift_scenarios_pp:
        raise ValueError("uplift_scenarios_pp must be a non-empty mapping")

    maximum_uplift = 100.0 - baseline
    scenarios = []
    previous_uplift = -1.0
    for name, raw_uplift in uplift_scenarios_pp.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Scenario names must be non-empty strings")
        uplift = finite_number(raw_uplift)
        if uplift is None or not 0 <= uplift <= maximum_uplift:
            raise ValueError(
                f"Uplift for {name!r} must be between 0 and {maximum_uplift:.2f} percentage points"
            )
        if uplift < previous_uplift:
            raise ValueError("Uplift scenarios must be supplied in non-decreasing order")
        previous_uplift = uplift

        target_rate = baseline + uplift
        expected_repeat_customers = count * target_rate / 100.0
        expected_baseline_repeat_customers = count * baseline / 100.0
        incremental_customers = count * uplift / 100.0
        incremental_orders = incremental_customers
        incremental_revenue = incremental_orders * order_value
        scenarios.append({
            "scenario": name.strip(),
            "eligible_customers": count,
            "baseline_repeat_rate_pct": baseline,
            "uplift_percentage_points": uplift,
            "target_repeat_rate_pct": target_rate,
            "expected_baseline_repeat_customers": expected_baseline_repeat_customers,
            "expected_repeat_customers": expected_repeat_customers,
            "expected_incremental_repeat_customers": incremental_customers,
            "expected_incremental_orders": incremental_orders,
            "average_order_value_gbp": order_value,
            "expected_incremental_gross_revenue_gbp": incremental_revenue,
        })

    return {
        "eligible_customers": count,
        "baseline_repeat_rate_pct": baseline,
        "average_order_value_gbp": order_value,
        "assumption": "Each incremental repeat customer places one additional order at the historical identified-customer average order value.",
        "scenarios": scenarios,
        "limitations": [
            "The uplift values are user-defined assumptions, not model predictions or measured treatment effects.",
            "Expected incremental customer and order counts can be fractional; they are planning expectations, not actual counts.",
            "Revenue is gross sales revenue, not profit or contribution. No margin, acquisition cost, campaign cost, returns adjustment or capacity constraint is modelled.",
            "The historical source ends on 9 December 2011 and is not a live customer feed.",
            "A controlled experiment is required to estimate causal incremental impact.",
        ],
    }


def build_repeat_purchase_sensitivity(
    *,
    eligible_customers: int,
    baseline_repeat_rate_pct: float,
    average_order_value_gbp: float,
    maximum_uplift_pp: float,
    points: int = 21,
) -> list[dict[str, float]]:
    """Return a deterministic uplift-to-gross-revenue sensitivity curve."""
    count = non_negative_count(eligible_customers)
    if count is None or count <= 0 or type(eligible_customers) is not int:
        raise ValueError("eligible_customers must be a positive integer")
    baseline = percentage(baseline_repeat_rate_pct)
    if baseline is None:
        raise ValueError("baseline_repeat_rate_pct must be finite and between 0 and 100")
    order_value = _validated_order_value(average_order_value_gbp)
    maximum = finite_number(maximum_uplift_pp)
    if maximum is None or not 0 <= maximum <= 100.0 - baseline:
        raise ValueError(
            f"maximum_uplift_pp must be between 0 and {100.0 - baseline:.2f} percentage points"
        )
    if type(points) is not int or not 2 <= points <= 101:
        raise ValueError("points must be an integer between 2 and 101")

    rows = []
    for index in range(points):
        uplift = maximum * index / (points - 1)
        customers = count * uplift / 100.0
        rows.append({
            "uplift_percentage_points": uplift,
            "target_repeat_rate_pct": baseline + uplift,
            "expected_incremental_repeat_customers": customers,
            "expected_incremental_gross_revenue_gbp": customers * order_value,
        })
    return rows
