# Experiment Studio

## Purpose

Experiment Studio is a planning and post-test analysis aid for controlled experiments with a binary outcome (for example, whether an eligible participant converted during a pre-defined observation window). It supports:

1. Estimating the participant count needed in two equal-sized arms to detect a specified minimum absolute conversion-rate difference.
2. Inspecting how the required sample changes as the minimum detectable effect changes.
3. Evaluating observed control and variant counts with an adaptive z-test or Fisher exact test and a score-based confidence interval for the absolute difference.
4. Checking whether observed control/variant sample sizes match the allocation ratio declared before the experiment.

It does not assign participants, record exposures, monitor a running experiment, or prove that an experiment was randomised correctly.

## Sample-size method

Let:

- `p1` be the assumed control conversion proportion;
- `p2` be the target variant proportion (`p2 = p1 + delta`);
- `delta` be the minimum detectable effect as an absolute proportion, not a relative percentage;
- `p_bar = (p1 + p2) / 2`;
- `alpha` be the two-sided significance level; and
- `power = 1 - beta` be the target statistical power.

The normal-approximation planning formula for each arm is:

```text
n = ceil(
    (
        z_(1 - alpha/2) * sqrt(2 * p_bar * (1 - p_bar))
        + z_(power) * sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    / (p2 - p1) ** 2
)
```

Here, `z_q` is the standard-normal quantile whose cumulative probability is `q`. The total target sample is `2 * n`, before any allowance for attrition or ineligible observations. Enrollment duration is estimated as total sample divided by the user-entered number of eligible participants available per day. That traffic input is never inferred from the historical workbook.

## Post-test readout

The evaluator accepts successes and total participants for each arm. It reports observed conversion rates, absolute difference (variant minus control) in percentage points, relative lift when the control rate is non-zero, a two-sided p-value, and a Newcombe hybrid score confidence interval based on Wilson score limits.

The evaluator computes the four expected success/failure cells under the pooled null rate. When all are at least five, it uses the pooled two-proportion z-test. When any is below five, it switches to a two-sided, probability-ordered Fisher exact test. The exact calculation is bounded to 100,000 possible tables; if that limit is exceeded, the p-value is not computed and the decision is **Inconclusive** rather than silently falling back to an unreliable normal approximation. The nominal z-test p-value is separately exposed for diagnostic transparency. A non-significant result is described as inconclusive—not proof that the variants are equivalent.

## Sample-ratio mismatch diagnostic

The completed-test evaluator also compares observed arm counts with the expected allocation share supplied before the test. Let `N` be the total participants and `q` the expected control share. Expected counts are `E_control = N × q` and `E_variant = N × (1 − q)`. The diagnostic computes:

```text
chi_square = sum((observed_arm_count - expected_arm_count)^2 / expected_arm_count)
p_value = erfc(sqrt(chi_square / 2))
```

This is the Pearson goodness-of-fit test with one degree of freedom. The default alert threshold is **p < 0.001**, a conservative diagnostic threshold distinct from the conversion test's usual alpha. A lower p-value raises a sample-ratio-mismatch warning.

The diagnostic accepts a pre-declared non-50/50 allocation, so a planned 90/10 split is not incorrectly flagged as imbalanced. If either expected arm count is below five, the UI warns that the chi-square approximation is not dependable. Collect more data or use a suitable exact allocation test for small expected counts.

A mismatch is a signal to investigate assignment, eligibility, exposure logging and instrumentation before interpreting the conversion result. It does not identify which process failed, and a clean allocation check does not prove that the experiment was randomised correctly.

## Assumptions and limitations

- Participants are independent observations and are allocated equally between arms for the planning calculation.
- There is one pre-specified binary primary outcome and one consistent observation window.
- The planning calculation uses a normal approximation and does not model clustering, repeated exposure, non-compliance or attrition. The separate sample-ratio diagnostic checks observed arm sizes only.
- The post-test readout is not adjusted for repeated interim peeking, multiple metrics or multiple variants. Use an appropriate sequential or multiplicity-control method when these apply.
- The confidence interval uses the Newcombe hybrid score method built from Wilson score limits. It is bounded to the valid difference range [-100, 100] percentage points and behaves better than a Wald interval near extreme conversion rates. The confidence interval remains an approximation; small samples and sparse outcomes should be interpreted with the inference method and assumptions shown.
- Statistical significance does not establish randomisation quality, instrumentation correctness, absence of selection bias or long-term business impact.
- A non-flagged sample-ratio diagnostic does not certify randomisation, event logging, eligibility or outcome instrumentation.
- UCI Online Retail II covers 1 December 2009–9 December 2011. Its 90-day repeat-purchase rate can appear as a labelled historical reference only; it is not a current conversion baseline and does not supply present-day traffic.
- Revenue, where considered in other RetailPulse panels, remains historical gross revenue and is not profit.

## Reproduction

```bash
python -W error::DeprecationWarning -m pytest -q
streamlit run dashboard/app.py
```

The pure calculation functions live in `src/retailpulse/experiments.py`, with regression coverage in `tests/test_experiments.py`.
