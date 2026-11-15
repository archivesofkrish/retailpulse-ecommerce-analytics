#!/usr/bin/env python3
"""Validate end-to-end invariants on the downloaded UCI Online Retail II workbook."""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.analysis import read_source, prepare_transactions, calculate_analytics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/online_retail_II.xlsx",
                        help="UCI workbook or compatible CSV/XLSX (defaults to downloaded UCI workbook)")
    args = parser.parse_args()
    source = args.input if args.input.is_absolute() else (ROOT / args.input).resolve()
    if not source.exists():
        print(f"ERROR: dataset not found: {source}", file=sys.stderr)
        print("Run: python scripts/download_data.py", file=sys.stderr)
        return 2

    raw = read_source(source)
    prepared, stats = prepare_transactions(raw)
    result = calculate_analytics(prepared, stats)
    sales = result["sales"]
    returns = result["returns"]
    other = result["non_sales_non_returns"]
    kpis = result["kpis"]

    checks: list[dict] = []
    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    classified = int(len(sales) + len(returns) + len(other))
    record("all_valid_rows_classified", classified == stats["rows_after_core_validation"],
           f"sales={len(sales):,}; returns/cancellations={len(returns):,}; other={len(other):,}; valid={stats['rows_after_core_validation']:,}")
    sales_invariants = bool((sales["quantity"].gt(0) & sales["unit_price"].gt(0) & ~sales["invoice"].str.startswith("C", na=False)).all())
    record("sales_line_invariants", sales_invariants,
           "Every included sales line has positive quantity and price and is not a C-prefixed invoice.")
    return_invariants = bool((returns["invoice"].str.startswith("C", na=False) | returns["quantity"].lt(0)).all())
    record("return_cancellation_invariants", return_invariants,
           "Every return/cancellation line has a C-prefixed invoice or negative quantity.")
    revenue_from_lines = round(float(sales["line_value"].sum()), 2)
    record("gross_revenue_reconciles", revenue_from_lines == kpis["gross_sales_revenue_gbp"],
           f"sales-line sum=£{revenue_from_lines:,.2f}; KPI=£{kpis['gross_sales_revenue_gbp']:,.2f}")
    customer_revenue = round(kpis["identified_customer_sales_revenue_gbp"] + kpis["unidentified_customer_sales_revenue_gbp"], 2)
    record("customer_revenue_reconciles", customer_revenue == kpis["gross_sales_revenue_gbp"],
           f"identified + unidentified=£{customer_revenue:,.2f}; gross=£{kpis['gross_sales_revenue_gbp']:,.2f}")
    record("rfm_customer_count_reconciles", int(result["rfm"]["customer_id"].nunique()) == kpis["identified_customers"],
           f"RFM customers={result['rfm']['customer_id'].nunique():,}; KPI customers={kpis['identified_customers']:,}")
    cohort = result["cohort_retention"]
    cohort_ok = (not cohort.empty) and bool((cohort["Month_0"].dropna().round(10) == 1.0).all())
    record("cohort_month_zero_is_100_percent", cohort_ok,
           "Every non-empty cohort has 100% retention in its acquisition month.")

    expected_rows = 1_067_371
    if source.name.lower() == "online_retail_ii.xlsx":
        record("uci_source_row_count", len(raw) == expected_rows,
               f"rows={len(raw):,}; expected UCI Online Retail II count={expected_rows:,}.")
    else:
        checks.append({"check": "uci_source_row_count", "status": "SKIP",
                       "detail": "Input filename is not the canonical UCI workbook; source identity check not applied."})

    passed = sum(item["status"] == "PASS" for item in checks)
    failed = sum(item["status"] == "FAIL" for item in checks)
    skipped = sum(item["status"] == "SKIP" for item in checks)
    report = {
        "input_file": str(source),
        "rows_received": len(raw),
        "checks_passed": passed,
        "checks_failed": failed,
        "checks_skipped": skipped,
        "checks": checks,
        "key_kpis": {
            "gross_sales_revenue_gbp": kpis["gross_sales_revenue_gbp"],
            "recorded_return_cancellation_value_gbp": kpis["recorded_return_cancellation_value_gbp"],
            "orders": kpis["sales_orders"],
            "identified_customers": kpis["identified_customers"],
            "identified_customer_revenue_share_pct": kpis["identified_customer_revenue_share_pct"],
            "unidentified_customer_revenue_share_pct": kpis["unidentified_customer_revenue_share_pct"],
            "rows_missing_customer_id": kpis["rows_missing_customer_id"],
            "rows_neither_sale_nor_return_cancellation": kpis["rows_neither_sale_nor_return_cancellation"],
        },
    }
    out = ROOT / "test-results" / "real_data_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nValidation report: {out}")
    return 0 if not any(item["status"] == "FAIL" for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
