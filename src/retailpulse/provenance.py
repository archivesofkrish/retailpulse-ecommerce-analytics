"""Source and derived-output lineage helpers for RetailPulse."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


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


def artifact_fingerprint(path: str | Path) -> dict[str, Any]:
    """Return a portable size + SHA-256 fingerprint for a generated artifact.

    Modification times and absolute paths are deliberately omitted: generated
    outputs must remain verifiable after being copied or mounted elsewhere.
    """
    target = Path(path)
    before = target.stat()
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = target.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Artifact changed while its fingerprint was being calculated: {target}")
    return {"size_bytes": int(after.st_size), "sha256": digest.hexdigest()}


def build_artifact_manifest(
    directory: str | Path,
    *,
    exclude: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    """Fingerprint all regular files below a directory using relative POSIX paths."""
    root = Path(directory).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Artifact directory does not exist: {root}")
    excluded = set(exclude)
    artifacts: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded or path.name.endswith(".tmp"):
            continue
        artifacts[relative] = artifact_fingerprint(path)
    return artifacts


def verify_artifact_manifest(
    directory: str | Path,
    artifacts: dict[str, dict[str, Any]] | None,
) -> tuple[bool, str]:
    """Verify every declared artifact and reject missing, edited or unsafe paths."""
    if not isinstance(artifacts, dict) or not artifacts:
        return False, "The output artifact manifest is missing or empty. Rebuild the analytics."

    root = Path(directory).resolve()
    problems: list[str] = []
    for name, expected in sorted(artifacts.items()):
        if not isinstance(name, str) or not isinstance(expected, dict):
            problems.append("invalid manifest entry")
            continue

        relative = PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts or "\\" in name:
            problems.append(f"unsafe artifact path: {name!r}")
            continue

        candidate = root.joinpath(*relative.parts)
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
            if candidate.is_symlink() or not resolved.is_file():
                problems.append(f"missing or non-regular artifact: {name}")
                continue
            actual = artifact_fingerprint(resolved)
        except (OSError, RuntimeError, ValueError):
            problems.append(f"unavailable artifact: {name}")
            continue

        if (
            expected.get("size_bytes") != actual["size_bytes"]
            or expected.get("sha256") != actual["sha256"]
        ):
            problems.append(f"checksum mismatch: {name}")

    if problems:
        preview = "; ".join(problems[:5])
        remaining = len(problems) - 5
        suffix = f"; and {remaining} more" if remaining > 0 else ""
        return False, f"Output artifact integrity check failed: {preview}{suffix}."

    return True, f"Verified {len(artifacts)} output artifacts against their SHA-256 manifest."


def build_pipeline_manifest(
    source_path: str | Path,
    stats: dict[str, Any],
    kpis: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Create a manifest identifying the exact input and core-pipeline run."""
    return {
        "schema_version": 2,
        "status": "building",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": file_fingerprint(source_path),
        "artifacts": {},
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
