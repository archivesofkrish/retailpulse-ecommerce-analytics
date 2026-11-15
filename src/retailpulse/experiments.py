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


def evaluate_two_proportion_experiment(
    *,
    control_successes: int,
    control_trials: int,
    variant_successes: int,
    variant_trials: int,
    significance_level: float = 0.05,
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
    significant = p_value < alpha
    if significant and difference > 0:
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
        "decision": decision,
        "control_successes": control_successes,
        "control_trials": control_trials,
        "variant_successes": variant_successes,
        "variant_trials": variant_trials,
        "method": "Two-sided two-proportion z-test with pooled null standard error",
        "limitations": [
            "Statistical significance does not verify random assignment, instrumentation, exposure integrity, or absence of sample-ratio mismatch.",
            "The confidence interval uses a normal approximation; very small samples or extreme rates may require exact methods.",
            "Repeated peeking, multiple outcomes, or multiple variants require an appropriate sequential or multiplicity adjustment.",
            "The result estimates a difference for the supplied experiment sample; it is not automatically a long-term business impact estimate.",
        ],
    }
