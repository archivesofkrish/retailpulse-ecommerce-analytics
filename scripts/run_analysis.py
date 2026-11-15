#!/usr/bin/env python3
"""Run RetailPulse analytics and generate a concise executive report."""
from pathlib import Path
import argparse
import json
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.analysis import run_pipeline


def make_charts(result: dict, figures_dir: Path) -> None:
    """Render static charts used by the generated executive report."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    monthly = result["monthly"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(monthly["order_month"], monthly["revenue"], marker="o", linewidth=2)
    ax.set_title("Monthly gross sales revenue")
    ax.set_xlabel("Invoice month")
    ax.set_ylabel("Revenue (£)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "monthly_revenue.png", dpi=160)
    plt.close(fig)

    products = result["merchandise_products"].head(10).sort_values("revenue")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.barh(products["description"], products["revenue"])
    ax.set_title("Top 10 products by gross revenue")
    ax.set_xlabel("Revenue (£)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "top_products.png", dpi=160)
    plt.close(fig)

    segments = result["segment_summary"].sort_values("customers")
    if not segments.empty:
        fig, ax = plt.subplots(figsize=(9, 5.2))
        ax.barh(segments["rfm_segment"], segments["customers"])
        ax.set_title("Customers by RFM segment")
        ax.set_xlabel("Customers")
        ax.grid(axis="x", alpha=0.25)
        fig.tight_layout()
        fig.savefig(figures_dir / "rfm_segments.png", dpi=160)
        plt.close(fig)

    retention = result["cohort_retention"]
    if not retention.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        values = np.ma.masked_invalid(retention.apply(pd.to_numeric, errors="coerce").to_numpy())
        im = ax.imshow(values, aspect="auto", vmin=0, vmax=1)
        ax.set_title("Cohort customer retention")
        ax.set_xlabel("Months since first purchase")
        ax.set_ylabel("First purchase cohort")
        ax.set_xticks(range(len(retention.columns)), labels=retention.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(retention.index)), labels=retention.index)
        fig.colorbar(im, ax=ax, label="Retention rate")
        fig.tight_layout()
        fig.savefig(figures_dir / "cohort_retention.png", dpi=160)
        plt.close(fig)


def make_report(result: dict, input_path: Path, report_path: Path) -> None:
    k = result["kpis"]
    products = result["merchandise_products"].head(10)
    countries = result["countries"].head(10)
    segments = result["segment_summary"].sort_values("customers", ascending=False).copy()
    operational = result["non_merchandise_products"].sort_values("revenue", ascending=False)
    if not segments.empty:
        segments["customer_share_pct"] = segments["customers"] / segments["customers"].sum() * 100
        segments["revenue_share_pct"] = segments["monetary"] / segments["monetary"].sum() * 100
    top10_merch_share = (products["revenue"].sum() / result["merchandise_products"]["revenue"].sum() * 100) if not result["merchandise_products"].empty else 0
    is_demo = "sample" in input_path.as_posix().lower()
    title = "RetailPulse — Demonstration Analysis" if is_demo else "RetailPulse — Business Performance Report"
    lines = [
        f"# {title}", "",
        ("> **DEMONSTRATION DATA:** this report is generated from the included synthetic sample, not the UCI retailer records."
         if is_demo else "> **SOURCE DATA:** UCI Online Retail II. Results describe this historical dataset, not a current retailer."),
        "", "## Executive summary", "",
        f"- **Gross sales revenue:** £{k['gross_sales_revenue_gbp']:,.2f}",
        f"- **Orders:** {k['sales_orders']:,}",
        f"- **Identified customers:** {k['identified_customers']:,}",
        f"- **Average order value:** £{k['average_order_value_gbp']:,.2f}",
        f"- **Distinct products:** {k['unique_products']:,}",
        f"- **Countries represented:** {k['countries']:,}",
        f"- **Recorded returns/cancellations (absolute line value):** £{k['recorded_return_cancellation_value_gbp']:,.2f}",
        f"- **Sales date range:** {k['sales_date_min']} to {k['sales_date_max']}",
        f"- **Merchandise revenue:** £{k['merchandise_revenue_gbp']:,.2f}",
        f"- **Operational / non-merchandise revenue:** £{k['operational_non_merchandise_revenue_gbp']:,.2f} ({k['operational_non_merchandise_revenue_share_pct']:.2f}% of gross sales)",
        "", "## Visual overview", "", "![Monthly gross sales revenue](figures/monthly_revenue.png)", "", "![Top products](figures/top_products.png)", "", "![Customer RFM segments](figures/rfm_segments.png)", "", "![Cohort retention](figures/cohort_retention.png)", "", "## Top products by gross sales", "", "| Stock code | Product | Revenue | Units | Orders |", "|---|---|---:|---:|---:|",
    ]
    for _, row in products.iterrows():
        lines.append(f"| {row.stock_code} | {str(row.description).replace('|', '/')} | £{row.revenue:,.2f} | {row.units:,.0f} | {int(row.orders):,} |")
    lines += ["", "## Operational / non-merchandise codes (excluded from product ranking)", "",
              f"These {k['operational_non_merchandise_stock_codes']} source stock codes represent fees, postage, adjustments, samples, or other operational lines. Their combined recorded value is £{k['operational_non_merchandise_revenue_gbp']:,.2f} ({k['operational_non_merchandise_revenue_share_pct']:.2f}% of gross sales). This is a classification for product analysis, not an accounting reclassification.", "",
              "| Stock code | Description | Revenue | Units | Orders |", "|---|---|---:|---:|---:|"]
    for _, row in operational.iterrows():
        lines.append(f"| {row.stock_code} | {str(row.description).replace('|', '/')} | £{row.revenue:,.2f} | {row.units:,.0f} | {int(row.orders):,} |")
    lines += ["", "## Top countries by gross sales", "", "| Country | Revenue | Orders | Identified customers |", "|---|---:|---:|---:|"]
    for _, row in countries.iterrows():
        lines.append(f"| {row.country} | £{row.revenue:,.2f} | {int(row.orders):,} | {int(row.customers):,} |")
    lines += [
        "", "## Data quality and customer identification", "",
        "| Measure | Result |", "|---|---:|",
        f"| Source rows received | {k['rows_received']:,} |",
        f"| Invalid core rows dropped | {k['rows_dropped_invalid_core_fields']:,} |",
        f"| Positive sales lines | {k['sale_line_rows']:,} |",
        f"| Return/cancellation lines | {k['return_or_cancellation_lines']:,} |",
        f"| Other valid non-sales/non-return lines | {k['rows_neither_sale_nor_return_cancellation']:,} |",
        f"| Rows missing customer ID | {k['rows_missing_customer_id']:,} |",
        f"| Sales revenue linked to identified customers | £{k['identified_customer_sales_revenue_gbp']:,.2f} ({k['identified_customer_revenue_share_pct']:.2f}%) |",
        f"| Sales revenue without customer ID | £{k['unidentified_customer_sales_revenue_gbp']:,.2f} ({k['unidentified_customer_revenue_share_pct']:.2f}%) |",
        "",
        "Rows without a customer ID remain included in sales-level revenue, but cannot be attributed to an identified customer. Other valid rows are retained separately rather than silently counted as sales.",
    ]
    lines += ["", "## Customer segments", "", "| Segment | Customers | Customer share | Segment revenue | Revenue share | Avg recency (days) | Avg orders/customer |", "|---|---:|---:|---:|---:|---:|---:|"]
    for _, row in segments.iterrows():
        lines.append(f"| {row.rfm_segment} | {int(row.customers):,} | {row.customer_share_pct:.2f}% | £{row.monetary:,.2f} | {row.revenue_share_pct:.2f}% | {row.avg_recency_days:,.1f} | {row.avg_frequency:.2f} |")
    if not segments.empty:
        seg_by_name = segments.set_index("rfm_segment")
        champion = seg_by_name.loc["Champions"] if "Champions" in seg_by_name.index else None
        cannot_lose = seg_by_name.loc["Cannot Lose Them"] if "Cannot Lose Them" in seg_by_name.index else None
        hibernating = seg_by_name.loc["Hibernating"] if "Hibernating" in seg_by_name.index else None
        lines += ["", "## Business observations and recommended actions", ""]
        if champion is not None:
            lines.append(f"- **Revenue concentration in Champions:** {int(champion.customers):,} customers ({champion.customer_share_pct:.2f}% of identified customers) contribute {champion.revenue_share_pct:.2f}% of identified-customer revenue. Protect the experience of this segment and measure retention before/after any loyalty initiative.")
        if cannot_lose is not None:
            lines.append(f"- **Historically valuable but currently inactive customers:** the Cannot Lose Them segment contains {int(cannot_lose.customers):,} customers, averages {cannot_lose.avg_recency_days:.1f} days since last purchase, and contributes {cannot_lose.revenue_share_pct:.2f}% of identified-customer revenue. Test a small, controlled reactivation campaign and compare incremental repeat purchase against a holdout group.")
        if hibernating is not None:
            lines.append(f"- **Large inactive segment:** Hibernating customers are {int(hibernating.customers):,} ({hibernating.customer_share_pct:.2f}% of identified customers) with average recency of {hibernating.avg_recency_days:.1f} days. Prioritise low-cost reactivation and avoid blanket discounts until response is measured.")
        if len(products):
            lines.append(f"- **Merchandise concentration:** the top 10 merchandise stock-code/description rows account for {top10_merch_share:.2f}% of merchandise revenue. Product demand is therefore not dominated by just those top 10 rows in this data extract.")
        anomaly = result["merchandise_products"].loc[result["merchandise_products"]["stock_code"].astype(str).eq("23843")]
        if not anomaly.empty:
            ar = anomaly.iloc[0]
            lines.append(f"- **Product data-quality review:** stock code 23843 ({ar.description}) records {int(ar.units):,} units against {int(ar.orders):,} distinct invoice(s). Inspect the source invoice line before using this as a normal demand or replenishment signal.")
        lines.append("- These are descriptive findings from historical data. RFM labels are rule-based, not churn predictions; campaign effectiveness must be tested rather than assumed.")
    lines += [
        "", "## Methodology and interpretation", "",
        "1. Invalid core records are removed when invoice, SKU, date, quantity, or price is missing; negative prices are excluded.",
        "1a. Valid lines are partitioned into sales, return/cancellations, and other non-sales/non-return lines (including zero-quantity or zero-price rows) so row counts reconcile.",
        "2. Gross sales include positive-quantity, positive-price lines on invoices not marked as cancellations.",
        "3. Negative-quantity lines and invoices prefixed with `C` are reported separately as return/cancellation records. Their value is not silently netted against sales because the source does not establish a complete accounting treatment.",
        "4. Customer metrics use rows with a known customer ID. Sales-level metrics can include valid sales where customer ID is missing.",
        "5. RFM recency is measured from one day after the latest valid sales timestamp. Frequency is distinct invoice count; monetary value is gross sales value. Tied metric values receive the same average-rank percentile score.",
        "6. Cohort month is each customer's first observed purchase month. Retention is the share of that cohort purchasing in each later month. Months beyond the dataset's final observed month are left blank (not zero); zero means an observed month with no repeat purchase.",
        "7. Thirteen source stock codes (including Manual, postage, fees, adjustments, discounts, samples, carriage, and pads) are tagged operational/non-merchandise and excluded from the merchandise ranking. They remain included in gross sales revenue to preserve the source-level KPI definition.",
        "", "## Important limitations", "",
        "- The data is historical and represents one UK-based online retailer; it should not be generalised to all e-commerce businesses.",
        "- Missing customer identifiers mean customer-level analysis covers only identifiable customers.",
        "- The source fields do not provide cost of goods, shipping, marketing spend, or profit. Revenue must not be described as profit.",
        "- Cohort retention measures repeat purchasing in the observed period; newer cohorts have fewer observable months. Blank heatmap cells denote unobserved future months, not zero retention.",
        "- RFM segments are relative to the observed customer distribution and are not externally validated labels.",
        "", "## Reproducibility", "",
        f"- Input file: `{input_path.as_posix()}`",
        "- Machine-readable outputs: `data/processed/`",
        "- Run command: `python scripts/run_analysis.py` (uses the downloaded UCI workbook when present; otherwise the included demo sample).",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None, help="Optional CSV/XLSX input path")
    args = parser.parse_args()
    default_real = ROOT / "data/raw/online_retail_II.xlsx"
    default_sample = ROOT / "data/sample/sample_retail_transactions.csv"
    source = args.input or (default_real if default_real.exists() else default_sample)
    if not source.is_absolute():
        source = (ROOT / source).resolve()
    output_dir = ROOT / "data/processed"
    result = run_pipeline(source, output_dir)
    make_charts(result, ROOT / "reports/figures")
    report_path = ROOT / "reports/EXECUTIVE_REPORT.md"
    make_report(result, source.relative_to(ROOT) if source.is_relative_to(ROOT) else source, report_path)
    print(json.dumps(result["kpis"], indent=2))
    print(f"\nAnalysis outputs: {output_dir}\nExecutive report: {report_path}")
    if "sample" in source.as_posix().lower():
        print("NOTE: sample output is synthetic demonstration data, not UCI dataset findings.")

if __name__ == "__main__":
    main()
