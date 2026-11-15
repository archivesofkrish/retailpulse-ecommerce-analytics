"""Source and derived-output lineage helpers for RetailPulse."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def file_fingerprint(path: str | Path) -> dict[str, Any]:
    """Return a content digest and filesystem signature for one source file."""
    source = Path(path).resolve()
    before = source.stat()
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Source file changed while its fingerprint was being calculated: {source}")
    return {
        "path": str(source),
        "file_name": source.name,
        "size_bytes": int(after.st_size),
        "modified_ns": int(after.st_mtime_ns),
        "sha256": digest.hexdigest(),
    }


def build_pipeline_manifest(
    source_path: str | Path,
    stats: dict[str, Any],
    kpis: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Create a manifest identifying the exact input and core-pipeline run."""
    return {
        "schema_version": 1,
        "status": "building",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": file_fingerprint(source_path),
        "row_counts": {
            "received": int(stats.get("rows_received", 0)),
            "valid": int(stats.get("rows_after_core_validation", 0)),
            "sales": int(kpis.get("sales_lines", 0)),
            "returns_or_cancellations": int(kpis.get("return_or_cancellation_lines", 0)),
        },
        "reporting_period": {
            "start": kpis.get("sales_date_min"),
            "end": kpis.get("sales_date_max"),
        },
        "gross_sales_revenue_gbp": float(kpis.get("gross_sales_revenue_gbp", 0.0)),
    }


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    """Write JSON through a temporary file, then atomically replace the target."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(destination)


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read a JSON object and reject arrays/scalars with an actionable error."""
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def phase3_freshness(
    pipeline_manifest: dict[str, Any],
    phase3_manifest: dict[str, Any],
    source_path: str | Path,
    current_fingerprint: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Determine whether advanced outputs belong to the current source run."""
    if pipeline_manifest.get("status") != "complete":
        return False, "The core analytics pipeline is incomplete. Run scripts/run_analysis.py again."
    if phase3_manifest.get("status") != "complete":
        return False, "The advanced analytics run is incomplete. Run scripts/run_phase3_analysis.py again."
    run_id = pipeline_manifest.get("run_id")
    if not run_id or phase3_manifest.get("pipeline_run_id") != run_id:
        return False, "Advanced analytics were generated from an older core-pipeline run. Re-run Phase 3."
    source = pipeline_manifest.get("source", {})
    if phase3_manifest.get("source_sha256") != source.get("sha256"):
        return False, "The source fingerprint differs between core and advanced analytics. Re-run Phase 3."
    try:
        current = current_fingerprint or file_fingerprint(source_path)
    except OSError:
        return False, "The source dataset is unavailable. Restore it and rebuild the analytics."
    if source.get("size_bytes") != current.get("size_bytes") or source.get("modified_ns") != current.get("modified_ns"):
        return False, "The source dataset changed after the last core run. Re-run scripts/run_analysis.py and Phase 3."
    if source.get("sha256") != current.get("sha256"):
        return False, "The source content fingerprint does not match the completed pipeline. Re-run the core pipeline and Phase 3."
    return True, "Advanced outputs match the current source dataset and core-pipeline run."
