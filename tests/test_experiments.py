import math

import pytest

from retailpulse.experiments import (
    evaluate_two_proportion_experiment,
    plan_two_proportion_experiment,
)


def test_sample_size_plan_returns_equal_allocation_and_documented_method():
    result = plan_two_proportion_experiment(
        baseline_rate_pct=10,
        minimum_detectable_effect_pp=2,
        significance_level=0.05,
        target_power=0.8,
    )

    assert result["sample_size_per_arm"] > 0
    assert result["total_sample_size"] == 2 * result["sample_size_per_arm"]
    assert result["target_rate_pct"] == 12
    assert result["allocation"] == "50/50"
    assert "two-proportion" in result["method"]


def test_larger_detectable_effect_requires_fewer_participants():
    small_effect = plan_two_proportion_experiment(
        baseline_rate_pct=10, minimum_detectable_effect_pp=1
    )
    large_effect = plan_two_proportion_experiment(
        baseline_rate_pct=10, minimum_detectable_effect_pp=3
    )
    assert large_effect["sample_size_per_arm"] < small_effect["sample_size_per_arm"]


def test_stricter_significance_and_higher_power_require_more_participants():
    standard = plan_two_proportion_experiment(
        baseline_rate_pct=10, minimum_detectable_effect_pp=2
    )
    stringent = plan_two_proportion_experiment(
        baseline_rate_pct=10,
        minimum_detectable_effect_pp=2,
        significance_level=0.01,
        target_power=0.9,
    )
    assert stringent["sample_size_per_arm"] > standard["sample_size_per_arm"]


def test_planner_accepts_zero_baseline_and_target_of_one_hundred_percent():
    result = plan_two_proportion_experiment(
        baseline_rate_pct=0, minimum_detectable_effect_pp=100
    )
    assert result["target_rate_pct"] == 100
    assert result["sample_size_per_arm"] > 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"baseline_rate_pct": 100, "minimum_detectable_effect_pp": 1}, "baseline_rate_pct"),
        ({"baseline_rate_pct": 98, "minimum_detectable_effect_pp": 3}, "target rate"),
        ({"baseline_rate_pct": 10, "minimum_detectable_effect_pp": 0}, "positive"),
        ({"baseline_rate_pct": 10, "minimum_detectable_effect_pp": 1, "significance_level": 0}, "significance_level"),
        ({"baseline_rate_pct": 10, "minimum_detectable_effect_pp": 1, "target_power": 0.5}, "target_power"),
        ({"baseline_rate_pct": True, "minimum_detectable_effect_pp": 1}, "baseline_rate_pct"),
        ({"baseline_rate_pct": math.nan, "minimum_detectable_effect_pp": 1}, "baseline_rate_pct"),
        ({"baseline_rate_pct": 10, "minimum_detectable_effect_pp": math.inf}, "minimum_detectable_effect_pp"),
    ],
)
def test_planner_rejects_invalid_inputs(kwargs, message):
    with pytest.raises(ValueError, match=message):
        plan_two_proportion_experiment(**kwargs)


def test_evaluator_detects_a_statistically_significant_variant_improvement():
    result = evaluate_two_proportion_experiment(
        control_successes=10,
        control_trials=100,
        variant_successes=20,
        variant_trials=100,
    )
    assert result["statistically_significant"] is True
    assert result["p_value"] < 0.05
    assert result["absolute_difference_pp"] == 10
    assert result["difference_ci_lower_pp"] > 0
    assert result["decision"].startswith("Evidence of a higher")


def test_evaluator_reports_inconclusive_when_evidence_is_weak():
    result = evaluate_two_proportion_experiment(
        control_successes=10,
        control_trials=100,
        variant_successes=12,
        variant_trials=100,
    )
    assert result["statistically_significant"] is False
    assert result["decision"].startswith("Inconclusive")
    assert result["difference_ci_lower_pp"] <= 0 <= result["difference_ci_upper_pp"]


def test_evaluator_handles_zero_baseline_without_infinite_relative_lift():
    result = evaluate_two_proportion_experiment(
        control_successes=0, control_trials=100,
        variant_successes=5, variant_trials=100,
    )
    assert result["relative_lift_pct"] is None
    assert result["control_conversion_rate_pct"] == 0


def test_evaluator_handles_equal_zero_outcomes():
    result = evaluate_two_proportion_experiment(
        control_successes=0, control_trials=50,
        variant_successes=0, variant_trials=50,
    )
    assert result["p_value"] == 1
    assert result["statistically_significant"] is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"control_successes": 1, "control_trials": 0, "variant_successes": 1, "variant_trials": 10}, "greater than zero"),
        ({"control_successes": 11, "control_trials": 10, "variant_successes": 1, "variant_trials": 10}, "between zero"),
        ({"control_successes": True, "control_trials": 10, "variant_successes": 1, "variant_trials": 10}, "must be an integer"),
        ({"control_successes": 1, "control_trials": 10, "variant_successes": 1, "variant_trials": 10, "significance_level": 1}, "significance_level"),
    ],
)
def test_evaluator_rejects_invalid_counts_and_alpha(kwargs, message):
    with pytest.raises(ValueError, match=message):
        evaluate_two_proportion_experiment(**kwargs)
