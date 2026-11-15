#!/usr/bin/env python3
"""Execute the project's DuckDB query examples and print result tables."""
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.provenance import read_json_object
SQL_FILE = ROOT / "sql/analysis.sql"


def main() -> None:
    manifest_path = ROOT / "data/processed/pipeline_manifest.json"
    if not manifest_path.exists() or not (ROOT / "data/processed/sales_lines.csv").exists():
        raise SystemExit("Run `python scripts/run_analysis.py` before running SQL queries.")
    manifest = read_json_object(manifest_path)
    if manifest.get("status") != "complete":
        raise SystemExit("Core pipeline outputs are incomplete. Re-run `python scripts/run_analysis.py`.")
    connection = duckdb.connect(database=":memory:")
    statements = [part.strip() for part in SQL_FILE.read_text(encoding="utf-8").split(";") if part.strip()]
    for index, statement in enumerate(statements, start=1):
        cursor = connection.execute(statement)
        if cursor.description:
            print(f"\n--- Query {index} ---")
            print(cursor.fetchdf().to_string(index=False))
    connection.close()


if __name__ == "__main__":
    main()
