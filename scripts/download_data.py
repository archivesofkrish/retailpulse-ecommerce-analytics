#!/usr/bin/env python3
"""Download the UCI Online Retail II workbook into data/raw."""
from pathlib import Path
import hashlib
import json
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx"
DEST = ROOT / "data" / "raw" / "online_retail_II.xlsx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(retrieved_utc: str | None) -> dict:
    """Write provenance without inventing a retrieval time for pre-existing files."""
    manifest = {
        "source_url": URL,
        "retrieved_utc": retrieved_utc,
        "manifest_created_utc": datetime.now(timezone.utc).isoformat(),
        "file": str(DEST.relative_to(ROOT)),
        "bytes": DEST.stat().st_size,
        "sha256": sha256(DEST),
        "dataset_citation": "Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D",
        "license": "CC BY 4.0",
    }
    (DEST.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        if DEST.stat().st_size < 1_000_000:
            raise RuntimeError(f"Existing dataset file is unexpectedly small: {DEST}")
        manifest_path = DEST.parent / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            print(f"Dataset already exists: {DEST}")
            print(f"SHA-256: {sha256(DEST)}")
            return
        manifest = write_manifest(retrieved_utc=None)
        print(f"Dataset already exists: {DEST}")
        print("The original retrieval time is unknown; the manifest records the current file digest.")
        print(f"Created provenance manifest: {DEST.parent / 'manifest.json'}")
        print(f"SHA-256: {manifest['sha256']}")
        return
    request = urllib.request.Request(URL, headers={"User-Agent": "RetailPulse-data-project/1.0"})
    temporary = DEST.with_suffix(".xlsx.part")
    print(f"Downloading UCI Online Retail II from {URL}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if temporary.stat().st_size < 1_000_000:
            raise RuntimeError("Downloaded file is unexpectedly small; refusing to treat it as the dataset.")
        temporary.replace(DEST)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    manifest = write_manifest(retrieved_utc=datetime.now(timezone.utc).isoformat())
    print(f"Saved: {DEST}\nSHA-256: {manifest['sha256']}")

if __name__ == "__main__":
    main()
