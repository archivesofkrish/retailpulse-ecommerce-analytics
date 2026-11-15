from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.provenance import build_artifact_manifest
from scripts.verify_outputs import verify_outputs


def _write_valid_run(root: Path) -> tuple[Path, Path]:
    processed = root / "data" / "processed"
    phase3 = root / "reports" / "phase3"
    processed.mkdir(parents=True)
    phase3.mkdir(parents=True)

    (processed / "sales_lines.csv").write_text(
        "invoice,revenue\n100001,12.5\n", encoding="utf-8"
    )
    (processed / "kpis.json").write_text(
        json.dumps({"gross_sales_revenue_gbp": 12.5}), encoding="utf-8"
    )
    (phase3 / "summary.json").write_text(
        json.dumps({"pipeline_run_id": "run-001"}), encoding="utf-8"
    )
    (phase3 / "report.md").write_text("# Test report\n", encoding="utf-8")

    pipeline = {
        "schema_version": 2,
        "status": "complete",
        "run_id": "run-001",
        "source": {"sha256": "a" * 64},
        "artifacts": build_artifact_manifest(processed),
    }
    advanced = {
        "schema_version": 2,
        "status": "complete",
        "pipeline_run_id": "run-001",
        "source_sha256": "a" * 64,
        "artifacts": build_artifact_manifest(phase3),
    }
    (processed / "pipeline_manifest.json").write_text(
        json.dumps(pipeline), encoding="utf-8"
    )
    (phase3 / "phase3_manifest.json").write_text(
        json.dumps(advanced), encoding="utf-8"
    )
    return processed, phase3


def test_verify_outputs_passes_for_consistent_manifests(tmp_path):
    processed, phase3 = _write_valid_run(tmp_path)

    report = verify_outputs(processed, phase3)

    assert report["status"] == "PASS"
    assert report["checks_failed"] == 0
    assert report["checks_passed"] == 6


def test_verify_outputs_fails_when_an_export_is_modified(tmp_path):
    processed, phase3 = _write_valid_run(tmp_path)
    export = processed / "sales_lines.csv"
    export.write_text(
        export.read_text(encoding="utf-8").replace("12.5", "99.9"),
        encoding="utf-8",
    )

    report = verify_outputs(processed, phase3)

    assert report["status"] == "FAIL"
    assert any(
        check["check"] == "core_artifact_checksums" and check["status"] == "FAIL"
        for check in report["checks"]
    )


def test_verify_outputs_fails_when_phase3_references_another_source(tmp_path):
    processed, phase3 = _write_valid_run(tmp_path)
    manifest_path = phase3 / "phase3_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_sha256"] = "b" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = verify_outputs(processed, phase3)

    assert report["status"] == "FAIL"
    assert any(
        check["check"] == "source_fingerprint_link" and check["status"] == "FAIL"
        for check in report["checks"]
    )


def test_verify_outputs_fails_for_missing_phase3_manifest(tmp_path):
    processed, phase3 = _write_valid_run(tmp_path)
    (phase3 / "phase3_manifest.json").unlink()

    report = verify_outputs(processed, phase3)

    assert report["status"] == "FAIL"
    assert any(
        check["check"] == "phase3_manifest" and check["status"] == "FAIL"
        for check in report["checks"]
    )
