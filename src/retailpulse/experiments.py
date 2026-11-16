"""Planning and analysis utilities for binary A/B experiments.

These functions use normal-approximation two-proportion methods. They do not
randomise participants, monitor a live experiment, or establish causal validity.
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _validate_significance_level(value: Any) -> float:
    alpha = _finite_number("significance_level", value)
    if not 0 < alpha < 0.5:
        raise ValueError("significance_level must be greater than 0 and less than 0.5")
    return alpha


def plan_two_proportion_experiment(
    *,
    baseline_rate_pct: float,
    minimum_detectable_effect_pp: float,
    significance_level: float = 0.05,
    target_power: float = 0.80,
) -> dict[str, Any]:
    """Estimate equal-allocation sample size for a two-sided binary-outcome test.

    The alternative rate is baseline + MDE. The returned sample size is the
    required number of independent participants in each arm.
    """
    baseline_pct = _finite_number("baseline_rate_pct", baseline_rate_pct)
    effect_pp = _finite_number("minimum_detectable_effect_pp", minimum_detectable_effect_pp)
    alpha = _validate_significance_level(significance_level)
    power = _finite_number("target_power", target_power)

    if not 0 <= baseline_pct < 100:
        raise ValueError("baseline_rate_pct must be at least 0 and less than 100")
    if effect_pp <= 0 or baseline_pct + effect_pp > 100:
        raise ValueError(
            "minimum_detectable_effect_pp must be positive and keep the target rate at or below 100%"
        )
    if not 0.5 < power < 1:
        raise ValueError("target_power must be greater than 0.5 and less than 1")

    p_control = baseline_pct / 100
    p_variant = (baseline_pct + effect_pp) / 100
    pooled_alternative = (p_control + p_variant) / 2

    distribution = NormalDist()
    critical_value = distribution.inv_cdf(1 - alpha / 2)
    power_value = distribution.inv_cdf(power)
    variance_null = 2 * pooled_alternative * (1 - pooled_alternative)
    variance_alternative = (
        p_control * (1 - p_control) + p_variant * (1 - p_variant)
    )
    numerator = (
        critical_value * math.sqrt(variance_null)
        + power_value * math.sqrt(variance_alternative)
    ) ** 2
    sample_per_arm = math.ceil(numerator / ((p_variant - p_control) ** 2))

    return {
        "baseline_rate_pct": baseline_pct,
        "target_rate_pct": baseline_pct + effect_pp,
        "minimum_detectable_effect_pp": effect_pp,
        "significance_level": alpha,
        "target_power": power,
        "allocation": "50/50",
        "sample_size_per_arm": sample_per_arm,
        "total_sample_size": sample_per_arm * 2,
        "method": "Two-sided two-proportion z-test; normal-approximation planning formula",
        "limitations": [
            "Assumes independent participants, equal allocation, one binary primary outcome, and complete outcome measurement.",
            "Does not account for clustering, repeated exposure, attrition, non-compliance, multiple comparisons, or sequential peeking.",
            "A sample-size estimate does not guarantee adequate randomisation, clean instrumentation, or causal validity.",
        ],
    }


def evaluate_sample_ratio_mismatch(
    *,
    control_trials: int,
    variant_trials: int,
    expected_control_share: float = 0.5,
    significance_level: float = 0.001,
) -> dict[str, Any]:
    """Compare observed arm sizes with the pre-specified allocation.

    Uses Pearson's chi-square goodness-of-fit statistic with one degree of
    freedom. Expected arm counts below five are explicitly marked as too small
    for a dependable chi-square approximation.
    """
    alpha = _validate_significance_level(significance_level)
    expected_share = _finite_number("expected_control_share", expected_control_share)
    if not 0 < expected_share < 1:
        raise ValueError("expected_control_share must be greater than 0 and less than 1")
    for name, value in (
        ("control_trials", control_trials),
        ("variant_trials", variant_trials),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")

    total = control_trials + variant_trials
    expected_control = total * expected_share
    expected_variant = total * (1 - expected_share)
    statistic = (
        (control_trials - expected_control) ** 2 / expected_control
        + (variant_trials - expected_variant) ** 2 / expected_variant
    )
    p_value = min(1.0, max(0.0, math.erfc(math.sqrt(statistic / 2))))
    minimum_expected = min(expected_control, expected_variant)
    approximation_adequate = minimum_expected >= 5
    mismatch = p_value < alpha
    if not approximation_adequate:
        status = "LOW_EXPECTED_COUNT"
    elif mismatch:
        status = "SAMPLE_RATIO_MISMATCH"
    else:
        status = "OK"

    actual_control_share = control_trials / total
    return {
        "status": status,
        "sample_ratio_mismatch": mismatch,
        "approximation_adequate": approximation_adequate,
        "expected_control_share_pct": expected_share * 100,
        "expected_variant_share_pct": (1 - expected_share) * 100,
        "observed_control_share_pct": actual_control_share * 100,
        "observed_variant_share_pct": (1 - actual_control_share) * 100,
        "allocation_deviation_pp": (actual_control_share - expected_share) * 100,
        "expected_control_count": expected_control,
        "expected_variant_count": expected_variant,
        "observed_control_count": control_trials,
        "observed_variant_count": variant_trials,
        "minimum_expected_arm_count": minimum_expected,
        "chi_square_statistic": statistic,
        "degrees_of_freedom": 1,
        "p_value": p_value,
        "significance_level": alpha,
        "method": "Pearson chi-square goodness-of-fit test with one degree of freedom",
        "limitations": [
            "This checks arm-size allocation only; it cannot verify assignment randomness, exposure logging, eligibility rules, or outcome instrumentation.",
            "The chi-square approximation can be unreliable when either expected arm count is below five.",
            "Investigate a flagged imbalance before interpreting the conversion comparison; the diagnostic does not identify a specific failure cause.",
        ],
    }


def evaluate_two_proportion_experiment(
    *,
    control_successes: int,
    control_trials: int,
    variant_successes: int,
    variant_trials: int,
    significance_level: float = 0.05,
    expected_control_share: float = 0.5,
    sample_ratio_alpha: float = 0.001,
) -> dict[str, Any]:
    """Evaluate an independent two-arm binary outcome with a two-sided z-test.

    The difference and confidence interval are variant minus control. The
    confidence interval uses the unpooled standard error; the test uses the
    pooled standard error under the null hypothesis of equal proportions.
    """
    alpha = _validate_significance_level(significance_level)
    counts = {
        "control_successes": control_successes,
        "control_trials": control_trials,
        "variant_successes": variant_successes,
        "variant_trials": variant_trials,
    }
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if control_trials <= 0 or variant_trials <= 0:
        raise ValueError("trial counts must be greater than zero")
    if not 0 <= control_successes <= control_trials:
        raise ValueError("control_successes must be between zero and control_trials")
    if not 0 <= variant_successes <= variant_trials:
        raise ValueError("variant_successes must be between zero and variant_trials")

    sample_ratio_diagnostic = evaluate_sample_ratio_mismatch(
        control_trials=control_trials,
        variant_trials=variant_trials,
        expected_control_share=expected_control_share,
        significance_level=sample_ratio_alpha,
    )
    p_control = control_successes / control_trials
    p_variant = variant_successes / variant_trials
    difference = p_variant - p_control
    pooled = (control_successes + variant_successes) / (control_trials + variant_trials)
    pooled_se = math.sqrt(
        pooled * (1 - pooled) * (1 / control_trials + 1 / variant_trials)
    )
    if pooled_se == 0:
        z_score = 0.0
        p_value = 1.0
    else:
        z_score = difference / pooled_se
        p_value = min(1.0, max(0.0, 2 * (1 - NormalDist().cdf(abs(z_score)))))

    unpooled_se = math.sqrt(
        p_control * (1 - p_control) / control_trials
        + p_variant * (1 - p_variant) / variant_trials
    )
    critical_value = NormalDist().inv_cdf(1 - alpha / 2)
    lower = difference - critical_value * unpooled_se
    upper = difference + critical_value * unpooled_se
    # The pooled null rate defines the four expected success/failure cells.
    # A normal-approximation z-test is not a dependable decision rule when any
    # expected cell is sparse, even if the nominal p-value looks small.
    expected_outcome_cells = (
        control_trials * pooled,
        control_trials * (1 - pooled),
        variant_trials * pooled,
        variant_trials * (1 - pooled),
    )
    minimum_expected_outcome_cell = min(expected_outcome_cells)
    normal_approximation_adequate = minimum_expected_outcome_cell >= 5
    nominally_significant = p_value < alpha
    significant = normal_approximation_adequate and nominally_significant
    if not normal_approximation_adequate:
        decision = (
            "Inconclusive: at least one expected success/failure count is below five; "
            "the normal approximation may be unreliable. Use an exact method or collect more data."
        )
    elif significant and difference > 0:
        decision = "Evidence of a higher conversion rate in the variant"
    elif significant and difference < 0:
        decision = "Evidence of a lower conversion rate in the variant"
    else:
        decision = "Inconclusive at the selected significance level"

    return {
        "control_conversion_rate_pct": p_control * 100,
        "variant_conversion_rate_pct": p_variant * 100,
        "absolute_difference_pp": difference * 100,
        "relative_lift_pct": (difference / p_control * 100) if p_control > 0 else None,
        "confidence_level_pct": (1 - alpha) * 100,
        "difference_ci_lower_pp": lower * 100,
        "difference_ci_upper_pp": upper * 100,
        "z_score": z_score,
        "p_value": p_value,
        "significance_level": alpha,
        "statistically_significant": significant,
        "nominally_significant": nominally_significant,
        "normal_approximation_adequate": normal_approximation_adequate,
        "minimum_expected_outcome_cell_count": minimum_expected_outcome_cell,
        "decision": decision,
        "control_successes": control_successes,
        "control_trials": control_trials,
        "variant_successes": variant_successes,
        "variant_trials": variant_trials,
        "sample_ratio_diagnostic": sample_ratio_diagnostic,
        "method": "Two-sided two-proportion z-test with pooled null standard error",
        "limitations": [
            "Statistical significance does not verify random assignment, instrumentation or exposure integrity. Review the allocation diagnostic separately.",
            "The confidence interval uses a normal approximation; very small samples or extreme rates may require exact methods.",
            "Repeated peeking, multiple outcomes, or multiple variants require an appropriate sequential or multiplicity adjustment.",
            "The result estimates a difference for the supplied experiment sample; it is not automatically a long-term business impact estimate.",
        ],
    }
