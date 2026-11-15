from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.analysis import run_pipeline
from retailpulse.provenance import verify_artifact_manifest
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


def test_synthetic_pipeline_runs_through_phase3_with_complete_lineage(tmp_path, monkeypatch):
    data_dir, output_dir = _configure_phase3(tmp_path, monkeypatch)
    sample = ROOT / "data" / "sample" / "sample_retail_transactions.csv"

    core_result = run_pipeline(sample, data_dir)
    phase3.main()

    pipeline_manifest = json.loads(
        (data_dir / "pipeline_manifest.json").read_text(encoding="utf-8")
    )
    phase3_manifest = json.loads(
        (output_dir / "phase3_manifest.json").read_text(encoding="utf-8")
    )
    summary = json.loads(
        (output_dir / "phase3_summary.json").read_text(encoding="utf-8")
    )

    assert pipeline_manifest["status"] == "complete"
    assert phase3_manifest["status"] == "complete"
    assert phase3_manifest["pipeline_run_id"] == pipeline_manifest["run_id"]
    assert phase3_manifest["source_sha256"] == pipeline_manifest["source"]["sha256"]
    assert phase3_manifest["schema_version"] == 2
    assert "phase3_summary.json" in phase3_manifest["artifacts"]
    assert "business_insights.csv" in phase3_manifest["artifacts"]
    core_valid, core_message = verify_artifact_manifest(data_dir, pipeline_manifest["artifacts"])
    phase3_valid, phase3_message = verify_artifact_manifest(output_dir, phase3_manifest["artifacts"])
    assert core_valid, core_message
    assert phase3_valid, phase3_message
    assert summary["pipeline_run_id"] == core_result["pipeline_manifest"]["run_id"]
    assert summary["source_sha256"] == pipeline_manifest["source"]["sha256"]
    assert summary["historical_inactivity_model"]["status"] in {"COMPLETED", "SKIPPED"}
    assert summary["business_insight_count"] == len(summary["business_insights"])
    assert (output_dir / "business_insights.csv").exists()
    customer_metrics = summary["customer_metrics"]
    assert "identified_customer_order_count" in customer_metrics
    if customer_metrics["identified_customer_order_count"]:
        assert customer_metrics["average_identified_customer_order_value_gbp"] > 0
        assert customer_metrics["median_identified_customer_order_value_gbp"] > 0
    else:
        assert customer_metrics["average_identified_customer_order_value_gbp"] is None


    required_outputs = [
        "customer_segment_value.csv",
        "customer_revenue_concentration.csv",
        "repeat_purchase_windows.csv",
        "merchandise_product_concentration.csv",
        "product_associations.csv",
        "business_insights.csv",
        "country_concentration.csv",
        "historical_inactivity_monthly_backtest.csv",
        "historical_inactivity_feature_importance.csv",
        "cohort_retention_recomputed.csv",
        "weighted_cohort_retention.csv",
    ]
    assert all((output_dir / name).exists() for name in required_outputs)


def test_phase3_refuses_core_outputs_marked_as_building(tmp_path, monkeypatch):
    data_dir, _ = _configure_phase3(tmp_path, monkeypatch)
    sample = ROOT / "data" / "sample" / "sample_retail_transactions.csv"
    run_pipeline(sample, data_dir)

    manifest_path = data_dir / "pipeline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "building"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Core pipeline outputs are incomplete"):
        phase3.load_inputs()


def test_phase3_refuses_tampered_core_export(tmp_path, monkeypatch):
    data_dir, _output_dir = _configure_phase3(tmp_path, monkeypatch)
    sample = ROOT / "data" / "sample" / "sample_retail_transactions.csv"
    run_pipeline(sample, data_dir)

    sales_path = data_dir / "sales_lines.csv"
    original = sales_path.read_text(encoding="utf-8")
    sales_path.write_text(original.replace("United Kingdom", "United States"), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Core pipeline export integrity failed"):
        phase3.load_inputs()


def test_phase3_manifest_detects_edited_advanced_output(tmp_path, monkeypatch):
    _data_dir, output_dir = _configure_phase3(tmp_path, monkeypatch)
    sample = ROOT / "data" / "sample" / "sample_retail_transactions.csv"
    run_pipeline(sample, _data_dir)
    phase3.main()

    manifest = json.loads(
        (output_dir / "phase3_manifest.json").read_text(encoding="utf-8")
    )
    report = output_dir / "PHASE3_ADVANCED_ANALYTICS.md"
    report.write_text(report.read_text(encoding="utf-8") + "\\nEdited after generation.", encoding="utf-8")

    valid, message = verify_artifact_manifest(output_dir, manifest["artifacts"])

    assert valid is False
    assert "checksum mismatch" in message.lower()
