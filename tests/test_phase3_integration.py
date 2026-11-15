from pathlib import Path
import json
import sys

import pytest

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
    assert summary["pipeline_run_id"] == core_result["pipeline_manifest"]["run_id"]
    assert summary["source_sha256"] == pipeline_manifest["source"]["sha256"]
    assert summary["historical_inactivity_model"]["status"] in {"COMPLETED", "SKIPPED"}

    required_outputs = [
        "customer_segment_value.csv",
        "customer_revenue_concentration.csv",
        "repeat_purchase_windows.csv",
        "merchandise_product_concentration.csv",
        "product_associations.csv",
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
