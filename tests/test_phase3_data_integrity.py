from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.analysis import run_pipeline
import scripts.run_phase3_analysis as phase3


def _configure_phase3(tmp_path, monkeypatch):
    data_dir = tmp_path / "processed"
    output_dir = tmp_path / "reports" / "phase3"
    monkeypatch.setattr(phase3, "DATA", data_dir)
    monkeypatch.setattr(phase3, "OUT", output_dir)
    monkeypatch.setattr(phase3, "FIG", output_dir / "figures")
    data_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)
    return data_dir, output_dir


def test_phase3_preserves_zero_padded_and_alphanumeric_customer_ids(tmp_path, monkeypatch):
    data_dir, output_dir = _configure_phase3(tmp_path, monkeypatch)
    source = tmp_path / "transactions.csv"
    pd.DataFrame([
        {"Invoice": "100001", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "01/01/2011 10:00", "Price": 10.0, "Customer ID": "00123", "Country": "UK"},
        {"Invoice": "100002", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "02/01/2011 10:00", "Price": 10.0, "Customer ID": "00123", "Country": "UK"},
        {"Invoice": "100003", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "03/01/2011 10:00", "Price": 10.0, "Customer ID": "123", "Country": "UK"},
        {"Invoice": "100004", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "04/01/2011 10:00", "Price": 10.0, "Customer ID": "123", "Country": "UK"},
        {"Invoice": "100005", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "05/01/2011 10:00", "Price": 10.0, "Customer ID": "CUST-A", "Country": "UK"},
        {"Invoice": "100006", "StockCode": "A", "Description": "Alpha", "Quantity": 1,
         "InvoiceDate": "06/01/2011 10:00", "Price": 10.0, "Customer ID": "CUST-A", "Country": "UK"},
    ]).to_csv(source, index=False)

    run_pipeline(source, data_dir)
    sales, rfm, _segments, _products, _countries, kpis, _manifest = phase3.load_inputs()

    expected_ids = {"00123", "123", "CUST-A"}
    assert set(sales["customer_id_key"].dropna().unique()) == expected_ids
    assert set(rfm["customer_id"].dropna().unique()) == expected_ids

    customers, _segments, orders, metrics = phase3.make_customer_outputs(sales, rfm, kpis)
    assert set(customers["customer_id"]) == expected_ids
    assert set(orders["customer_id_key"]) == expected_ids
    assert metrics["identified_customers"] == 3

    phase3.make_cohort_outputs(sales)
    active = pd.read_csv(output_dir / "cohort_active_customer_counts.csv", index_col=0)
    assert active.loc["2011-01", "0"] == 3.0


def test_product_diagnostics_aggregate_duplicate_sku_lines_per_invoice(tmp_path, monkeypatch):
    _data_dir, output_dir = _configure_phase3(tmp_path, monkeypatch)
    sales = pd.DataFrame([
        {"invoice": "I-1", "stock_code": "A", "quantity": 2, "revenue": 20.0},
        {"invoice": "I-1", "stock_code": "A", "quantity": 3, "revenue": 30.0},
        {"invoice": "I-2", "stock_code": "A", "quantity": 1, "revenue": 10.0},
        {"invoice": "I-3", "stock_code": "A", "quantity": 4, "revenue": 40.0},
        {"invoice": "I-1", "stock_code": "B", "quantity": 1, "revenue": 8.0},
    ])
    products = pd.DataFrame([
        {"stock_code": "A", "description": "Alpha", "product_type": "Merchandise",
         "revenue": 100.0, "units": 10, "orders": 2},
        {"stock_code": "B", "description": "Beta", "product_type": "Merchandise",
         "revenue": 8.0, "units": 1, "orders": 1},
    ])

    product_codes, _operational, _metrics = phase3.make_product_outputs(sales, products)
    alpha = product_codes.set_index("stock_code").loc["A"]

    assert alpha["distinct_invoices"] == 3
    assert alpha["orders"] == 3
    assert alpha["max_single_invoice_units"] == 5
    assert alpha["max_single_invoice_revenue_gbp"] == 50.0
    saved = pd.read_csv(output_dir / "merchandise_product_concentration.csv")
    assert saved.set_index("stock_code").loc["A", "max_single_invoice_units"] == 5
