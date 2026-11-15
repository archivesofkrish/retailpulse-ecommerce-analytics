#!/usr/bin/env python3
"""Execute the project's DuckDB query examples and print result tables."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "sql/analysis.sql"


def main() -> None:
    if not (ROOT / "data/processed/sales_lines.csv").exists():
        raise SystemExit("Run `python scripts/run_analysis.py` before running SQL queries.")
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
