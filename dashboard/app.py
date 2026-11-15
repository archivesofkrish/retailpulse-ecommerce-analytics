"""RetailPulse Professional Edition dashboard.

Run from the project root with: streamlit run dashboard/app.py
The overview responds to sidebar filters. Phase 3 intelligence panels use the
full historical observation window and are explicitly labelled as such.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.analysis import (  # noqa: E402
    NON_MERCHANDISE_STOCK_CODES,
    build_customer_rfm,
    calculate_analytics,
    prepare_transactions,
    read_source,
)
from retailpulse.provenance import file_fingerprint, phase3_freshness, read_json_object

PROCESSED = ROOT / "data" / "processed"
PHASE3 = ROOT / "reports" / "phase3"

st.set_page_config(
    page_title="RetailPulse | Professional Edition",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {background: rgba(128,128,128,.07); padding: 14px 16px; border-radius: 12px;}
      .rp-muted {color: #8a94a6; font-size: .88rem;}
      .rp-kicker {text-transform: uppercase; letter-spacing: .09em; font-size: .72rem; color: #8a94a6; font-weight: 700;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading and preparing transaction data...")
def load_analytics(path: str, modified_ns: int, size_bytes: int):
    raw = read_source(path)
    prepared, stats = prepare_transactions(raw)
    return calculate_analytics(prepared, stats)


@st.cache_data(show_spinner=False)
def read_csv(path: str, modified_ns: int, size_bytes: int) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


@st.cache_data(show_spinner=False)
def read_json(path: str, modified_ns: int, size_bytes: int) -> dict:
    return read_json_object(path)


@st.cache_data(show_spinner=False)
def source_fingerprint(path: str, modified_ns: int, size_bytes: int) -> dict:
    """Cache the source SHA-256 until its path, size or modification time changes."""
    return file_fingerprint(path)


def gbp(value: float, decimals: int = 0) -> str:
    return f"£{value:,.{decimals}f}"


def phase3_csv(name: str) -> pd.DataFrame | None:
    path = PHASE3 / name
    if not path.exists():
        return None
    stat = path.stat()
    return read_csv(str(path), stat.st_mtime_ns, stat.st_size)


def phase3_ready(source_path: Path) -> tuple[bool, str]:
    required = [
        "phase3_manifest.json",
        "phase3_summary.json",
        "customer_segment_value.csv",
        "customer_revenue_concentration.csv",
        "repeat_purchase_windows.csv",
        "merchandise_product_concentration.csv",
        "product_associations.csv",
        "business_insights.csv",
        "country_concentration.csv",
        "historical_inactivity_monthly_backtest.csv",
        "historical_inactivity_feature_importance.csv",
        "cohort_retention_recomputed.csv",
        "weighted_cohort_retention.csv",
    ]
    missing = [name for name in required if not (PHASE3 / name).exists()]
    if missing:
        return False, (
            "Advanced analytics are missing or incomplete. Run scripts/run_analysis.py "
            "and then scripts/run_phase3_analysis.py."
        )
    pipeline_path = PROCESSED / "pipeline_manifest.json"
    if not pipeline_path.exists():
        return False, "Core pipeline provenance is missing. Run scripts/run_analysis.py before Phase 3."
    try:
        pipeline_manifest = read_json_object(pipeline_path)
        phase3_manifest = read_json_object(PHASE3 / "phase3_manifest.json")
        source_stat = source_path.stat()
        fingerprint = source_fingerprint(
            str(source_path), source_stat.st_mtime_ns, source_stat.st_size
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False, "Pipeline provenance files or the source dataset are invalid. Re-run core and Phase 3 analytics."
    return phase3_freshness(
        pipeline_manifest, phase3_manifest, source_path, fingerprint
    )


real_path = ROOT / "data" / "raw" / "online_retail_II.xlsx"
sample_path = ROOT / "data" / "sample" / "sample_retail_transactions.csv"
input_path = real_path if real_path.exists() else sample_path
is_demo = input_path == sample_path

input_stat = input_path.stat()
result = load_analytics(str(input_path), input_stat.st_mtime_ns, input_stat.st_size)
kpis = result["kpis"]
sales = result["sales"].copy()

st.title("RetailPulse")
st.caption("Professional Edition · E-commerce Business Intelligence · Sales, Customers, Retention & Risk")
if is_demo:
    st.warning("DEMO MODE — using the included synthetic sample. Run `python scripts/download_data.py` to retrieve UCI Online Retail II.")
else:
    st.info("HISTORICAL DATA MODE — UCI Online Retail II · 1,067,371 source rows · observation period 1 Dec 2009–9 Dec 2011. This is not a live business feed.")

p3, phase3_message = phase3_ready(input_path)
if not p3:
    st.warning(phase3_message)
    phase3_summary = {}
else:
    summary_path = PHASE3 / "phase3_summary.json"
    summary_stat = summary_path.stat()
    phase3_summary = read_json(str(summary_path), summary_stat.st_mtime_ns, summary_stat.st_size)

with st.sidebar:
    st.header("Overview filters")
    countries_all = sorted(sales["country"].dropna().unique().tolist())
    selected_countries = st.multiselect("Country", countries_all, default=countries_all)
    date_min = sales["invoice_date"].min().date()
    date_max = sales["invoice_date"].max().date()
    date_range = st.date_input("Invoice date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    st.divider()
    st.caption(f"Source: {'Synthetic sample' if is_demo else 'UCI Online Retail II'}")
    st.caption("Currency: GBP (£), as recorded in the source.")
    if p3:
        st.caption("Phase 3 panels use the full source period and are not changed by overview filters.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range
mask = sales["country"].isin(selected_countries) if selected_countries else pd.Series(False, index=sales.index)
mask &= sales["invoice_date"].dt.date.between(start_date, end_date)
filtered = sales.loc[mask].copy()

if filtered.empty:
    st.info("No sales match the current filters. Widen the date range or select more countries.")
    st.stop()

# Phase navigation
labels = ["Overview", "Customer Intelligence", "Retention", "Products & Markets", "Decision Brief", "Inactivity Model", "Data Quality"]
tab_overview, tab_customer, tab_retention, tab_products, tab_decisions, tab_model, tab_quality = st.tabs(labels)

# -----------------------------------------------------------------------------
# OVERVIEW — filter-aware
# -----------------------------------------------------------------------------
with tab_overview:
    revenue = float(filtered["line_value"].sum())
    orders = int(filtered["invoice"].nunique())
    customers = int(filtered["customer_id"].nunique())
    aov = revenue / orders if orders else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross sales revenue", gbp(revenue))
    c2.metric("Orders", f"{orders:,}")
    c3.metric("Identified customers", f"{customers:,}")
    c4.metric("Average order value", gbp(aov, 2))

    monthly = filtered.assign(month=filtered["invoice_date"].dt.to_period("M").astype(str)).groupby("month", as_index=False).agg(
        revenue=("line_value", "sum"), orders=("invoice", "nunique")
    )
    product_all = filtered.groupby(["stock_code", "description"], as_index=False).agg(
        revenue=("line_value", "sum"), units=("quantity", "sum"), orders=("invoice", "nunique")
    )
    product_all["product_type"] = np.where(
        product_all["stock_code"].astype(str).isin(NON_MERCHANDISE_STOCK_CODES),
        "Operational / non-merchandise", "Merchandise",
    )
    products = product_all.loc[product_all["product_type"].eq("Merchandise")].sort_values("revenue", ascending=False)
    operational = product_all.loc[product_all["product_type"].eq("Operational / non-merchandise")].sort_values("revenue", ascending=False)
    countries = filtered.groupby("country", as_index=False).agg(
        revenue=("line_value", "sum"), orders=("invoice", "nunique")
    ).sort_values("revenue", ascending=False)

    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Revenue trend")
        fig = px.line(monthly, x="month", y="revenue", markers=True,
                      labels={"month": "Month", "revenue": "Gross revenue (£)"})
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Revenue by country")
        fig = px.bar(countries.head(12).sort_values("revenue"), x="revenue", y="country", orientation="h",
                     labels={"revenue": "Revenue (£)", "country": "Country"})
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader("Top merchandise products")
        if not products.empty:
            top_products = products.head(10).sort_values("revenue")
            fig = px.bar(top_products, x="revenue", y="description", orientation="h",
                         hover_data=["stock_code", "units", "orders"],
                         labels={"revenue": "Merchandise revenue (£)", "description": "Product"})
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No merchandise products match the current filters.")
    with right:
        st.subheader("Sales by weekday")
        weekday = filtered.assign(weekday=filtered["invoice_date"].dt.day_name()).groupby("weekday", as_index=False).agg(
            orders=("invoice", "nunique"), revenue=("line_value", "sum")
        )
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday["weekday"] = pd.Categorical(weekday["weekday"], categories=weekday_order, ordered=True)
        weekday = weekday.sort_values("weekday")
        fig = px.bar(weekday, x="weekday", y="orders", labels={"weekday": "Day", "orders": "Distinct orders"})
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")

    merch_rev = float(products["revenue"].sum())
    ops_rev = float(operational["revenue"].sum())
    st.caption(f"Merchandise revenue: {gbp(merch_rev, 2)} · Operational/non-merchandise revenue: {gbp(ops_rev, 2)}. Operational codes remain in gross sales but are excluded from merchandise rankings.")
    with st.expander("View operational / non-merchandise codes"):
        st.dataframe(operational.rename(columns={"stock_code": "Stock code", "description": "Description", "revenue": "Revenue (£)", "units": "Units", "orders": "Orders"}), width="stretch", hide_index=True)

    st.subheader("Customer segmentation (current filters)")
    rfm = build_customer_rfm(filtered)
    if not rfm.empty:
        seg = rfm.groupby("rfm_segment", as_index=False).agg(
            customers=("customer_id", "nunique"), monetary=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"), avg_frequency=("frequency", "mean"),
        )
        seg["customer_share_pct"] = seg["customers"] / seg["customers"].sum() * 100
        seg["revenue_share_pct"] = seg["monetary"] / seg["monetary"].sum() * 100
        seg = seg.sort_values("monetary", ascending=False)
        left, right = st.columns([1, 1.35])
        with left:
            fig = px.pie(seg, names="rfm_segment", values="customers", hole=0.48)
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")
        with right:
            display = seg.rename(columns={
                "rfm_segment": "Segment", "customers": "Customers", "monetary": "Historical revenue (£)",
                "avg_recency_days": "Avg recency (days)", "avg_frequency": "Avg orders/customer",
                "customer_share_pct": "Customer share (%)", "revenue_share_pct": "Revenue share (%)",
            })
            # Keep the table compact and readable in portfolio demonstrations.
            display["Customers"] = display["Customers"].map(lambda x: f"{int(x):,}")
            display["Historical revenue (£)"] = display["Historical revenue (£)"].map(lambda x: gbp(float(x), 2))
            for column in ["Avg recency (days)", "Avg orders/customer"]:
                display[column] = display[column].map(lambda x: f"{float(x):,.1f}")
            for column in ["Customer share (%)", "Revenue share (%)"]:
                display[column] = display[column].map(lambda x: f"{float(x):.1f}%")
            st.dataframe(display, width="stretch", hide_index=True)
    else:
        st.info("No customer IDs are available for segmentation under these filters.")

    st.subheader("Cohort retention (full source period)")
    retention = result["cohort_retention"]
    if not retention.empty:
        fig = go.Figure(data=go.Heatmap(
            z=retention.to_numpy(dtype=float), x=list(retention.columns), y=[str(x) for x in retention.index],
            zmin=0, zmax=1, colorscale="Blues", connectgaps=False, hoverongaps=False,
            colorbar={"title": "Monthly activity"},
            hovertemplate="Cohort: %{y}<br>Period: %{x}<br>Active share: %{z:.1%}<extra></extra>",
        ))
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10),
                          xaxis_title="Months since first purchase", yaxis_title="First-purchase cohort")
        st.plotly_chart(fig, width="stretch")
        st.caption("Monthly activity is not cumulative survival. Blank cells are unobserved future months; an observed zero means no cohort member purchased in that month.")

# -----------------------------------------------------------------------------
# CUSTOMER INTELLIGENCE — full historical period
# -----------------------------------------------------------------------------
with tab_customer:
    st.subheader("Customer value and revenue concentration")
    if not p3:
        st.info("Run the Phase 3 analysis to populate customer intelligence.")
    else:
        cm = phase3_summary.get("customer_metrics", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Identified customers", f"{cm.get('identified_customers', 0):,}")
        mean_spend = cm.get("mean_historical_revenue_per_customer_gbp")
        median_spend = cm.get("median_historical_revenue_per_customer_gbp")
        revenue_gini = cm.get("customer_revenue_gini")
        c2.metric("Mean historical spend", gbp(mean_spend, 2) if mean_spend is not None else "N/A")
        c3.metric("Median historical spend", gbp(median_spend, 2) if median_spend is not None else "N/A")
        c4.metric("Revenue Gini", f"{revenue_gini:.3f}" if revenue_gini is not None else "N/A")
        if not cm.get("identified_customers"):
            st.info("Customer-level metrics are unavailable because this dataset contains no usable customer IDs. Sales-level reporting remains available.")
        st.caption("Historical spend is observed revenue over the dataset window, not a forward-looking customer lifetime value estimate.")

        pareto = phase3_csv("customer_revenue_concentration.csv")
        segments = phase3_csv("customer_segment_value.csv")
        top_conc = phase3_csv("top_customer_concentration.csv")
        left, right = st.columns([1.25, 1])
        with left:
            st.markdown("**Customer revenue Pareto curve**")
            if pareto is not None and not pareto.empty:
                fig = px.line(pareto, x="customer_share_cumulative", y="revenue_share_cumulative",
                              labels={"customer_share_cumulative": "Cumulative customer share", "revenue_share_cumulative": "Cumulative identified revenue share"})
                fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dot", color="gray"))
                fig.add_hline(y=0.8, line_dash="dash", line_color="gray")
                fig.update_xaxes(tickformat=".0%", range=[0, 1])
                fig.update_yaxes(tickformat=".0%", range=[0, 1])
                fig.update_layout(height=370, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Customer revenue concentration is unavailable.")
        with right:
            st.markdown("**Revenue contributed by top customer groups**")
            if top_conc is not None and not top_conc.empty:
                fig = px.bar(top_conc, x="top_customer_share_pct", y="identified_revenue_share_pct", text_auto=".1f",
                             labels={"top_customer_share_pct": "Top customer share (%)", "identified_revenue_share_pct": "Identified revenue share (%)"})
                fig.update_layout(height=370, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No identified-customer concentration groups are available.")
        if segments is not None and not segments.empty:
            st.markdown("**RFM segment economics**")
            chart = segments.melt(id_vars="rfm_segment", value_vars=["customer_share_pct", "identified_revenue_share_pct"],
                                  var_name="measure", value_name="share_pct")
            chart["measure"] = chart["measure"].map({"customer_share_pct": "Customer share", "identified_revenue_share_pct": "Revenue share"})
            fig = px.bar(chart, x="rfm_segment", y="share_pct", color="measure", barmode="group",
                         labels={"rfm_segment": "RFM segment", "share_pct": "Share (%)", "measure": "Measure"})
            fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10), xaxis_tickangle=-25)
            st.plotly_chart(fig, width="stretch")
            segment_display = segments[[
                "rfm_segment", "customers", "customer_share_pct", "historical_revenue_gbp",
                "identified_revenue_share_pct", "avg_recency_days", "avg_orders_per_customer",
            ]].rename(columns={
                "rfm_segment": "Segment", "customers": "Customers", "historical_revenue_gbp": "Historical revenue (£)",
                "avg_recency_days": "Avg recency (days)", "avg_orders_per_customer": "Avg orders/customer",
                "customer_share_pct": "Customer share (%)", "identified_revenue_share_pct": "Revenue share (%)",
            })
            segment_display["Customers"] = segment_display["Customers"].map(lambda x: f"{int(x):,}")
            segment_display["Historical revenue (£)"] = segment_display["Historical revenue (£)"].map(lambda x: gbp(float(x), 2))
            for column in ["Avg recency (days)", "Avg orders/customer"]:
                segment_display[column] = segment_display[column].map(lambda x: f"{float(x):,.1f}")
            for column in ["Customer share (%)", "Revenue share (%)"]:
                segment_display[column] = segment_display[column].map(lambda x: f"{float(x):.1f}%")
            st.dataframe(segment_display, width="stretch", hide_index=True)

        alert = phase3_summary.get("customer_metrics", {}).get("top_customer_concentration", [])
        thresholds = cm.get("customer_pareto_thresholds", [])
        if thresholds:
            t80 = next((x for x in thresholds if int(x["revenue_threshold_pct"]) == 80), None)
            if t80:
                st.info(f"Approximately {t80['customer_base_share_pct']:.1f}% of identified customers account for 80% of identified-customer revenue. This is a historical concentration pattern, not a forecast.")

# -----------------------------------------------------------------------------
# RETENTION — repeat purchase + point-in-time cohort activity
# -----------------------------------------------------------------------------
with tab_retention:
    st.subheader("Repeat purchase and cohort activity")
    if not p3:
        st.info("Run the Phase 3 analysis to populate retention analytics.")
    else:
        cm = phase3_summary.get("customer_metrics", {})
        windows = phase3_csv("repeat_purchase_windows.csv")
        c1, c2, c3 = st.columns(3)
        c1.metric("Repeat-customer share", f"{cm.get('repeat_customer_share_pct', 0):.1f}%")
        c2.metric("Customers with 2+ orders", f"{cm.get('repeat_customers', 0):,}")
        median_second_order_days = cm.get("median_days_to_second_order_among_repeaters")
        c3.metric(
            "Median days to second order",
            f"{median_second_order_days:.1f}" if median_second_order_days is not None else "N/A",
        )
        if windows is not None:
            left, right = st.columns([1.25, 1])
            with left:
                fig = px.line(windows, x="follow_up_days", y="second_order_within_window_pct", markers=True,
                              labels={"follow_up_days": "Follow-up window (days)", "second_order_within_window_pct": "Second purchase within window (%)"})
                fig.update_yaxes(range=[0, 100])
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")
            with right:
                st.markdown("**Follow-up eligibility**")
                window_display = windows.rename(columns={
                    "follow_up_days": "Window (days)", "eligible_customers": "Eligible first-time customers",
                    "customers_with_second_order": "Second purchase count",
                    "second_order_within_window_pct": "Second purchase rate (%)",
                }).copy()
                for column in ["Window (days)", "Eligible first-time customers", "Second purchase count"]:
                    window_display[column] = window_display[column].map(lambda x: f"{int(x):,}")
                window_display["Second purchase rate (%)"] = window_display["Second purchase rate (%)"].map(
                    lambda x: f"{float(x):.1f}%" if pd.notna(x) else "N/A"
                )
                st.dataframe(window_display, width="stretch", hide_index=True)
        retention = phase3_csv("cohort_retention_recomputed.csv")
        weighted = phase3_csv("weighted_cohort_retention.csv")
        if retention is not None and not retention.empty:
            cohort_col = retention.columns[0]
            matrix = retention.set_index(cohort_col)
            month_cols = [c for c in matrix.columns if str(c).isdigit()]
            matrix = matrix[month_cols]
            fig = go.Figure(data=go.Heatmap(
                z=matrix.to_numpy(dtype=float), x=[f"Month {c}" for c in month_cols], y=matrix.index.astype(str).tolist(),
                zmin=0, zmax=1, colorscale="Blues", connectgaps=False, hoverongaps=False,
                colorbar={"title": "Monthly active share"},
                hovertemplate="Cohort: %{y}<br>%{x}<br>Active share: %{z:.1%}<extra></extra>",
            ))
            fig.update_layout(height=500, margin=dict(l=10, r=10, t=20, b=10),
                              xaxis_title="Months since first purchase", yaxis_title="Acquisition cohort")
            st.markdown("**Cohort activity heatmap**")
            st.plotly_chart(fig, width="stretch")
            st.caption("Cells show the share of the original cohort active in that exact calendar month. This is not cumulative survival. Blank cells are unobserved future months; zeros mean the month was observed but no cohort member purchased.")
        if weighted is not None and not weighted.empty:
            st.markdown("**Weighted monthly active share across eligible cohorts**")
            fig = px.line(weighted, x="months_since_first_purchase", y="weighted_monthly_active_retention_pct", markers=True,
                          labels={"months_since_first_purchase": "Months since first purchase", "weighted_monthly_active_retention_pct": "Weighted monthly active share (%)"})
            fig.update_yaxes(range=[0, 100])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")

# -----------------------------------------------------------------------------
# PRODUCTS & MARKETS
# -----------------------------------------------------------------------------
with tab_products:
    st.subheader("Merchandise performance and geographic concentration")
    if not p3:
        st.info("Run the Phase 3 analysis to populate merchandise and market analytics.")
    else:
        pm = phase3_summary.get("product_metrics", {})
        country_m = phase3_summary.get("country_metrics", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Merchandise revenue", gbp(pm.get("merchandise_revenue_gbp", 0)))
        c2.metric("Merchandise stock codes", f"{pm.get('merchandise_stock_codes', 0):,}")
        c3.metric("Top-10 product share", f"{pm.get('top_10_merchandise_stock_code_revenue_share_pct', 0):.1f}%")
        c4.metric("Operational revenue", gbp(pm.get("operational_non_merchandise_revenue_gbp", 0)))

        products = phase3_csv("merchandise_product_concentration.csv")
        countries = phase3_csv("country_concentration.csv")
        one_invoice = phase3_csv("single_invoice_merchandise_products.csv")
        left, right = st.columns(2)
        with left:
            st.markdown("**Top merchandise stock codes**")
            if products is not None and not products.empty:
                top = products.head(12).sort_values("revenue_gbp")
                fig = px.bar(top, x="revenue_gbp", y="description", orientation="h", hover_data=["stock_code", "orders", "units"],
                             labels={"revenue_gbp": "Revenue (£)", "description": "Product"})
                fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No merchandise stock codes are available for ranking.")
        with right:
            st.markdown("**Merchandise revenue Pareto curve**")
            if products is not None and not products.empty:
                x_share = np.arange(1, len(products) + 1) / len(products)
                fig = px.line(x=x_share, y=products["cumulative_revenue_share_pct"] / 100,
                              labels={"x": "Cumulative share of stock codes", "y": "Cumulative merchandise revenue"})
                fig.add_hline(y=.8, line_dash="dash", line_color="gray")
                fig.update_xaxes(tickformat=".0%", range=[0, 1])
                fig.update_yaxes(tickformat=".0%", range=[0, 1])
                fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Merchandise concentration is unavailable because there are no merchandise stock codes.")
        st.markdown("**Country revenue concentration**")
        if countries is not None:
            topc = countries.head(12).sort_values("revenue")
            fig = px.bar(topc, x="revenue", y="country", orientation="h", hover_data=["revenue_share_pct", "orders", "customers"],
                         labels={"revenue": "Gross sales revenue (£)", "country": "Country"})
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")
        st.caption(f"United Kingdom revenue share: {country_m.get('top_country_revenue_share_pct', 0):.2f}%. Top five countries: {country_m.get('top_five_country_revenue_share_pct', 0):.2f}%. Revenue alone does not establish market profitability or expansion potential.")
        associations = phase3_csv("product_associations.csv")
        st.markdown("**Products frequently purchased together**")
        affinity = phase3_summary.get("product_affinity_metrics", {})
        if associations is not None and not associations.empty:
            st.caption(
                f"{affinity.get('merchandise_baskets', 0):,} merchandise invoices analysed. "
                f"Rules require at least {affinity.get('minimum_joint_orders', 0):,} joint invoices "
                "and are ranked by lift."
            )
            display_rules = associations.head(15).rename(columns={
                "antecedent_stock_code": "Product code",
                "antecedent_description": "Product",
                "consequent_stock_code": "Often bought with code",
                "consequent_description": "Often bought with",
                "joint_orders": "Joint invoices",
                "support_pct": "Support (%)",
                "confidence_pct": "Confidence (%)",
                "lift": "Lift",
            })
            st.dataframe(
                display_rules[[
                    "Product code", "Product", "Often bought with code", "Often bought with",
                    "Joint invoices", "Support (%)", "Confidence (%)", "Lift",
                ]],
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Support measures how common the pair is across merchandise invoices. "
                "Confidence measures how often the paired product appears when the first product is present. "
                "Lift compares that confidence with the paired product's baseline purchase rate; lift above 1 indicates above-baseline co-purchase. "
                "These are historical associations, not causal effects or profit estimates."
            )
        else:
            st.info("No product pairs met the minimum co-purchase frequency threshold in this dataset.")

        if one_invoice is not None and not one_invoice.empty:
            st.warning("Manual review required: some merchandise stock codes appear on only one invoice. They remain in the revenue totals; do not treat unusual bulk lines as normal demand without source-document review.")
            st.dataframe(one_invoice.head(10).rename(columns={
                "stock_code": "Stock code", "description": "Description", "revenue_gbp": "Revenue (£)",
                "units": "Units", "distinct_invoices": "Distinct invoices", "max_single_invoice_units": "Max units on one invoice",
            }), width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# BUSINESS DECISION BRIEF — transparent, threshold-based recommendations
# -----------------------------------------------------------------------------
with tab_decisions:
    st.subheader("Business decision brief")
    st.caption(
        "Evidence-backed investigation prompts generated from the full historical dataset. "
        "Rules identify patterns to review; they do not establish causality or expected profit."
    )
    if not p3:
        st.info("Run the core pipeline and Phase 3 analytics to generate the business decision brief.")
    else:
        insights = phase3_summary.get("business_insights", [])
        high_count = int(phase3_summary.get("high_priority_business_insight_count", 0))
        medium_count = max(0, len(insights) - high_count)
        c1, c2, c3 = st.columns(3)
        c1.metric("Triggered insights", f"{len(insights):,}")
        c2.metric("High priority", f"{high_count:,}")
        c3.metric("Medium priority", f"{medium_count:,}")
        if not insights:
            st.success("No pre-defined decision rule crossed its threshold in this run. This does not prove that no risk or opportunity exists.")
        for insight in insights:
            with st.expander(f"{insight['priority']} priority · {insight['area']} · {insight['headline']}", expanded=False):
                st.markdown(f"**Evidence**  \n{insight['evidence']}")
                st.markdown(f"**Trigger rule**  \n{insight['trigger_rule']}")
                st.markdown(f"**Recommended next action**  \n{insight['recommended_action']}")
                st.caption(f"Guardrail: {insight['guardrail']}")
        insight_table = phase3_csv("business_insights.csv")
        if insight_table is not None and not insight_table.empty:
            st.download_button(
                "Download decision brief (CSV)",
                data=insight_table.to_csv(index=False).encode("utf-8"),
                file_name="retailpulse_business_insights.csv",
                mime="text/csv",
            )
        st.caption("Thresholds and definitions are documented in docs/BUSINESS_INSIGHTS.md.")


# -----------------------------------------------------------------------------
# HISTORICAL INACTIVITY MODEL — backtest, not live customer scoring
# -----------------------------------------------------------------------------
with tab_model:
    st.subheader("Historical 90-day inactivity model")
    if not p3:
        st.info("Run the Phase 3 analysis to populate the historical model evaluation.")
    else:
        model = phase3_summary.get("historical_inactivity_model", {})
        if model.get("status") != "COMPLETED":
            st.warning(f"Historical model not completed: {model.get('reason', 'See Phase 3 report for details.')}")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Holdout ROC-AUC", f"{model.get('roc_auc', float('nan')):.3f}")
            c2.metric("Average precision", f"{model.get('average_precision', float('nan')):.3f}")
            c3.metric("Brier score", f"{model.get('brier_score', float('nan')):.3f}")
            c4.metric("Top-20% risk lift", f"{model.get('top_20pct_risk_lift', float('nan')):.2f}×")
            st.caption(f"Training snapshots through {model.get('training_snapshot_end', '—')}; held-out snapshots from {model.get('test_snapshot_start', '—')} to {model.get('test_snapshot_end', '—')}. Label horizon: 90 days.")
            monthly = phase3_csv("historical_inactivity_monthly_backtest.csv")
            importance = phase3_csv("historical_inactivity_feature_importance.csv")
            left, right = st.columns(2)
            with left:
                st.markdown("**Monthly held-out ROC-AUC**")
                if monthly is not None:
                    fig = px.line(monthly, x="snapshot_date", y="roc_auc", markers=True,
                                  labels={"snapshot_date": "Snapshot date", "roc_auc": "ROC-AUC"})
                    fig.add_hline(y=.5, line_dash="dash", line_color="gray")
                    fig.update_yaxes(range=[0, 1])
                    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig, width="stretch")
            with right:
                st.markdown("**Model feature importance**")
                if importance is not None:
                    imp = importance.head(10).sort_values("importance")
                    fig = px.bar(imp, x="importance", y="feature", orientation="h",
                                 labels={"importance": "Random Forest importance", "feature": "Feature"})
                    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig, width="stretch")
            st.warning("Interpretation limits: the target is no identified-customer invoice within 90 days, not permanent churn. Customer-month rows repeat customers and are not independent. The dataset ends in 2011; these scores do not estimate current customer risk. Do not use as calibrated probabilities or for financial forecasting.")
            with st.expander("View model definition and caveats"):
                st.write(model.get("target_definition", ""))
                st.write(f"Training observations: {model.get('train_snapshot_customer_observations', 0):,}; test observations: {model.get('test_snapshot_customer_observations', 0):,}.")
                st.write(f"Training inactivity prevalence: {model.get('train_90d_inactivity_prevalence_pct', float('nan')):.1f}%; test prevalence: {model.get('test_90d_inactivity_prevalence_pct', float('nan')):.1f}%.")
                for item in model.get("limitations", []):
                    st.markdown(f"- {item}")

# -----------------------------------------------------------------------------
# DATA QUALITY & REPRODUCIBILITY
# -----------------------------------------------------------------------------
with tab_quality:
    st.subheader("Data quality, definitions and reproducibility")
    quality_keys = [
        "rows_received", "rows_dropped_invalid_core_fields", "rows_after_core_validation",
        "sale_line_rows", "return_or_cancellation_rows", "rows_neither_sale_nor_return_cancellation",
        "rows_missing_customer_id", "rows_missing_customer_id_sales", "operational_non_merchandise_stock_codes",
        "sales_date_min", "sales_date_max",
    ]
    st.json({k: kpis[k] for k in quality_keys if k in kpis})
    validation_path = ROOT / "test-results" / "real_data_validation.json"
    if validation_path.exists():
        validation_stat = validation_path.stat()
        validation = read_json(
            str(validation_path), validation_stat.st_mtime_ns, validation_stat.st_size
        )
        v1, v2, v3 = st.columns(3)
        v1.metric("Real-data checks passed", f"{validation.get('checks_passed', 0)}")
        v2.metric("Checks failed", f"{validation.get('checks_failed', 0)}")
        v3.metric("Checks skipped", f"{validation.get('checks_skipped', 0)}")
        st.dataframe(pd.DataFrame(validation.get("checks", [])), width="stretch", hide_index=True)
    else:
        st.info("Real-data validation JSON not found. Run `python scripts/validate_real_data.py` to generate it.")

    st.markdown("**Core interpretation rules**")
    st.markdown(
        """
        - Gross sales include positive-quantity, positive-price lines on non-cancelled invoices.
        - Returns and cancellations are tracked separately; they are not automatically netted into accounting net sales.
        - Operational/non-merchandise codes remain part of gross recorded revenue but are excluded from merchandise rankings.
        - Customer-level analysis excludes transactions without a customer ID; sales-level totals retain valid anonymous sales.
        - Revenue is not profit. The dataset contains no cost of goods, margin, customer acquisition cost or shipping expense.
        - Cohort cells are point-in-time monthly activity, not cumulative survival; unobserved future months must remain blank.
        """
    )
    st.markdown("**Reproduce the full analysis**")
    st.code("""source .venv/bin/activate
python scripts/run_analysis.py
python scripts/validate_real_data.py
python scripts/run_phase3_analysis.py
python -W error::DeprecationWarning -m pytest -q
streamlit run dashboard/app.py""", language="bash")

# Global project footer / downloads
st.divider()
st.caption("RetailPulse · UCI Online Retail II · Historical observation period 1 Dec 2009 – 9 Dec 2011 · Revenue is not profit · Analyses are descriptive unless explicitly identified as historical model backtests.")
report_path = PHASE3 / "PHASE3_ADVANCED_ANALYTICS.md"
if report_path.exists():
    st.download_button("Download Phase 3 advanced analytics report", report_path.read_bytes(),
                       file_name="RetailPulse_Phase3_Advanced_Analytics.md", mime="text/markdown")
