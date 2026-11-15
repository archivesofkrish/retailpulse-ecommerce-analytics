from pathlib import Path
import sys
import pandas as pd
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.analysis import prepare_transactions, calculate_analytics, build_cohort_retention, run_pipeline, _quintile_score
from retailpulse.provenance import verify_artifact_manifest


def tiny_frame():
    return pd.DataFrame([
        {"Invoice": "100001", "StockCode": "A", "Description": "Mug", "Quantity": 2, "InvoiceDate": "01/01/2011 10:00", "Price": 5.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100001", "StockCode": "B", "Description": "Plate", "Quantity": 1, "InvoiceDate": "01/01/2011 10:00", "Price": 8.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100002", "StockCode": "A", "Description": "Mug", "Quantity": 1, "InvoiceDate": "01/02/2011 11:00", "Price": 5.0, "Customer ID": 11, "Country": "France"},
        {"Invoice": "C100003", "StockCode": "A", "Description": "Mug", "Quantity": -1, "InvoiceDate": "01/03/2011 12:00", "Price": 5.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100004", "StockCode": "C", "Description": "Bad price", "Quantity": 1, "InvoiceDate": "01/03/2011 12:00", "Price": 0.0, "Customer ID": 11, "Country": "France"},
    ])


def test_sales_exclude_cancellations_and_nonpositive_prices():
    prepared, stats = prepare_transactions(tiny_frame())
    result = calculate_analytics(prepared, stats)
    assert round(result["kpis"]["gross_sales_revenue_gbp"], 2) == 23.0
    assert result["kpis"]["sales_orders"] == 2
    assert result["kpis"]["return_or_cancellation_lines"] == 1
    assert result["kpis"]["unique_products"] == 2


def test_rfm_has_valid_scores_and_segments():
    prepared, stats = prepare_transactions(tiny_frame())
    result = calculate_analytics(prepared, stats)
    rfm = result["rfm"]
    assert set(rfm["R"]).issubset({1, 2, 3, 4, 5})
    assert set(rfm["F"]).issubset({1, 2, 3, 4, 5})
    assert set(rfm["M"]).issubset({1, 2, 3, 4, 5})
    assert rfm["customer_id"].nunique() == 2


def test_cohort_month_zero_is_100_percent():
    prepared, stats = prepare_transactions(tiny_frame())
    sales = prepared.loc[prepared["is_sale"]]
    retention = build_cohort_retention(sales)
    assert not retention.empty
    assert (retention["Month_0"].dropna() == 1.0).all()


def test_demo_pipeline_writes_expected_outputs(tmp_path):
    sample = ROOT / "data/sample/sample_retail_transactions.csv"
    result = run_pipeline(sample, tmp_path)
    expected = ["sales_lines.csv", "return_cancellation_lines.csv", "excluded_non_sale_non_return_lines.csv", "monthly_sales.csv", "customer_rfm.csv", "cohort_retention.csv", "kpis.json", "pipeline_manifest.json"]
    assert all((tmp_path / name).exists() for name in expected)
    manifest = json.loads((tmp_path / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["run_id"] == result["pipeline_manifest"]["run_id"]
    assert manifest["source"]["file_name"] == sample.name
    assert len(manifest["source"]["sha256"]) == 64
    assert manifest["schema_version"] == 2
    assert "sales_lines.csv" in manifest["artifacts"]
    assert "kpis.json" in manifest["artifacts"]
    integrity_valid, integrity_message = verify_artifact_manifest(tmp_path, manifest["artifacts"])
    assert integrity_valid, integrity_message
    assert result["kpis"]["sales_orders"] > 0
    saved_cohorts = pd.read_csv(tmp_path / "cohort_retention.csv")
    assert saved_cohorts.columns[0] == "cohort_month"


def test_average_revenue_per_identified_customer_excludes_unknown_ids():
    frame = tiny_frame()
    extra = pd.DataFrame([{
        "Invoice": "100005", "StockCode": "A", "Description": "Mug", "Quantity": 10,
        "InvoiceDate": "01/04/2011 12:00", "Price": 5.0, "Customer ID": None, "Country": "United Kingdom"
    }])
    prepared, stats = prepare_transactions(pd.concat([frame, extra], ignore_index=True))
    result = calculate_analytics(prepared, stats)
    rfm_revenue = result["rfm"]["monetary"].sum()
    assert result["kpis"]["identified_customer_sales_revenue_gbp"] == round(rfm_revenue, 2)
    assert result["kpis"]["average_revenue_per_identified_customer_gbp"] == round(rfm_revenue / 2, 2)


def test_transaction_classification_reconciles_all_valid_rows():
    prepared, stats = prepare_transactions(tiny_frame())
    result = calculate_analytics(prepared, stats)
    assert stats["rows_after_core_validation"] == (
        stats["sale_line_rows"]
        + stats["return_or_cancellation_rows"]
        + stats["rows_neither_sale_nor_return_cancellation"]
    )
    assert len(result["non_sales_non_returns"]) == stats["rows_neither_sale_nor_return_cancellation"]
    assert stats["rows_neither_sale_nor_return_cancellation"] == 1


def test_equal_rfm_values_receive_equal_scores():
    values = pd.Series([10, 10, 20, 30, 30, 30])
    scores = _quintile_score(values, high_is_good=True)
    assert scores.iloc[0] == scores.iloc[1]
    assert scores.iloc[3] == scores.iloc[4] == scores.iloc[5]


def test_cohort_future_months_are_not_zero():
    frame = pd.DataFrame([
        {"Invoice": "100001", "StockCode": "A", "Description": "Mug", "Quantity": 1, "InvoiceDate": "01/03/2011 10:00", "Price": 5.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100002", "StockCode": "A", "Description": "Mug", "Quantity": 1, "InvoiceDate": "01/04/2011 10:00", "Price": 5.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100003", "StockCode": "B", "Description": "Plate", "Quantity": 1, "InvoiceDate": "02/04/2011 10:00", "Price": 8.0, "Customer ID": 11, "Country": "France"},
    ])
    prepared, stats = prepare_transactions(frame)
    sales = prepared.loc[prepared["is_sale"]]
    retention = build_cohort_retention(sales)
    assert retention.loc["2011-03", "Month_0"] == 1.0
    assert retention.loc["2011-03", "Month_1"] == 1.0
    assert retention.loc["2011-04", "Month_0"] == 1.0
    assert pd.isna(retention.loc["2011-04", "Month_1"])


def test_operational_stock_codes_are_separated_from_merchandise():
    frame = pd.DataFrame([
        {"Invoice": "100001", "StockCode": "A", "Description": "Mug", "Quantity": 2, "InvoiceDate": "01/01/2011 10:00", "Price": 5.0, "Customer ID": 10, "Country": "United Kingdom"},
        {"Invoice": "100002", "StockCode": "POST", "Description": "POSTAGE", "Quantity": 1, "InvoiceDate": "01/02/2011 11:00", "Price": 3.0, "Customer ID": 10, "Country": "United Kingdom"},
    ])
    prepared, stats = prepare_transactions(frame)
    result = calculate_analytics(prepared, stats)
    assert result["merchandise_products"]["stock_code"].tolist() == ["A"]
    assert result["non_merchandise_products"]["stock_code"].tolist() == ["POST"]
    assert result["kpis"]["operational_non_merchandise_revenue_gbp"] == 3.0
