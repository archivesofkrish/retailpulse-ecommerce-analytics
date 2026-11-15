import math

import pytest

from retailpulse.scenarios import (
    build_repeat_purchase_scenarios,
    build_repeat_purchase_sensitivity,
)


def test_repeat_purchase_scenarios_calculate_expected_incremental_revenue():
    result = build_repeat_purchase_scenarios(
        eligible_customers=1000,
        baseline_repeat_rate_pct=30.0,
        average_order_value_gbp=25.0,
        uplift_scenarios_pp={
            "Conservative": 2.5,
            "Base": 5.0,
            "Stretch": 7.5,
        },
    )

    rows = result["scenarios"]
    assert [row["scenario"] for row in rows] == ["Conservative", "Base", "Stretch"]
    assert [row["expected_incremental_repeat_customers"] for row in rows] == [25.0, 50.0, 75.0]
    assert [row["expected_incremental_orders"] for row in rows] == [25.0, 50.0, 75.0]
    assert [row["expected_incremental_gross_revenue_gbp"] for row in rows] == [625.0, 1250.0, 1875.0]
    assert rows[1]["target_repeat_rate_pct"] == 35.0
    assert result["limitations"]


def test_sensitivity_curve_has_deterministic_endpoints():
    rows = build_repeat_purchase_sensitivity(
        eligible_customers=200,
        baseline_repeat_rate_pct=40.0,
        average_order_value_gbp=50.0,
        maximum_uplift_pp=10.0,
        points=5,
    )

    assert len(rows) == 5
    assert rows[0]["expected_incremental_gross_revenue_gbp"] == 0.0
    assert rows[-1]["target_repeat_rate_pct"] == 50.0
    assert rows[-1]["expected_incremental_gross_revenue_gbp"] == 1000.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"eligible_customers": True, "baseline_repeat_rate_pct": 20, "average_order_value_gbp": 10, "uplift_scenarios_pp": {"Base": 5}},
        {"eligible_customers": 0, "baseline_repeat_rate_pct": 20, "average_order_value_gbp": 10, "uplift_scenarios_pp": {"Base": 5}},
        {"eligible_customers": 100, "baseline_repeat_rate_pct": 101, "average_order_value_gbp": 10, "uplift_scenarios_pp": {"Base": 5}},
        {"eligible_customers": 100, "baseline_repeat_rate_pct": 95, "average_order_value_gbp": 10, "uplift_scenarios_pp": {"Base": 6}},
        {"eligible_customers": 100, "baseline_repeat_rate_pct": 20, "average_order_value_gbp": -1, "uplift_scenarios_pp": {"Base": 5}},
        {"eligible_customers": 100, "baseline_repeat_rate_pct": 20, "average_order_value_gbp": float("nan"), "uplift_scenarios_pp": {"Base": 5}},
    ],
)
def test_repeat_purchase_scenarios_reject_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        build_repeat_purchase_scenarios(**kwargs)


def test_scenarios_require_non_decreasing_uplifts():
    with pytest.raises(ValueError, match="non-decreasing"):
        build_repeat_purchase_scenarios(
            eligible_customers=100,
            baseline_repeat_rate_pct=25,
            average_order_value_gbp=30,
            uplift_scenarios_pp={"Conservative": 8, "Base": 5},
        )


@pytest.mark.parametrize("points", [1, 102, True])
def test_sensitivity_rejects_invalid_point_counts(points):
    with pytest.raises(ValueError, match="points"):
        build_repeat_purchase_sensitivity(
            eligible_customers=100,
            baseline_repeat_rate_pct=25,
            average_order_value_gbp=30,
            maximum_uplift_pp=10,
            points=points,
        )
