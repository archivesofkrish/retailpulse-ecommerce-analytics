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


def test_sample_ratio_diagnostic_accepts_expected_equal_allocation():
    from retailpulse.experiments import evaluate_sample_ratio_mismatch

    result = evaluate_sample_ratio_mismatch(control_trials=10_000, variant_trials=10_000)
    assert result["status"] == "OK"
    assert result["p_value"] == 1
    assert result["sample_ratio_mismatch"] is False
    assert result["approximation_adequate"] is True
    assert result["allocation_deviation_pp"] == 0


def test_sample_ratio_diagnostic_flags_large_allocation_imbalance():
    from retailpulse.experiments import evaluate_sample_ratio_mismatch

    result = evaluate_sample_ratio_mismatch(
        control_trials=12_000, variant_trials=8_000, expected_control_share=0.5
    )
    assert result["status"] == "SAMPLE_RATIO_MISMATCH"
    assert result["sample_ratio_mismatch"] is True
    assert result["p_value"] < 0.001
    assert result["allocation_deviation_pp"] == pytest.approx(10)


def test_sample_ratio_diagnostic_respects_predeclared_non_equal_allocation():
    from retailpulse.experiments import evaluate_sample_ratio_mismatch

    result = evaluate_sample_ratio_mismatch(
        control_trials=9_000, variant_trials=1_000, expected_control_share=0.9
    )
    assert result["status"] == "OK"
    assert result["p_value"] == pytest.approx(1)
    assert result["expected_variant_share_pct"] == pytest.approx(10)


def test_sample_ratio_diagnostic_warns_for_small_expected_counts():
    from retailpulse.experiments import evaluate_sample_ratio_mismatch

    result = evaluate_sample_ratio_mismatch(control_trials=2, variant_trials=1)
    assert result["status"] == "LOW_EXPECTED_COUNT"
    assert result["approximation_adequate"] is False
    assert result["minimum_expected_arm_count"] < 5


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"control_trials": 0, "variant_trials": 10}, "greater than zero"),
        ({"control_trials": True, "variant_trials": 10}, "must be an integer"),
        ({"control_trials": 10, "variant_trials": 10, "expected_control_share": 0}, "greater than 0"),
        ({"control_trials": 10, "variant_trials": 10, "expected_control_share": math.nan}, "finite number"),
        ({"control_trials": 10, "variant_trials": 10, "significance_level": 0}, "significance_level"),
    ],
)
def test_sample_ratio_diagnostic_rejects_invalid_inputs(kwargs, message):
    from retailpulse.experiments import evaluate_sample_ratio_mismatch

    with pytest.raises(ValueError, match=message):
        evaluate_sample_ratio_mismatch(**kwargs)


def test_two_proportion_evaluator_includes_sample_ratio_diagnostic():
    result = evaluate_two_proportion_experiment(
        control_successes=60, control_trials=12_000,
        variant_successes=100, variant_trials=8_000,
        expected_control_share=0.5,
    )
    assert result["sample_ratio_diagnostic"]["status"] == "SAMPLE_RATIO_MISMATCH"



def test_sparse_expected_cells_use_two_sided_fisher_exact_test():
    result = evaluate_two_proportion_experiment(
        control_successes=0,
        control_trials=5,
        variant_successes=5,
        variant_trials=5,
    )

    assert result["normal_approximation_adequate"] is False
    assert result["minimum_expected_outcome_cell_count"] == pytest.approx(2.5)
    assert result["inference_status"] == "FISHER_EXACT"
    assert result["inference_method"].startswith("Two-sided Fisher exact")
    assert result["p_value"] == pytest.approx(2 / 252)
    assert result["statistically_significant"] is True
    assert result["decision"].startswith("Evidence of a higher")
    assert result["difference_ci_lower_pp"] <= 100
    assert result["difference_ci_upper_pp"] == pytest.approx(100)


def test_newcombe_interval_is_bounded_and_contains_observed_difference():
    result = evaluate_two_proportion_experiment(
        control_successes=0, control_trials=20,
        variant_successes=20, variant_trials=20,
    )
    assert result["confidence_interval_method"].startswith("Newcombe")
    assert -100 <= result["difference_ci_lower_pp"] <= 100
    assert -100 <= result["difference_ci_upper_pp"] <= 100
    assert result["difference_ci_lower_pp"] <= result["absolute_difference_pp"]
    assert result["difference_ci_upper_pp"] >= result["absolute_difference_pp"]


def test_exact_test_computation_limit_fails_closed():
    result = evaluate_two_proportion_experiment(
        control_successes=2_000_000,
        control_trials=100_000_000,
        variant_successes=2_000_000,
        variant_trials=100_000_000_000_000,
    )
    assert result["normal_approximation_adequate"] is False
    assert result["inference_status"] == "EXACT_TABLE_LIMIT"
    assert result["p_value"] is None
    assert result["statistically_significant"] is False
    assert result["decision"].startswith("Inconclusive:")
