from pathlib import Path
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.provenance import build_pipeline_manifest, phase3_freshness, read_json_object, write_json_atomic


def _complete_manifests(source: Path):
    pipeline = build_pipeline_manifest(
        source,
        {"rows_received": 10, "rows_after_core_validation": 9},
        {
            "sales_lines": 7,
            "return_or_cancellation_lines": 1,
            "sales_date_min": "2011-01-01",
            "sales_date_max": "2011-01-31",
            "gross_sales_revenue_gbp": 42.0,
        },
        "test-run-001",
    )
    pipeline["status"] = "complete"
    phase3 = {
        "status": "complete",
        "pipeline_run_id": pipeline["run_id"],
        "source_sha256": pipeline["source"]["sha256"],
    }
    return pipeline, phase3


def test_matching_phase3_manifest_is_current(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("invoice,quantity\n10001,1\n", encoding="utf-8")
    pipeline, phase3 = _complete_manifests(source)

    current, reason = phase3_freshness(pipeline, phase3, source)

    assert current is True
    assert "match" in reason.lower()


def test_phase3_from_an_older_pipeline_run_is_rejected(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("invoice,quantity\n10001,1\n", encoding="utf-8")
    pipeline, phase3 = _complete_manifests(source)
    phase3["pipeline_run_id"] = "older-run"

    current, reason = phase3_freshness(pipeline, phase3, source)

    assert current is False
    assert "older" in reason.lower()


def test_changed_source_file_invalidates_previous_phase3_outputs(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("invoice,quantity\n10001,1\n", encoding="utf-8")
    pipeline, phase3 = _complete_manifests(source)
    source.write_text("invoice,quantity\n10001,10\n", encoding="utf-8")

    current, reason = phase3_freshness(pipeline, phase3, source)

    assert current is False
    assert "changed" in reason.lower()


def test_incomplete_core_pipeline_is_rejected(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("invoice,quantity\n10001,1\n", encoding="utf-8")
    pipeline, phase3 = _complete_manifests(source)
    pipeline["status"] = "building"

    current, reason = phase3_freshness(pipeline, phase3, source)

    assert current is False
    assert "incomplete" in reason.lower()


def test_json_manifest_writer_round_trips_atomically(tmp_path):
    path = tmp_path / "nested" / "manifest.json"
    write_json_atomic(path, {"status": "complete", "count": 3})

    assert read_json_object(path) == {"status": "complete", "count": 3}
    assert not path.with_suffix(".json.tmp").exists()



def test_same_source_copy_at_a_different_path_remains_current(tmp_path):
    source = tmp_path / "host" / "online_retail_II.xlsx"
    source.parent.mkdir()
    source.write_bytes(b"stable source workbook bytes")
    pipeline, phase3 = _complete_manifests(source)

    mounted_copy = tmp_path / "container" / "online_retail_II.xlsx"
    mounted_copy.parent.mkdir()
    shutil.copy2(source, mounted_copy)

    current, reason = phase3_freshness(pipeline, phase3, mounted_copy)

    assert current is True
    assert "match" in reason.lower()



def test_content_change_with_same_size_and_timestamp_is_detected(tmp_path):
    source = tmp_path / "online_retail_II.xlsx"
    source.write_bytes(b"12345")
    pipeline, phase3 = _complete_manifests(source)
    original_stat = source.stat()

    source.write_bytes(b"abcde")
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    current, reason = phase3_freshness(pipeline, phase3, source)

    assert current is False
    assert "fingerprint" in reason.lower()
