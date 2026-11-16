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
from retailpulse.provenance import (
    file_fingerprint,
    phase3_freshness,
    read_json_object,
    verify_artifact_manifest,
)
from retailpulse.scenarios import (
    build_repeat_purchase_scenarios,
    build_repeat_purchase_sensitivity,
)
from retailpulse.experiments import (
    evaluate_two_proportion_experiment,
    plan_two_proportion_experiment,
)

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
      :root { --rp-ink:#14213a; --rp-muted:#66758c; --rp-accent:#6558d3; --rp-line:#e4eaf3; }
      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(ellipse at 88% 0%, rgba(122,112,237,.10), transparent 28%),
          radial-gradient(ellipse at 2% 28%, rgba(25,181,164,.07), transparent 25%),
          linear-gradient(180deg,#f7f9fd 0%,#f2f5fb 100%);
      }
      [data-testid="stHeader"] { background:transparent; }
      .block-container { max-width:1540px; padding-top:1.65rem; padding-bottom:3rem; }
      [data-testid="stSidebar"] { background:linear-gradient(180deg,#111a30 0%,#202d4a 100%); }
      [data-testid="stSidebar"] * { color:#eaf0fa; }
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#d3dced; }
      [data-testid="stMetric"] {
        background:rgba(255,255,255,.92); border:1px solid var(--rp-line);
        border-radius:17px; padding:17px 19px; box-shadow:0 12px 34px rgba(25,42,77,.055);
      }
      [data-testid="stMetricLabel"] p { color:#66758c; font-size:.78rem; font-weight:650; }
      [data-testid="stMetricValue"] { color:#14213a; font-weight:780; letter-spacing:-.035em; }
      [data-baseweb="tab-list"] {
        gap:7px; padding:7px; border:1px solid #e3e9f2; border-radius:16px;
        background:rgba(255,255,255,.84); box-shadow:0 8px 25px rgba(25,42,77,.04);
      }
      [data-baseweb="tab"] { border-radius:10px; color:#63718a; font-weight:650; }
      [data-baseweb="tab"][aria-selected="true"] {
        background:#202d4a; color:white; box-shadow:0 4px 12px rgba(20,33,58,.18);
      }
      div[data-testid="stPlotlyChart"] {
        background:rgba(255,255,255,.86); border:1px solid #e7ecf4;
        border-radius:16px; padding:8px 8px 2px; box-shadow:0 8px 25px rgba(25,42,77,.035);
      }
      .rp-hero {
        position:relative; overflow:hidden; border-radius:25px; padding:29px 34px 25px;
        margin:0 0 22px; color:#f6f8ff;
        background:linear-gradient(112deg,#111c35 0%,#263963 52%,#5a4ec0 100%);
        box-shadow:0 22px 60px rgba(34,46,92,.19);
        border:1px solid rgba(255,255,255,.17);
      }
      .rp-hero:after {
        content:""; position:absolute; width:360px; height:360px; right:-95px; top:-230px;
        border-radius:50%; border:1px solid rgba(255,255,255,.18);
        box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 62px rgba(255,255,255,.025);
        pointer-events:none;
      }
      .rp-hero-top,.rp-hero-meta { display:flex; flex-wrap:wrap; align-items:center; gap:9px; }
      .rp-hero-badge {
        text-transform:uppercase; letter-spacing:.15em; font-size:.68rem; font-weight:800;
        color:#a8f1e7; background:rgba(60,220,193,.11); border:1px solid rgba(130,245,224,.22);
        border-radius:99px; padding:6px 10px;
      }
      .rp-hero-edition { color:#c1cce1; font-size:.72rem; letter-spacing:.08em; }
      .rp-hero-title { font-size:clamp(2.1rem,4vw,3.4rem); line-height:1.05; font-weight:850; letter-spacing:-.055em; margin:18px 0 8px; }
      .rp-hero-title span { color:#8fe9dc; }
      .rp-hero-sub { color:#d5def0; font-size:1.03rem; max-width:760px; }
      .rp-hero-meta { margin-top:23px; }
      .rp-hero-chip { font-size:.69rem; color:#e2e9f7; border:1px solid #ffffff28; background:#ffffff0c; border-radius:99px; padding:6px 10px; }
      .rp-section-head {
        display:flex; justify-content:space-between; align-items:flex-end; gap:12px;
        margin:3px 0 18px; padding:0 0 13px; border-bottom:1px solid #e1e7f0;
      }
      .rp-section-title { color:#162541; font-size:1.45rem; font-weight:800; letter-spacing:-.035em; }
      .rp-section-sub { color:#718098; font-size:.83rem; margin-top:3px; }
      .rp-section-tag { color:#5d55c7; background:#eeedff; border:1px solid #dcd9ff; padding:6px 10px; border-radius:99px; font-size:.68rem; font-weight:750; white-space:nowrap; }
      .rp-note {
        border:1px solid #dce5f2; background:linear-gradient(110deg,#f0f5ff,#f5f2ff);
        color:#52627b; border-radius:14px; padding:13px 16px; font-size:.82rem;
      }
      .rp-muted { color:#7b879b; font-size:.88rem; }
      .rp-kicker { text-transform:uppercase; letter-spacing:.09em; font-size:.72rem; color:#8a94a6; font-weight:700; }
      .rp-experiment-arm {
        border:1px solid #dce4f1; border-radius:17px; padding:17px 19px;
        background:linear-gradient(145deg,#ffffff,#f4f7ff);
        box-shadow:0 12px 34px rgba(25,42,77,.055); min-height:128px;
      }
      .rp-experiment-arm.variant {
        background:linear-gradient(145deg,#f3fffc,#eaf8f7); border-color:#cbeae5;
      }
      .rp-experiment-arm-label { color:#7b879b; font-size:.69rem; font-weight:800; letter-spacing:.13em; }
      .rp-experiment-arm-n { color:#172642; font-size:2rem; font-weight:850; letter-spacing:-.05em; margin:9px 0 1px; }
      .rp-experiment-arm-caption { color:#77849b; font-size:.76rem; }
      .rp-result-positive { border:1px solid #aee5d0; background:linear-gradient(110deg,#effcf6,#f4fbff); color:#25634d; border-radius:14px; padding:14px 16px; }
      .rp-result-neutral { border:1px solid #e0e6f0; background:linear-gradient(110deg,#f4f7fc,#f8f7ff); color:#52627b; border-radius:14px; padding:14px 16px; }
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
        "customer_cohort_value.csv",
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
    fresh, freshness_message = phase3_freshness(
        pipeline_manifest, phase3_manifest, source_path, fingerprint
    )
    if not fresh:
        return False, freshness_message

    for label, directory, manifest in (
        ("Core pipeline", PROCESSED, pipeline_manifest),
        ("Phase 3", PHASE3, phase3_manifest),
    ):
        verified, integrity_message = verify_artifact_manifest(
            directory, manifest.get("artifacts")
        )
        if not verified:
            return False, (
                f"{label} output integrity check failed. {integrity_message} "
                "Re-run the corresponding analytics pipeline before using these results."
            )

    return True, (
        "Source lineage and all generated-output SHA-256 checksums are valid. "
        + freshness_message
    )


real_path = ROOT / "data" / "raw" / "online_retail_II.xlsx"
sample_path = ROOT / "data" / "sample" / "sample_retail_transactions.csv"
input_path = real_path if real_path.exists() else sample_path
is_demo = input_path == sample_path

input_stat = input_path.stat()
result = load_analytics(str(input_path), input_stat.st_mtime_ns, input_stat.st_size)
kpis = result["kpis"]
sales = result["sales"].copy()

st.markdown(
    """
    <section class="rp-hero">
      <div class="rp-hero-top">
        <span class="rp-hero-badge">Retail Intelligence · Evidence First</span>
        <span class="rp-hero-edition">PROFESSIONAL EDITION · v1.6.0</span>
      </div>
      <div class="rp-hero-title">RetailPulse<span>✦</span></div>
      <div class="rp-hero-sub">See the story behind every order — from revenue performance to customer retention and historical value.</div>
      <div class="rp-hero-meta">
        <span class="rp-hero-chip">PYTHON · PANDAS · PLOTLY</span>
        <span class="rp-hero-chip">COHORT INTELLIGENCE</span>
        <span class="rp-hero-chip">REPRODUCIBLE ANALYTICS</span>
        <span class="rp-hero-chip">HISTORICAL UCI DATA</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
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
labels = ["Overview", "Customer Intelligence", "Customer Value Studio", "Retention", "Products & Markets", "Decision Brief", "Scenario Lab", "Inactivity Model", "Data Quality", "Experiment Studio"]
tab_overview, tab_customer, tab_value, tab_retention, tab_products, tab_decisions, tab_scenarios, tab_model, tab_quality, tab_experiments = st.tabs(labels)

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
# -----------------------------------------------------------------------------
# CUSTOMER VALUE STUDIO — historical cohort economics
# -----------------------------------------------------------------------------
with tab_value:
    st.markdown(
        '<div class="rp-section-head"><div><div class="rp-kicker">CUSTOMER ECONOMICS · COHORT LENS</div>'
        '<div class="rp-section-title">Customer Value Studio</div>'
        '<div class="rp-section-sub">See how observed revenue yield and customer activity evolve after first purchase.</div></div>'
        '<span class="rp-section-tag">HISTORICAL · NOT FORECAST</span></div>',
        unsafe_allow_html=True,
    )
    if not p3:
        st.info("Run the Phase 3 analysis to build the customer cohort value panel.")
    else:
        value_panel = phase3_csv("customer_cohort_value.csv")
        if value_panel is None or value_panel.empty:
            st.info("No identified-customer cohort value data is available for this source.")
        else:
            value_panel = value_panel.copy()
            value_panel["age_month"] = pd.to_numeric(
                value_panel["age_month"], errors="coerce"
            ).fillna(0).astype(int)
            for column in [
                "cohort_customers", "active_customers", "retention_pct",
                "observed_revenue_gbp",
                "revenue_per_acquired_customer_gbp",
                "cumulative_revenue_per_acquired_customer_gbp",
            ]:
                value_panel[column] = pd.to_numeric(
                    value_panel[column], errors="coerce"
                ).fillna(0.0)
            value_panel["is_partial_period"] = (
                value_panel["is_partial_period"].astype(str).str.lower().eq("true")
            )

            cohort_sizes = value_panel.groupby("cohort_month")["cohort_customers"].first()
            matured = value_panel.loc[
                value_panel["age_month"].eq(11)
                & ~value_panel["is_partial_period"]
            ].copy()
            matured_months = set(matured["cohort_month"].astype(str))
            matured_base = float(matured["cohort_customers"].sum())
            twelve_month_value = (
                float(
                    (
                        matured["cumulative_revenue_per_acquired_customer_gbp"]
                        * matured["cohort_customers"]
                    ).sum() / matured_base
                )
                if matured_base else None
            )
            twelve_month_retention = (
                float(matured["active_customers"].sum() / matured_base * 100)
                if matured_base else None
            )

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Acquisition cohorts", f"{len(cohort_sizes):,}")
            k2.metric("Identified customers", f"{int(cohort_sizes.sum()):,}")
            k3.metric("Mature 12-period cohorts", f"{len(matured_months):,}")
            k4.metric(
                "12-month observed revenue / customer",
                gbp(twelve_month_value, 2) if twelve_month_value is not None else "N/A",
                help="Weighted historical gross revenue per original cohort customer across fully observed 12-calendar-month cohorts.",
            )
            if twelve_month_value is None:
                st.info("The source does not yet contain a complete 12-calendar-month observation window for a cohort. Missing months are not extrapolated.")

            comparable = (
                value_panel.loc[
                    value_panel["cohort_month"].astype(str).isin(matured_months)
                ].copy()
                if matured_months else value_panel.copy()
            )
            curve_rows = []
            for age, group in comparable.groupby("age_month", sort=True):
                base = float(group["cohort_customers"].sum())
                if base <= 0:
                    continue
                curve_rows.append({
                    "age_month": int(age),
                    "cohort_customers": int(base),
                    "active_customers": int(group["active_customers"].sum()),
                    "retention_pct": float(group["active_customers"].sum() / base * 100),
                    "monthly_revenue_per_acquired_customer_gbp": float(
                        group["observed_revenue_gbp"].sum() / base
                    ),
                    "cumulative_revenue_per_acquired_customer_gbp": float(
                        (
                            group["cumulative_revenue_per_acquired_customer_gbp"]
                            * group["cohort_customers"]
                        ).sum() / base
                    ),
                })
            curve = pd.DataFrame(curve_rows)

            left, right = st.columns(2)
            with left:
                st.markdown("**Cumulative observed revenue per acquired customer**")
                fig = go.Figure()
                if not curve.empty:
                    fig.add_trace(go.Scatter(
                        x=curve["age_month"],
                        y=curve["cumulative_revenue_per_acquired_customer_gbp"],
                        mode="lines+markers",
                        line=dict(color="#6558d3", width=3, shape="spline"),
                        marker=dict(size=7, color="#6558d3", line=dict(width=2, color="#ffffff")),
                        fill="tozeroy",
                        fillcolor="rgba(101,88,211,.12)",
                        customdata=curve[["cohort_customers"]],
                        hovertemplate="Month %{x}<br>Observed revenue/customer £%{y:,.2f}<br>Comparable cohort customers %{customdata[0]:,.0f}<extra></extra>",
                    ))
                fig.update_layout(
                    height=350, margin=dict(l=10, r=10, t=14, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475467"), xaxis_title="Months since first purchase",
                    yaxis_title="Cumulative gross revenue (£)",
                )
                st.plotly_chart(fig, width="stretch")
            with right:
                st.markdown("**Active customers by cohort age**")
                fig = go.Figure()
                if not curve.empty:
                    fig.add_trace(go.Scatter(
                        x=curve["age_month"], y=curve["retention_pct"],
                        mode="lines+markers",
                        line=dict(color="#0e9f8a", width=3, shape="spline"),
                        marker=dict(size=7, color="#0e9f8a", line=dict(width=2, color="#ffffff")),
                        fill="tozeroy", fillcolor="rgba(14,159,138,.11)",
                        customdata=curve[["active_customers", "cohort_customers"]],
                        hovertemplate="Month %{x}<br>Active share %{y:.1f}%<br>Active %{customdata[0]:,.0f} of %{customdata[1]:,.0f}<extra></extra>",
                    ))
                fig.update_layout(
                    height=350, margin=dict(l=10, r=10, t=14, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475467"), xaxis_title="Months since first purchase",
                    yaxis_title="Customers active in that calendar month (%)",
                    yaxis=dict(range=[0, 100]),
                )
                st.plotly_chart(fig, width="stretch")

            if not matured.empty:
                st.markdown("**12-month observed value by acquisition cohort**")
                maturity_chart = matured.sort_values("cohort_month").copy()
                fig = px.bar(
                    maturity_chart, x="cohort_month",
                    y="cumulative_revenue_per_acquired_customer_gbp",
                    color="retention_pct",
                    color_continuous_scale=["#d8e4ff", "#8277df", "#302a75"],
                    labels={
                        "cohort_month": "First-purchase cohort",
                        "cumulative_revenue_per_acquired_customer_gbp": "Observed gross revenue/customer (£)",
                        "retention_pct": "Month-12 active share (%)",
                    },
                    hover_data={"cohort_customers": True, "active_customers": True},
                )
                fig.update_layout(
                    height=340, margin=dict(l=10, r=10, t=14, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475467"), coloraxis_colorbar=dict(title="Active %"),
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.caption("The cohort-by-cohort 12-month comparison appears once at least one acquisition cohort has 12 complete observed calendar months.")

            st.markdown("**Cohort value matrix · cumulative observed revenue per original customer**")
            matrix = value_panel.pivot(
                index="cohort_month", columns="age_month",
                values="cumulative_revenue_per_acquired_customer_gbp",
            ).sort_index()
            fig = go.Figure(data=go.Heatmap(
                z=matrix.to_numpy(dtype=float),
                x=[int(value) for value in matrix.columns],
                y=[str(value) for value in matrix.index],
                colorscale=[
                    [0.0, "#f1efff"], [0.25, "#c8c3f5"],
                    [0.55, "#8a80df"], [1.0, "#302a75"],
                ],
                colorbar=dict(title="£ / acquired customer"),
                hovertemplate="Cohort %{y}<br>Age %{x} months<br>Cumulative observed revenue/customer £%{z:,.2f}<extra></extra>",
                connectgaps=False,
            ))
            fig.update_layout(
                height=max(360, min(760, 22 * len(matrix.index) + 150)),
                margin=dict(l=10, r=10, t=12, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#475467"),
                xaxis_title="Months since first purchase",
                yaxis_title="First-purchase cohort",
            )
            st.plotly_chart(fig, width="stretch")
            if value_panel["is_partial_period"].any():
                st.caption("The final source calendar month is partial and is excluded from the mature 12-month comparison. Empty heatmap cells are right-censored future periods, not zero revenue.")

            st.download_button(
                "Download cohort value data",
                data=value_panel.to_csv(index=False).encode("utf-8"),
                file_name="retailpulse_customer_cohort_value.csv",
                mime="text/csv",
            )
            with st.expander("Methodology and interpretation"):
                st.markdown(
                    """
                    - **Cohort:** calendar month of each identified customer's first observed invoice.
                    - **Monthly retention:** customers with an invoice in that calendar month divided by the original cohort size.
                    - **Monthly revenue yield:** gross sales revenue in that month divided by the original cohort size.
                    - **Cumulative revenue yield:** cumulative observed gross sales revenue divided by the original cohort size.
                    - **12-period comparison:** only cohorts with all 12 calendar months observed are included; a partial final calendar month is excluded.
                    """
                )
                st.warning(
                    "This is observed historical revenue yield, not projected customer lifetime value (CLV), "
                    "a forecast or profit. It excludes customers without IDs, future months after the source ends, "
                    "gross margin, acquisition costs, campaign spend, fulfilment costs and a returns-adjusted accounting measure."
                )
            if not matured.empty and twelve_month_retention is not None:
                st.caption(
                    f"Comparable matured cohorts: {len(matured_months):,} · "
                    f"weighted month-12 active share: {twelve_month_retention:.1f}% · "
                    f"analysis end: {value_panel['observation_end_date'].max()}."
                )

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
# -----------------------------------------------------------------------------
# COMMERCIAL SCENARIO LAB — assumption-driven repeat-purchase planning
# -----------------------------------------------------------------------------
with tab_scenarios:
    st.subheader("Repeat-purchase scenario lab")
    st.caption(
        "Explore what-if revenue outcomes when more eligible first-time customers "
        "make a second purchase within 90 days. All improvements are user-defined assumptions."
    )
    if not p3:
        st.info("Run the core pipeline and Phase 3 analytics to populate the scenario lab.")
    else:
        customer_metrics = phase3_summary.get("customer_metrics", {})
        repeat90 = next(
            (
                item for item in customer_metrics.get("repeat_purchase_windows", [])
                if int(item.get("follow_up_days", 0)) == 90
            ),
            None,
        )
        eligible = int(repeat90.get("eligible_customers", 0)) if repeat90 else 0
        baseline_rate = repeat90.get("second_order_within_window_pct") if repeat90 else None
        historical_aov = customer_metrics.get("average_identified_customer_order_value_gbp")

        if (
            eligible <= 0
            or baseline_rate is None
            or not np.isfinite(float(baseline_rate))
            or historical_aov is None
            or not np.isfinite(float(historical_aov))
            or float(historical_aov) <= 0
        ):
            st.warning(
                "The 90-day eligible cohort or identified-customer order value is unavailable. "
                "Regenerate the Phase 3 outputs with python scripts/run_phase3_analysis.py "
                "after running the core pipeline. Small synthetic samples may not have a complete 90-day cohort."
            )
        else:
            baseline_rate = float(baseline_rate)
            historical_aov = float(historical_aov)
            available_headroom = max(0.0, 100.0 - baseline_rate)
            maximum_base_uplift = min(20.0, available_headroom)

            c1, c2, c3 = st.columns(3)
            c1.metric("Eligible first-time customers", f"{eligible:,}")
            c2.metric("Observed 90-day second-purchase rate", f"{baseline_rate:.1f}%")
            c3.metric("Historical identified-customer AOV", gbp(historical_aov, 2))

            if maximum_base_uplift <= 0:
                st.info("The observed 90-day repeat-purchase rate is already 100%; there is no mathematical headroom for an uplift scenario.")
            else:
                controls_left, controls_right = st.columns(2)
                with controls_left:
                    base_uplift = st.slider(
                        "Assumed base-case improvement (percentage points)",
                        min_value=0.0,
                        max_value=float(maximum_base_uplift),
                        value=float(min(5.0, maximum_base_uplift)),
                        step=float(min(0.5, maximum_base_uplift)),
                        help="This is an assumption to explore, not a model prediction or measured treatment effect.",
                    )
                with controls_right:
                    aov_adjustment = st.slider(
                        "Assumed average order value change",
                        min_value=-20,
                        max_value=20,
                        value=0,
                        step=1,
                        format="%d%%",
                        help="Applies a user-defined adjustment to the historical identified-customer average order value.",
                    )

                scenario_aov = historical_aov * (1 + float(aov_adjustment) / 100)
                stretch_uplift = min(base_uplift * 1.5, available_headroom)
                uplift_cases = {
                    "Conservative": round(base_uplift * 0.5, 4),
                    "Base": round(base_uplift, 4),
                    "Stretch": round(stretch_uplift, 4),
                }
                scenario_result = build_repeat_purchase_scenarios(
                    eligible_customers=eligible,
                    baseline_repeat_rate_pct=baseline_rate,
                    average_order_value_gbp=scenario_aov,
                    uplift_scenarios_pp=uplift_cases,
                )
                rows = pd.DataFrame(scenario_result["scenarios"])
                base_row = next(row for row in scenario_result["scenarios"] if row["scenario"] == "Base")

                st.markdown("### Base-case illustration")
                m1, m2, m3 = st.columns(3)
                m1.metric(
                    "Expected additional repeat customers",
                    f"{base_row['expected_incremental_repeat_customers']:,.1f}",
                )
                m2.metric(
                    "Expected additional second orders",
                    f"{base_row['expected_incremental_orders']:,.1f}",
                )
                m3.metric(
                    "Illustrative incremental gross revenue",
                    gbp(base_row["expected_incremental_gross_revenue_gbp"], 2),
                )

                left, right = st.columns([1.1, 1])
                with left:
                    st.markdown("**Scenario comparison**")
                    display = rows[[
                        "scenario",
                        "uplift_percentage_points",
                        "target_repeat_rate_pct",
                        "expected_incremental_repeat_customers",
                        "expected_incremental_orders",
                        "expected_incremental_gross_revenue_gbp",
                    ]].rename(columns={
                        "scenario": "Scenario",
                        "uplift_percentage_points": "Assumed uplift (pp)",
                        "target_repeat_rate_pct": "Scenario repeat rate (%)",
                        "expected_incremental_repeat_customers": "Expected extra repeat customers",
                        "expected_incremental_orders": "Expected extra orders",
                        "expected_incremental_gross_revenue_gbp": "Incremental gross revenue (£)",
                    })
                    st.dataframe(
                        display.style.format({
                            "Assumed uplift (pp)": "{:.1f}",
                            "Scenario repeat rate (%)": "{:.1f}%",
                            "Expected extra repeat customers": "{:,.1f}",
                            "Expected extra orders": "{:,.1f}",
                            "Incremental gross revenue (£)": "£{:,.2f}",
                        }),
                        width="stretch",
                        hide_index=True,
                    )
                with right:
                    st.markdown("**Gross revenue by scenario**")
                    chart = rows.rename(columns={
                        "scenario": "Scenario",
                        "expected_incremental_gross_revenue_gbp": "Incremental gross revenue (£)",
                    })
                    fig = px.bar(
                        chart,
                        x="Scenario",
                        y="Incremental gross revenue (£)",
                        text_auto=",.0f",
                        labels={"Scenario": "Assumption set"},
                    )
                    fig.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig, width="stretch")

                sensitivity = pd.DataFrame(build_repeat_purchase_sensitivity(
                    eligible_customers=eligible,
                    baseline_repeat_rate_pct=baseline_rate,
                    average_order_value_gbp=scenario_aov,
                    maximum_uplift_pp=stretch_uplift,
                    points=21,
                ))
                st.markdown("**Sensitivity to repeat-rate improvement**")
                fig = px.line(
                    sensitivity,
                    x="uplift_percentage_points",
                    y="expected_incremental_gross_revenue_gbp",
                    markers=True,
                    labels={
                        "uplift_percentage_points": "Assumed repeat-rate improvement (percentage points)",
                        "expected_incremental_gross_revenue_gbp": "Illustrative incremental gross revenue (£)",
                    },
                )
                fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, width="stretch")

                st.download_button(
                    "Download scenario comparison (CSV)",
                    data=rows.to_csv(index=False).encode("utf-8"),
                    file_name="retailpulse_repeat_purchase_scenarios.csv",
                    mime="text/csv",
                )
                st.warning(
                    "This is not a forecast or causal estimate. The scenario assumes each "
                    "incremental repeat customer places one additional order at the adjusted "
                    "historical identified-customer AOV. Revenue is not profit: margin, campaign "
                    "cost, returns, customer acquisition cost and operational capacity are not modelled."
                )
                with st.expander("View assumptions and methodology"):
                    st.markdown(
                        f"- Eligible base: {eligible:,} first-time identified customers with a complete 90-day observation window.\n"
                        f"- Observed baseline: {baseline_rate:.2f}% second-purchase rate within 90 days.\n"
                        f"- Historical identified-customer AOV: {gbp(historical_aov, 2)}.\n"
                        f"- Scenario AOV after user adjustment: {gbp(scenario_aov, 2)}.\n"
                        "- Each incremental repeat customer contributes one additional second order in the scenario.\n"
                        "- Expected counts are not rounded to whole customers; they are arithmetic expectations."
                    )
                    for limitation in scenario_result["limitations"]:
                        st.markdown(f"- {limitation}")


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

# -----------------------------------------------------------------------------
# EXPERIMENT STUDIO — two-proportion sample-size planning and outcome review
# -----------------------------------------------------------------------------
with tab_experiments:
    st.markdown(
        '<div class="rp-section-head"><div><div class="rp-kicker">CONTROLLED TESTING · STATISTICAL DESIGN</div>'
        '<div class="rp-section-title">Experiment Studio</div>'
        '<div class="rp-section-sub">Design a binary-conversion experiment, understand its sample requirement, then evaluate the observed result.</div></div>'
        '<span class="rp-section-tag">PLANNING · NOT LIVE TRACKING</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rp-note">A practical experiment-design workbench: choose a baseline and the smallest uplift worth detecting, '
        'estimate the sample needed in each arm, and enter completed test counts for a transparent readout.</div>',
        unsafe_allow_html=True,
    )

    historical_baseline = None
    if p3:
        customer_metrics = phase3_summary.get("customer_metrics", {})
        repeat90_reference = next(
            (
                item for item in customer_metrics.get("repeat_purchase_windows", [])
                if int(item.get("follow_up_days", 0)) == 90
            ),
            None,
        )
        candidate = (
            repeat90_reference.get("second_order_within_window_pct")
            if repeat90_reference else None
        )
        if candidate is not None and np.isfinite(float(candidate)) and 0 <= float(candidate) < 99.9:
            historical_baseline = float(candidate)

    baseline_options = ["Manual planning assumption"]
    if historical_baseline is not None:
        baseline_options.insert(0, "Historical 90-day repeat-purchase reference")
    selected_baseline_source = st.radio(
        "Baseline conversion rate",
        baseline_options,
        horizontal=True,
        help="The historical rate is only a reference from the 2009–2011 UCI dataset. It is not a current business baseline.",
    )
    if historical_baseline is not None and selected_baseline_source.startswith("Historical"):
        baseline_rate = historical_baseline
        st.info(
            f"Reference baseline: {baseline_rate:.2f}% second purchase within 90 days, "
            "measured in the historical UCI observation window. Use a current measured baseline for a real experiment."
        )
    else:
        baseline_rate = st.number_input(
            "Assumed or externally measured control conversion rate (%)",
            min_value=0.0, max_value=99.9, value=10.0, step=0.5,
            key="experiment_baseline_rate",
            help="Enter a recent, relevant control rate. The synthetic sample and historical workbook are not sources of current traffic or conversion.",
        )

    headroom = max(0.1, 100.0 - float(baseline_rate))
    controls_left, controls_mid, controls_right = st.columns(3)
    with controls_left:
        mde = st.number_input(
            "Minimum detectable effect (percentage points)",
            min_value=0.1, max_value=float(headroom),
            value=float(min(2.0, headroom)), step=0.1,
            key="experiment_mde",
            help="The smallest absolute conversion-rate increase that would be meaningful to detect.",
        )
    with controls_mid:
        alpha_label = st.selectbox(
            "Significance level (two-sided)",
            options=["0.10", "0.05", "0.01"],
            index=1,
            key="experiment_alpha",
        )
        significance_level = float(alpha_label)
    with controls_right:
        power_label = st.selectbox(
            "Target statistical power",
            options=["80%", "90%", "95%"],
            index=0,
            key="experiment_power",
        )
        target_power = float(power_label.rstrip("%")) / 100

    eligible_per_day = st.number_input(
        "Eligible participants available per calendar day (both arms combined)",
        min_value=1, max_value=1_000_000, value=100, step=10,
        key="experiment_eligible_per_day",
        help="This is your own current operational estimate. RetailPulse does not infer daily traffic from the historical dataset.",
    )

    experiment_plan = plan_two_proportion_experiment(
        baseline_rate_pct=float(baseline_rate),
        minimum_detectable_effect_pp=float(mde),
        significance_level=significance_level,
        target_power=target_power,
    )
    per_arm = int(experiment_plan["sample_size_per_arm"])
    total_sample = int(experiment_plan["total_sample_size"])
    duration_days = int(np.ceil(total_sample / int(eligible_per_day)))

    st.markdown("### Your experiment blueprint")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Participants per arm", f"{per_arm:,}")
    k2.metric("Total participants", f"{total_sample:,}")
    k3.metric("Estimated enrollment", f"{duration_days:,} days")
    k4.metric(
        "Target conversion",
        f"{experiment_plan['target_rate_pct']:.1f}%",
        delta=f"+{experiment_plan['minimum_detectable_effect_pp']:.1f} pp",
    )
    arm_left, arm_right = st.columns(2)
    with arm_left:
        st.markdown(
            f'<div class="rp-experiment-arm"><div class="rp-experiment-arm-label">CONTROL · CURRENT EXPERIENCE</div>'
            f'<div class="rp-experiment-arm-n">{per_arm:,}</div>'
            f'<div class="rp-experiment-arm-caption">participants · assumed conversion {baseline_rate:.1f}%</div></div>',
            unsafe_allow_html=True,
        )
    with arm_right:
        st.markdown(
            f'<div class="rp-experiment-arm variant"><div class="rp-experiment-arm-label">VARIANT · NEW EXPERIENCE</div>'
            f'<div class="rp-experiment-arm-n">{per_arm:,}</div>'
            f'<div class="rp-experiment-arm-caption">participants · target conversion {experiment_plan["target_rate_pct"]:.1f}%</div></div>',
            unsafe_allow_html=True,
        )

    sensitivity_rows = []
    for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5]:
        effect = min(float(headroom), max(0.1, float(mde) * multiplier))
        if any(abs(effect - row["minimum_detectable_effect_pp"]) < 1e-9 for row in sensitivity_rows):
            continue
        sensitivity_plan = plan_two_proportion_experiment(
            baseline_rate_pct=float(baseline_rate),
            minimum_detectable_effect_pp=effect,
            significance_level=significance_level,
            target_power=target_power,
        )
        sensitivity_rows.append({
            "minimum_detectable_effect_pp": effect,
            "sample_size_per_arm": sensitivity_plan["sample_size_per_arm"],
            "total_sample_size": sensitivity_plan["total_sample_size"],
        })
    sensitivity = pd.DataFrame(sensitivity_rows)
    chart_left, chart_right = st.columns([1.35, 1])
    with chart_left:
        st.markdown("**How the detectable uplift changes sample size**")
        fig = px.line(
            sensitivity,
            x="minimum_detectable_effect_pp",
            y="sample_size_per_arm",
            markers=True,
            labels={
                "minimum_detectable_effect_pp": "Minimum detectable uplift (percentage points)",
                "sample_size_per_arm": "Participants required per arm",
            },
        )
        fig.add_vline(x=float(mde), line_dash="dash", line_color="#6558d3")
        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=12, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#475467"),
        )
        st.plotly_chart(fig, width="stretch")
    with chart_right:
        st.markdown("**Design assumptions**")
        st.markdown(
            f"- Control rate: **{baseline_rate:.2f}%**\n"
            f"- Variant target: **{experiment_plan['target_rate_pct']:.2f}%**\n"
            f"- Two-sided alpha: **{significance_level:.2f}**\n"
            f"- Target power: **{target_power:.0%}**\n"
            "- Allocation: **50 / 50**\n"
            f"- Eligible participants/day: **{int(eligible_per_day):,}**"
        )
        st.caption(
            "Enrollment duration is a rough planning estimate based on the participant/day input; "
            "it excludes ramp-up, eligibility loss, and outcome-maturation time."
        )

    st.download_button(
        "Download experiment plan (CSV)",
        data=sensitivity.to_csv(index=False).encode("utf-8"),
        file_name="retailpulse_experiment_sample_size_sensitivity.csv",
        mime="text/csv",
    )

    with st.expander("Evaluate a completed A/B test", expanded=False):
        st.caption(
            "Enter conversions and eligible participants for both arms. Set the pre-declared allocation "
            "ratio so RetailPulse can check whether the observed sample split is unexpectedly imbalanced."
        )
        expected_control_share_pct = st.slider(
            "Expected control allocation (%)",
            min_value=1.0,
            max_value=99.0,
            value=50.0,
            step=1.0,
            key="experiment_expected_control_share",
            help="Use the allocation specified before launch (for example 50/50 or 90/10).",
        )
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("**Control arm**")
            control_trials = st.number_input(
                "Control participants", min_value=0, max_value=100_000_000,
                value=0, step=100, key="experiment_control_trials",
            )
            control_successes = st.number_input(
                "Control conversions", min_value=0, max_value=100_000_000,
                value=0, step=10, key="experiment_control_successes",
            )
        with e2:
            st.markdown("**Variant arm**")
            variant_trials = st.number_input(
                "Variant participants", min_value=0, max_value=100_000_000,
                value=0, step=100, key="experiment_variant_trials",
            )
            variant_successes = st.number_input(
                "Variant conversions", min_value=0, max_value=100_000_000,
                value=0, step=10, key="experiment_variant_successes",
            )

        if int(control_trials) > 0 and int(variant_trials) > 0:
            try:
                outcome = evaluate_two_proportion_experiment(
                    control_successes=int(control_successes),
                    control_trials=int(control_trials),
                    variant_successes=int(variant_successes),
                    variant_trials=int(variant_trials),
                    significance_level=significance_level,
                    expected_control_share=float(expected_control_share_pct) / 100,
                )
                o1, o2, o3, o4 = st.columns(4)
                o1.metric("Control conversion", f"{outcome['control_conversion_rate_pct']:.2f}%")
                o2.metric("Variant conversion", f"{outcome['variant_conversion_rate_pct']:.2f}%")
                o3.metric("Absolute difference", f"{outcome['absolute_difference_pp']:+.2f} pp")
                p_value_display = (
                    f"{outcome['p_value']:.4f}"
                    if outcome["p_value"] is not None
                    else "Not computed"
                )
                o4.metric("Two-sided p-value", p_value_display)
                ci_text = (
                    f"{outcome['confidence_level_pct']:.0f}% CI for variant − control: "
                    f"[{outcome['difference_ci_lower_pp']:+.2f}, "
                    f"{outcome['difference_ci_upper_pp']:+.2f}] percentage points."
                )
                result_class = "rp-result-positive" if (
                    outcome["statistically_significant"]
                    and outcome["absolute_difference_pp"] > 0
                ) else "rp-result-neutral"
                st.markdown(
                    f'<div class="{result_class}"><strong>{outcome["decision"]}</strong><br>{ci_text}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Inference: {outcome['inference_method']}. "
                    f"Confidence interval: {outcome['confidence_interval_method']}."
                )
                if outcome["statistically_significant"]:
                    st.success(
                        "The observed difference meets the selected statistical significance threshold. "
                        "Review the confidence interval and experiment-quality checks before acting."
                    )
                else:
                    st.info(
                        "The observed data do not establish a difference at the selected significance level. "
                        "This is not proof that the experiences are equivalent."
                    )

                srm = outcome["sample_ratio_diagnostic"]
                st.markdown("### Experiment integrity · allocation check")
                integrity_left, integrity_right = st.columns([1, 1.35])
                with integrity_left:
                    srm_p_value = "<0.0001" if srm["p_value"] < 0.0001 else f"{srm['p_value']:.4f}"
                    st.metric("Sample-ratio diagnostic p-value", srm_p_value)
                    st.caption(
                        f"Observed control share: {srm['observed_control_share_pct']:.1f}% "
                        f"vs expected {srm['expected_control_share_pct']:.1f}% "
                        f"({srm['allocation_deviation_pp']:+.2f} pp)."
                    )
                    if srm["status"] == "SAMPLE_RATIO_MISMATCH":
                        st.error(
                            "Sample-ratio mismatch flagged. Investigate assignment, eligibility, exposure logging "
                            "and event instrumentation before interpreting the conversion result."
                        )
                    elif srm["status"] == "LOW_EXPECTED_COUNT":
                        st.warning(
                            "Expected arm counts are below five. The chi-square approximation is not dependable; "
                            "collect more observations or use an appropriate exact allocation test."
                        )
                    else:
                        st.success(
                            "No allocation imbalance was flagged at p < 0.001. "
                            "This does not certify randomisation or instrumentation quality."
                        )
                with integrity_right:
                    allocation_figure = go.Figure()
                    allocation_figure.add_trace(go.Bar(
                        name="Expected allocation",
                        x=["Control", "Variant"],
                        y=[srm["expected_control_share_pct"], srm["expected_variant_share_pct"]],
                        marker_color="#a5afd0",
                    ))
                    allocation_figure.add_trace(go.Bar(
                        name="Observed allocation",
                        x=["Control", "Variant"],
                        y=[srm["observed_control_share_pct"], srm["observed_variant_share_pct"]],
                        marker_color=["#6558d3", "#0e9f8a"],
                    ))
                    allocation_figure.update_layout(
                        barmode="group", height=300,
                        margin=dict(l=10, r=10, t=18, b=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#475467"),
                        yaxis=dict(title="Share of enrolled participants (%)", range=[0, 100]),
                        legend=dict(orientation="h", y=1.15, x=0),
                    )
                    st.plotly_chart(allocation_figure, width="stretch")
                with st.expander("Statistical interpretation and guardrails"):
                    if outcome["relative_lift_pct"] is None:
                        relative_text = "Undefined because the control conversion rate is zero."
                    else:
                        relative_text = f"{outcome['relative_lift_pct']:.2f}%"
                    st.markdown(
                        f"- Conversion test: {outcome['method']}.\\n"
                        f"- z statistic: **{outcome['z_score']:.3f}**.\\n"
                        f"- Relative lift: **{relative_text}**.\\n"
                        f"- Allocation test: {srm['method']}.\\n"
                        f"- Allocation threshold: **p < {srm['significance_level']:.3f}**."
                    )
                    for limitation in outcome["limitations"] + srm["limitations"]:
                        st.markdown(f"- {limitation}")
            except ValueError as exc:
                st.error(str(exc))
        else:
            st.info("Enter a positive participant count for both arms to see the experiment readout.")

    with st.expander("Methodology and interpretation"):
        st.markdown(
            """
            - **Primary metric:** a binary conversion outcome measured over one pre-defined window.
            - **Sample-size design:** equal 50/50 allocation using a two-sided two-proportion normal-approximation formula.
            - **Power:** the probability of detecting the specified minimum effect under the assumed alternative when that effect is present.
            - **Absolute effect:** variant conversion minus control conversion, reported in percentage points.
            - **Inference:** pooled-standard-error z-test for the null of equal proportions; the confidence interval uses the unpooled standard error.
            """
        )
        st.warning(
            "The planner assumes independent participants and a single binary primary outcome. "
            "It does not handle clustering, repeated exposure, attrition, non-compliance, multiple testing "
            "or sequential peeking. A statistical readout cannot confirm randomisation or instrumentation quality. "
            "The historical UCI conversion reference is not a current baseline; eligible participants/day is always user-entered."
        )

# Global project footer / downloads
st.divider()
st.caption("RetailPulse · UCI Online Retail II · Historical observation period 1 Dec 2009 – 9 Dec 2011 · Revenue is not profit · Analyses are descriptive unless explicitly identified as historical model backtests.")
report_path = PHASE3 / "PHASE3_ADVANCED_ANALYTICS.md"
if report_path.exists():
    st.download_button("Download Phase 3 advanced analytics report", report_path.read_bytes(),
                       file_name="RetailPulse_Phase3_Advanced_Analytics.md", mime="text/markdown")
