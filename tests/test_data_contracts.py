from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.analysis import prepare_transactions, standardise_columns


def _row(invoice, *, stock_code="SKU-1", quantity=1, price=2.0, customer_id=123):
    return {
        "Invoice": invoice,
        "StockCode": stock_code,
        "Description": "Test item",
        "Quantity": quantity,
        "InvoiceDate": "15/01/2011 10:30",
        "Price": price,
        "Customer ID": customer_id,
        "Country": "United Kingdom",
    }


def test_blank_invoice_and_stock_code_are_rejected():
    raw = pd.DataFrame([
        _row("   "),
        _row("100002", stock_code="   "),
        _row("100003"),
    ])

    prepared, stats = prepare_transactions(raw)

    assert prepared["invoice"].tolist() == ["100003"]
    assert stats["rows_dropped_invalid_core_fields"] == 2
    assert stats["rows_after_core_validation"] == 1


def test_infinite_numeric_values_and_overflowed_line_values_are_rejected():
    raw = pd.DataFrame([
        _row("100001", quantity=np.inf),
        _row("100002", price=np.inf),
        _row("100003", quantity=1e308, price=1e308),
        _row("100004", price=2.0),
    ])

    prepared, stats = prepare_transactions(raw)

    assert prepared["invoice"].tolist() == ["100004"]
    assert stats["rows_non_finite_numeric_values"] == 2
    assert stats["rows_dropped_non_finite_line_value"] == 1
    assert stats["rows_dropped_invalid_core_fields"] == 3
    assert np.isfinite(prepared["line_value"]).all()


def test_customer_ids_are_normalised_without_losing_zero_padding():
    raw = pd.DataFrame([
        _row("100001", customer_id=123.0),
        _row("100002", customer_id="123.0"),
        _row("100003", customer_id="00123"),
        _row("100004", customer_id=" CUST-01 "),
        _row("100005", customer_id="12.5"),
        _row("100006", customer_id=np.inf),
        _row("100007", customer_id=None),
    ])

    prepared, stats = prepare_transactions(raw)
    ids = prepared.set_index("invoice")["customer_id"]

    assert ids.loc["100001"] == "123"
    assert ids.loc["100002"] == "123"
    assert ids.loc["100003"] == "00123"
    assert ids.loc["100004"] == "CUST-01"
    assert pd.isna(ids.loc["100005"])
    assert pd.isna(ids.loc["100006"])
    assert pd.isna(ids.loc["100007"])
    assert stats["rows_invalid_customer_id"] == 2
    assert stats["rows_missing_customer_id"] == 3


def test_ambiguous_alias_columns_fail_with_actionable_error():
    raw = pd.DataFrame({
        "Invoice": ["100001"],
        "InvoiceNo": ["100001"],
        "StockCode": ["SKU-1"],
        "Quantity": [1],
        "InvoiceDate": ["15/01/2011"],
        "Price": [2.0],
        "Country": ["United Kingdom"],
    })

    with pytest.raises(ValueError, match="Multiple source columns map to 'invoice'"):
        standardise_columns(raw)


def test_duplicate_headers_after_normalisation_are_rejected():
    raw = pd.DataFrame(
        [["100001", "100002", "SKU-1", 1, "15/01/2011", 2.0, "United Kingdom"]],
        columns=["Invoice", " invoice ", "StockCode", "Quantity", "InvoiceDate", "Price", "Country"],
    )

    with pytest.raises(ValueError, match="Ambiguous source headers"):
        standardise_columns(raw)
