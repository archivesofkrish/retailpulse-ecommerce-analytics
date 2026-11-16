"""Planning and analysis utilities for binary A/B experiments.

Planning uses a documented normal approximation. Evaluation selects a
two-proportion z-test or a two-sided Fisher exact test based on expected
outcome counts and reports a Newcombe-Wilson score interval. These functions
do not randomise participants, monitor a live experiment, or establish causal validity.
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
    """Compare observed arm sizes with the allocation declared before the test.

    Use Pearson's chi-square test when both expected arm counts are at least
    five. For sparse expected counts, use a bounded, probability-ordered exact
    binomial test. If its support exceeds the computation budget, return no
    p-value rather than substituting an unreliable approximation.
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
    minimum_expected = min(expected_control, expected_variant)
    approximation_adequate = minimum_expected >= 5
    statistic = (
        (control_trials - expected_control) ** 2 / expected_control
        + (variant_trials - expected_variant) ** 2 / expected_variant
    )

    if approximation_adequate:
        p_value = min(1.0, max(0.0, math.erfc(math.sqrt(statistic / 2))))
        inference_method = (
            "Pearson chi-square goodness-of-fit test with one degree of freedom"
        )
        inference_status = "PEARSON_CHI_SQUARE"
        mismatch: bool | None = p_value < alpha
        status = "SAMPLE_RATIO_MISMATCH" if mismatch else "OK"
    else:
        p_value = _probability_ordered_binomial_test(
            successes=control_trials,
            trials=total,
            probability=expected_share,
        )
        inference_method = "Two-sided probability-ordered exact binomial test"
        if p_value is None:
            inference_status = "EXACT_TABLE_LIMIT"
            mismatch = None
            status = "EXACT_TABLE_LIMIT"
        else:
            inference_status = "EXACT_BINOMIAL"
            mismatch = p_value < alpha
            status = "SAMPLE_RATIO_MISMATCH" if mismatch else "LOW_EXPECTED_COUNT"

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
        "chi_square_statistic": statistic if approximation_adequate else None,
        "degrees_of_freedom": 1 if approximation_adequate else None,
        "p_value": p_value,
        "significance_level": alpha,
        "method": inference_method,
        "inference_method": inference_method,
        "inference_status": inference_status,
        "exact_test_table_limit": MAX_EXACT_TABLES,
        "limitations": [
            "This checks arm-size allocation only; it cannot verify assignment randomness, exposure logging, eligibility rules, or outcome instrumentation.",
            "Sparse expected arm counts use an exact binomial test; its computation fails closed if the outcome support exceeds the configured limit.",
            "Investigate a flagged imbalance before interpreting the conversion comparison; the diagnostic does not identify a specific failure cause.",
        ],
    }

def _log_combination(n: int, k: int) -> float:
    """Return log(n choose k), using lgamma to avoid integer overflow."""
    if k < 0 or k > n:
        return -math.inf
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)




def _probability_ordered_binomial_test(
    *,
    successes: int,
    trials: int,
    probability: float,
    max_tables: int = MAX_EXACT_TABLES,
) -> float | None:
    """Calculate a bounded two-sided probability-ordered exact binomial p-value.

    Outcomes whose null probability is no greater than the observed outcome's
    probability are included. None means the support exceeds the configured
    computation budget; callers must not substitute an asymptotic p-value.
    """
    if trials + 1 > max_tables:
        return None

    log_probability = math.log(probability)
    log_complement = math.log1p(-probability)
    observed_log_probability = (
        _log_combination(trials, successes)
        + successes * log_probability
        + (trials - successes) * log_complement
    )

    included_log_probabilities = []
    for candidate in range(trials + 1):
        candidate_log_probability = (
            _log_combination(trials, candidate)
            + candidate * log_probability
            + (trials - candidate) * log_complement
        )
        if candidate_log_probability <= observed_log_probability + 1e-12:
            included_log_probabilities.append(candidate_log_probability)

    maximum = max(included_log_probabilities)
    log_p_value = maximum + math.log(
        math.fsum(math.exp(value - maximum) for value in included_log_probabilities)
    )
    if log_p_value < math.log(math.ulp(0.0)):
        return math.ulp(0.0)
    return min(1.0, max(0.0, math.exp(log_p_value)))

def _fisher_exact_two_sided(
    *,
    control_successes: int,
    control_trials: int,
    variant_successes: int,
    variant_trials: int,
    max_tables: int = 100_000,
) -> float | None:
    """Probability-ordered two-sided Fisher exact p-value.

    Conditioning on both arm sizes and the total success count gives a
    hypergeometric distribution for the control-arm success count. Return
    None rather than silently falling back to an untrusted approximation if
    the exact support exceeds the bounded computation budget.
    """
    total_trials = control_trials + variant_trials
    total_successes = control_successes + variant_successes
    lower = max(0, total_successes - variant_trials)
    upper = min(control_trials, total_successes)
    support_size = upper - lower + 1
    if support_size > max_tables:
        return None

    log_denominator = _log_combination(total_trials, control_trials)
    observed_log_probability = (
        _log_combination(total_successes, control_successes)
        + _log_combination(total_trials - total_successes,
                           control_trials - control_successes)
        - log_denominator
    )

    probabilities = []
    for candidate in range(lower, upper + 1):
        log_probability = (
            _log_combination(total_successes, candidate)
            + _log_combination(total_trials - total_successes,
                               control_trials - candidate)
            - log_denominator
        )
        # Probability ordering defines the conventional two-sided Fisher
        # test. The tolerance absorbs tiny lgamma rounding differences for
        # tables that are mathematically tied with the observed table.
        if log_probability <= observed_log_probability + 1e-12:
            probabilities.append(math.exp(log_probability))

    return min(1.0, max(0.0, math.fsum(probabilities)))


def _wilson_score_interval(
    successes: int, trials: int, critical_value: float
) -> tuple[float, float]:
    """Wilson score interval for one binomial proportion."""
    proportion = successes / trials
    z_squared = critical_value * critical_value
    denominator = 1 + z_squared / trials
    centre = (proportion + z_squared / (2 * trials)) / denominator
    half_width = (
        critical_value
        / denominator
        * math.sqrt(
            proportion * (1 - proportion) / trials
            + z_squared / (4 * trials * trials)
        )
    )
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def _newcombe_difference_interval(
    *,
    control_successes: int,
    control_trials: int,
    variant_successes: int,
    variant_trials: int,
    confidence_level: float,
) -> tuple[float, float]:
    """Newcombe hybrid score interval for variant minus control."""
    critical_value = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    control = control_successes / control_trials
    variant = variant_successes / variant_trials
    control_lower, control_upper = _wilson_score_interval(
        control_successes, control_trials, critical_value
    )
    variant_lower, variant_upper = _wilson_score_interval(
        variant_successes, variant_trials, critical_value
    )
    difference = variant - control
    lower = difference - math.sqrt(
        (variant - variant_lower) ** 2 + (control_upper - control) ** 2
    )
    upper = difference + math.sqrt(
        (variant_upper - variant) ** 2 + (control - control_lower) ** 2
    )
    return max(-1.0, lower), min(1.0, upper)


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
    """Evaluate an independent two-arm binary outcome.

    Use a pooled two-proportion z-test when all four expected outcome cells
    are at least five; otherwise use a probability-ordered two-sided Fisher
    exact test when its support fits the bounded computation budget. The
    difference interval is a Newcombe hybrid score interval based on Wilson
    score limits.
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
        nominal_p_value = 1.0
    else:
        z_score = difference / pooled_se
        nominal_p_value = min(
            1.0, max(0.0, 2 * (1 - NormalDist().cdf(abs(z_score))))
        )

    expected_outcome_cells = (
        control_trials * pooled,
        control_trials * (1 - pooled),
        variant_trials * pooled,
        variant_trials * (1 - pooled),
    )
    minimum_expected_outcome_cell = min(expected_outcome_cells)
    normal_approximation_adequate = minimum_expected_outcome_cell >= 5

    if normal_approximation_adequate:
        p_value = nominal_p_value
        inference_method = "Two-sided two-proportion z-test (pooled null standard error)"
        inference_status = "NORMAL_APPROXIMATION"
    else:
        exact_p_value = _fisher_exact_two_sided(
            control_successes=control_successes,
            control_trials=control_trials,
            variant_successes=variant_successes,
            variant_trials=variant_trials,
        )
        p_value = exact_p_value
        inference_method = "Two-sided Fisher exact test (probability-ordered)"
        inference_status = "FISHER_EXACT" if exact_p_value is not None else "EXACT_TABLE_LIMIT"

    confidence_level = 1 - alpha
    lower, upper = _newcombe_difference_interval(
        control_successes=control_successes,
        control_trials=control_trials,
        variant_successes=variant_successes,
        variant_trials=variant_trials,
        confidence_level=confidence_level,
    )
    significant = p_value is not None and p_value < alpha
    nominally_significant = nominal_p_value < alpha

    if p_value is None:
        decision = (
            "Inconclusive: the exact-test table support exceeds the configured "
            "computation limit. Use a validated exact-test implementation or "
            "collect more data."
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
        "confidence_level_pct": confidence_level * 100,
        "difference_ci_lower_pp": lower * 100,
        "difference_ci_upper_pp": upper * 100,
        "confidence_interval_method": "Newcombe hybrid score interval based on Wilson limits",
        "z_score": z_score,
        "p_value": p_value,
        "nominal_z_test_p_value": nominal_p_value,
        "significance_level": alpha,
        "statistically_significant": significant,
        "nominally_significant": nominally_significant,
        "normal_approximation_adequate": normal_approximation_adequate,
        "minimum_expected_outcome_cell_count": minimum_expected_outcome_cell,
        "inference_method": inference_method,
        "inference_status": inference_status,
        "decision": decision,
        "control_successes": control_successes,
        "control_trials": control_trials,
        "variant_successes": variant_successes,
        "variant_trials": variant_trials,
        "sample_ratio_diagnostic": sample_ratio_diagnostic,
        "method": inference_method,
        "limitations": [
            "Statistical significance does not verify random assignment, instrumentation or exposure integrity. Review the allocation diagnostic separately.",
            "The confidence interval uses a normal approximation; very small samples or extreme rates may require exact methods.",
            "Repeated peeking, multiple outcomes, or multiple variants require an appropriate sequential or multiplicity adjustment.",
            "The result estimates a difference for the supplied experiment sample; it is not automatically a long-term business impact estimate.",
        ],
    }
