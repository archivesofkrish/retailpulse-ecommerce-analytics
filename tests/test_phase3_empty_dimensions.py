from pathlib import Path
import json
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


def _run_full_phase3(tmp_path, monkeypatch, rows):
    data_dir, output_dir = _configure_phase3(tmp_path, monkeypatch)
    source = tmp_path / "transactions.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    run_pipeline(source, data_dir)
    phase3.main()
    return output_dir


def _row(invoice, stock_code, customer_id, date, price=10.0):
    return {
        "Invoice": invoice,
        "StockCode": stock_code,
        "Description": stock_code,
        "Quantity": 1,
        "InvoiceDate": date,
        "Price": price,
        "Customer ID": customer_id,
        "Country": "United Kingdom",
    }


def test_phase3_completes_when_all_sales_are_anonymous(tmp_path, monkeypatch):
    output_dir = _run_full_phase3(
        tmp_path,
        monkeypatch,
        [
            _row("100001", "A", None, "01/01/2011 10:00"),
            _row("100002", "A", None, "01/02/2011 10:00"),
            _row("100003", "B", None, "01/03/2011 10:00"),
        ],
    )

    summary = json.loads((output_dir / "phase3_summary.json").read_text(encoding="utf-8"))
    phase3_manifest = json.loads((output_dir / "phase3_manifest.json").read_text(encoding="utf-8"))
    assert phase3_manifest["status"] == "complete"
    assert summary["customer_metrics"]["identified_customers"] == 0
    assert summary["customer_metrics"]["customer_revenue_gini"] is None
    assert summary["historical_inactivity_model"]["status"] == "SKIPPED"
    assert "No usable customer IDs" in (
        output_dir / "PHASE3_ADVANCED_ANALYTICS.md"
    ).read_text(encoding="utf-8")

    customer_table = pd.read_csv(output_dir / "customer_revenue_concentration.csv")
    assert customer_table.empty
    cohort_table = pd.read_csv(output_dir / "cohort_retention_recomputed.csv")
    assert cohort_table.empty
    assert cohort_table.columns.tolist() == ["cohort_month"]


def test_phase3_completes_when_all_sales_are_operational_codes(tmp_path, monkeypatch):
    output_dir = _run_full_phase3(
        tmp_path,
        monkeypatch,
        [
            _row("100001", "POST", "100", "01/01/2011 10:00"),
            _row("100002", "POST", "100", "01/02/2011 10:00"),
            _row("100003", "POST", "200", "01/03/2011 10:00"),
        ],
    )

    summary = json.loads((output_dir / "phase3_summary.json").read_text(encoding="utf-8"))
    phase3_manifest = json.loads((output_dir / "phase3_manifest.json").read_text(encoding="utf-8"))
    assert phase3_manifest["status"] == "complete"
    assert summary["product_metrics"]["merchandise_stock_codes"] == 0
    assert summary["product_metrics"]["merchandise_revenue_gbp"] == 0
    assert summary["product_affinity_metrics"]["merchandise_baskets"] == 0
    assert "No merchandise stock codes were classified" in (
        output_dir / "PHASE3_ADVANCED_ANALYTICS.md"
    ).read_text(encoding="utf-8")

    product_table = pd.read_csv(output_dir / "merchandise_product_concentration.csv")
    assert product_table.empty
    assert "max_single_invoice_units" in product_table.columns
    operational_table = pd.read_csv(output_dir / "operational_non_merchandise_codes.csv")
    assert operational_table["stock_code"].tolist() == ["POST"]
