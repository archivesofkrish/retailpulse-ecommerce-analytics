#!/usr/bin/env python3
"""Verify core and Phase 3 output checksums and cross-manifest lineage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.provenance import read_json_object, verify_artifact_manifest  # noqa: E402


def verify_outputs(processed_dir: str | Path, phase3_dir: str | Path) -> dict[str, Any]:
    """Return a machine-readable verification report without modifying outputs."""
    processed = Path(processed_dir)
    phase3 = Path(phase3_dir)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, details: str) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "details": details})

    pipeline_path = processed / "pipeline_manifest.json"
    phase3_path = phase3 / "phase3_manifest.json"
    pipeline_manifest: dict[str, Any] | None = None
    phase3_manifest: dict[str, Any] | None = None

    try:
        pipeline_manifest = read_json_object(pipeline_path)
        add("core_manifest", pipeline_manifest.get("status") == "complete",
            f"Core pipeline status: {pipeline_manifest.get('status', 'missing')}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add("core_manifest", False, f"Cannot read core pipeline manifest: {exc}")

    try:
        phase3_manifest = read_json_object(phase3_path)
        add("phase3_manifest", phase3_manifest.get("status") == "complete",
            f"Phase 3 status: {phase3_manifest.get('status', 'missing')}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add("phase3_manifest", False, f"Cannot read Phase 3 manifest: {exc}")

    if pipeline_manifest is not None:
        valid, message = verify_artifact_manifest(
            processed, pipeline_manifest.get("artifacts")
        )
        add("core_artifact_checksums", valid, message)

    if phase3_manifest is not None:
        valid, message = verify_artifact_manifest(
            phase3, phase3_manifest.get("artifacts")
        )
        add("phase3_artifact_checksums", valid, message)

    if pipeline_manifest is not None and phase3_manifest is not None:
        same_run = (
            bool(pipeline_manifest.get("run_id"))
            and phase3_manifest.get("pipeline_run_id") == pipeline_manifest.get("run_id")
        )
        add(
            "pipeline_run_link",
            same_run,
            "Phase 3 references the current core run."
            if same_run else "Phase 3 and core manifests refer to different pipeline runs.",
        )
        source_sha = pipeline_manifest.get("source", {}).get("sha256")
        same_source = bool(source_sha) and phase3_manifest.get("source_sha256") == source_sha
        add(
            "source_fingerprint_link",
            same_source,
            "Core and Phase 3 manifests reference the same source SHA-256."
            if same_source else "Core and Phase 3 source fingerprints do not match.",
        )

    passed = sum(item["status"] == "PASS" for item in checks)
    failed = len(checks) - passed
    return {
        "status": "PASS" if failed == 0 else "FAIL",
        "checks_passed": passed,
        "checks_failed": failed,
        "processed_directory": str(processed),
        "phase3_directory": str(phase3),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify RetailPulse core and Phase 3 artifact manifests."
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=ROOT / "data" / "processed",
        help="Directory containing core CSV exports and pipeline_manifest.json.",
    )
    parser.add_argument(
        "--phase3-dir",
        type=Path,
        default=ROOT / "reports" / "phase3",
        help="Directory containing Phase 3 outputs and phase3_manifest.json.",
    )
    args = parser.parse_args()
    report = verify_outputs(args.processed_dir, args.phase3_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
