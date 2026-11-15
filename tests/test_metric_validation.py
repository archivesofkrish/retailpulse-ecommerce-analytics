import math

import pytest

from retailpulse.metric_validation import finite_number, non_negative_count, percentage


@pytest.mark.parametrize("value", [None, True, False, "bad", float("nan"), float("inf"), -float("inf")])
def test_finite_number_rejects_invalid_or_non_finite_values(value):
    assert finite_number(value) is None


def test_finite_number_accepts_numeric_strings_and_numbers():
    assert finite_number("12.5") == 12.5
    assert finite_number(4) == 4.0


@pytest.mark.parametrize("value", [-1, 1.5, "nan", True, float("inf")])
def test_non_negative_count_rejects_invalid_counts(value):
    assert non_negative_count(value) is None


def test_non_negative_count_accepts_integral_values():
    assert non_negative_count(0) == 0
    assert non_negative_count("12") == 12
    assert non_negative_count(12.0) == 12


@pytest.mark.parametrize("value", [-0.1, 100.1, "nan", True, float("inf")])
def test_percentage_rejects_out_of_range_or_invalid_values(value):
    assert percentage(value) is None


def test_percentage_accepts_endpoints_and_interior():
    assert percentage(0) == 0.0
    assert percentage(100) == 100.0
    assert percentage("37.5") == 37.5
