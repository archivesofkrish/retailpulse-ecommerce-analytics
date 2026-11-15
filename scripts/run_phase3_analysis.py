#!/usr/bin/env python3
"""Reproducible Phase 3 analytics for RetailPulse.

Reads the processed transaction exports created by scripts/run_analysis.py and
writes advanced customer, product, country, cohort, and historical inactivity
backtest outputs under reports/phase3/.

The 90-day target is explicitly a historical inactivity proxy, not a verified
customer-churn event or a current operational prediction.
"""
from __future__ import annotations

import json
import math
import warnings
from collections import Counter
from itertools import combinations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retailpulse.provenance import read_json_object, write_json_atomic
from retailpulse.insights import generate_business_insights, INSIGHT_COLUMNS

DATA = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "phase3"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_inputs():
    required = [
        "sales_lines.csv", "customer_rfm.csv", "rfm_segment_summary.csv",
        "product_performance.csv", "country_performance.csv", "kpis.json",
        "pipeline_manifest.json",
    ]
    for name in required:
        require_file(DATA / name)

    pipeline_manifest = read_json_object(DATA / "pipeline_manifest.json")
    if pipeline_manifest.get("status") != "complete":
        raise RuntimeError(
            "Core pipeline outputs are incomplete. Run scripts/run_analysis.py before Phase 3."
        )

    sales = pd.read_csv(DATA / "sales_lines.csv", low_memory=False, dtype={"customer_id": "string"})
    rfm = pd.read_csv(DATA / "customer_rfm.csv", low_memory=False, dtype={"customer_id": "string"})
    segments = pd.read_csv(DATA / "rfm_segment_summary.csv", low_memory=False)
    products = pd.read_csv(DATA / "product_performance.csv", low_memory=False)
    countries = pd.read_csv(DATA / "country_performance.csv", low_memory=False)
    with (DATA / "kpis.json").open(encoding="utf-8") as f:
        kpis = json.load(f)

    needed_sales = {"invoice", "stock_code", "quantity", "invoice_date", "customer_id", "revenue", "country"}
    if not needed_sales.issubset(sales.columns):
        raise ValueError(f"sales_lines.csv missing columns: {sorted(needed_sales - set(sales.columns))}")
    needed_rfm = {"customer_id", "frequency", "monetary", "recency_days", "customer_tenure_days", "rfm_segment"}
    if not needed_rfm.issubset(rfm.columns):
        raise ValueError(f"customer_rfm.csv missing columns: {sorted(needed_rfm - set(rfm.columns))}")

    sales["invoice_date"] = pd.to_datetime(sales["invoice_date"], errors="coerce")
    sales["customer_id_key"] = sales["customer_id"].astype("string").str.strip()
    sales["customer_id_key"] = sales["customer_id_key"].mask(sales["customer_id_key"].eq(""), pd.NA)
    rfm["customer_id"] = rfm["customer_id"].astype("string").str.strip()
    rfm["customer_id"] = rfm["customer_id"].mask(rfm["customer_id"].eq(""), pd.NA)
    sales["invoice_key"] = sales["invoice"].astype(str)
    sales["stock_code_key"] = sales["stock_code"].astype(str)
    for col in ["quantity", "revenue"]:
        sales[col] = pd.to_numeric(sales[col], errors="coerce")
    for col in ["frequency", "monetary", "recency_days", "customer_tenure_days"]:
        rfm[col] = pd.to_numeric(rfm[col], errors="coerce")
    return sales, rfm, segments, products, countries, kpis, pipeline_manifest


def gini(values: pd.Series | np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    x = np.clip(x, 0, None)
    if len(x) == 0 or x.sum() == 0:
        return float("nan")
    x.sort()
    n = len(x)
    return float((2 * np.dot(np.arange(1, n + 1), x) / (n * x.sum())) - (n + 1) / n)


def pct_money(x: float) -> str:
    return f"£{x:,.2f}"


def make_customer_outputs(sales: pd.DataFrame, rfm: pd.DataFrame, kpis: dict):
    """Build customer concentration and repeat-purchase outputs, including empty-ID cases."""
    cust = rfm.copy()
    cust["customer_id"] = cust["customer_id"].astype("string").str.strip()
    cust["customer_id"] = cust["customer_id"].mask(cust["customer_id"].eq(""), pd.NA)
    cust = cust.dropna(subset=["customer_id", "monetary"]).copy()
    cust["monetary"] = cust["monetary"].clip(lower=0)
    cust = cust.sort_values("monetary", ascending=False).reset_index(drop=True)
    n = len(cust)
    total = float(cust["monetary"].sum())

    cust["revenue_rank"] = np.arange(1, n + 1, dtype=int)
    cust["customer_share_cumulative"] = cust["revenue_rank"] / n if n else pd.Series(dtype=float)
    cust["revenue_share_cumulative"] = (
        cust["monetary"].cumsum() / total if total > 0 else pd.Series(dtype=float)
    )
    cust.to_csv(OUT / "customer_revenue_concentration.csv", index=False)

    top_rows = []
    pareto_rows = []
    if n and total > 0:
        for pct in [0.01, 0.05, 0.10, 0.20]:
            k = max(1, math.ceil(n * pct))
            value = float(cust.head(k)["monetary"].sum())
            top_rows.append({
                "top_customer_share_pct": pct * 100,
                "customers": k,
                "historical_revenue_gbp": value,
                "identified_revenue_share_pct": value / total * 100,
            })
        for threshold in [0.50, 0.80, 0.90]:
            cumulative = cust["revenue_share_cumulative"].to_numpy()
            reached = np.flatnonzero(cumulative >= threshold)
            k = int(reached[0] + 1) if len(reached) else n
            pareto_rows.append({
                "revenue_threshold_pct": threshold * 100,
                "customers_required": k,
                "customer_base_share_pct": k / n * 100,
            })

    top_columns = [
        "top_customer_share_pct", "customers",
        "historical_revenue_gbp", "identified_revenue_share_pct",
    ]
    pareto_columns = [
        "revenue_threshold_pct", "customers_required", "customer_base_share_pct",
    ]
    pd.DataFrame(top_rows, columns=top_columns).to_csv(
        OUT / "top_customer_concentration.csv", index=False
    )
    pd.DataFrame(pareto_rows, columns=pareto_columns).to_csv(
        OUT / "customer_pareto_thresholds.csv", index=False
    )

    segment_columns = [
        "rfm_segment", "customers", "historical_revenue_gbp",
        "avg_recency_days", "median_recency_days", "avg_orders_per_customer",
        "median_historical_revenue_gbp", "customer_share_pct",
        "identified_revenue_share_pct",
    ]
    if n:
        seg = (
            cust.groupby("rfm_segment", dropna=False)
            .agg(
                customers=("customer_id", "size"),
                historical_revenue_gbp=("monetary", "sum"),
                avg_recency_days=("recency_days", "mean"),
                median_recency_days=("recency_days", "median"),
                avg_orders_per_customer=("frequency", "mean"),
                median_historical_revenue_gbp=("monetary", "median"),
            )
            .reset_index()
        )
        seg["customer_share_pct"] = seg["customers"] / n * 100
        seg["identified_revenue_share_pct"] = (
            seg["historical_revenue_gbp"] / total * 100 if total > 0 else 0.0
        )
        seg = seg.sort_values("historical_revenue_gbp", ascending=False)
    else:
        seg = pd.DataFrame(columns=segment_columns)
    seg.to_csv(OUT / "customer_segment_value.csv", index=False)

    # Customer-level order history is unavailable when no valid identifiers exist.
    sales_known = sales.dropna(
        subset=["customer_id_key", "invoice_date", "invoice_key"]
    ).copy()
    if sales_known.empty:
        orders = pd.DataFrame(columns=[
            "customer_id_key", "invoice_key", "order_date", "order_revenue", "order_number",
        ])
        first_second = pd.DataFrame(columns=[
            "customer_id_key", "first_order_date", "second_order_date", "days_to_second_order",
        ])
    else:
        orders = (
            sales_known.groupby(["customer_id_key", "invoice_key"], as_index=False)
            .agg(order_date=("invoice_date", "min"), order_revenue=("revenue", "sum"))
        )
        orders = orders.sort_values(["customer_id_key", "order_date", "invoice_key"])
        orders["order_number"] = orders.groupby("customer_id_key").cumcount() + 1
        first_orders = (
            orders.loc[orders["order_number"].eq(1), ["customer_id_key", "order_date"]]
            .rename(columns={"order_date": "first_order_date"})
        )
        second_orders = (
            orders.loc[orders["order_number"].eq(2), ["customer_id_key", "order_date"]]
            .rename(columns={"order_date": "second_order_date"})
        )
        first_second = first_orders.merge(second_orders, on="customer_id_key", how="left")
        first_second["days_to_second_order"] = (
            first_second["second_order_date"] - first_second["first_order_date"]
        ).dt.total_seconds() / 86400

    first_second.to_csv(OUT / "customer_first_second_order.csv", index=False)
    observation_end = sales["invoice_date"].max().normalize()
    order_counts = (
        orders.groupby("customer_id_key")["invoice_key"].nunique()
        if not orders.empty else pd.Series(dtype=int)
    )
    repeat_customers = int((order_counts >= 2).sum())
    single_order_customers = int((order_counts == 1).sum())
    windows = []
    for days in [30, 60, 90, 180, 365]:
        eligible = first_second[
            first_second["first_order_date"] <= observation_end - timedelta(days=days)
        ]
        returned = int((
            eligible["days_to_second_order"].notna()
            & eligible["days_to_second_order"].le(days)
        ).sum())
        windows.append({
            "follow_up_days": days,
            "eligible_customers": int(len(eligible)),
            "customers_with_second_order": returned,
            "second_order_within_window_pct": (
                returned / len(eligible) * 100 if len(eligible) else np.nan
            ),
        })
    pd.DataFrame(windows).to_csv(OUT / "repeat_purchase_windows.csv", index=False)

    metrics = {
        "identified_customers": int(n),
        "identified_customer_historical_revenue_gbp": total,
        "mean_historical_revenue_per_customer_gbp": (
            float(cust["monetary"].mean()) if n else None
        ),
        "median_historical_revenue_per_customer_gbp": (
            float(cust["monetary"].median()) if n else None
        ),
        "p90_historical_revenue_per_customer_gbp": (
            float(cust["monetary"].quantile(.90)) if n else None
        ),
        "p99_historical_revenue_per_customer_gbp": (
            float(cust["monetary"].quantile(.99)) if n else None
        ),
        "max_historical_revenue_per_customer_gbp": (
            float(cust["monetary"].max()) if n else None
        ),
        "mean_orders_per_customer": (
            float(cust["frequency"].mean()) if n else None
        ),
        "median_orders_per_customer": (
            float(cust["frequency"].median()) if n else None
        ),
        "repeat_customers": repeat_customers,
        "repeat_customer_share_pct": repeat_customers / n * 100 if n else 0.0,
        "single_order_customers": single_order_customers,
        "single_order_customer_share_pct": (
            single_order_customers / n * 100 if n else 0.0
        ),
        "customer_revenue_gini": gini(cust["monetary"]) if n else None,
        "median_days_to_second_order_among_repeaters": (
            float(first_second["days_to_second_order"].dropna().median())
            if first_second["days_to_second_order"].notna().any() else None
        ),
        "mean_days_to_second_order_among_repeaters": (
            float(first_second["days_to_second_order"].dropna().mean())
            if first_second["days_to_second_order"].notna().any() else None
        ),
        "top_customer_concentration": top_rows,
        "customer_pareto_thresholds": pareto_rows,
        "repeat_purchase_windows": windows,
    }
    return cust, seg, orders, metrics


def make_country_outputs(countries: pd.DataFrame):
    c = countries.copy()
    for col in ["revenue", "orders", "customers", "units"]:
        if col in c:
            c[col] = pd.to_numeric(c[col], errors="coerce")
    c = c.sort_values("revenue", ascending=False).reset_index(drop=True)
    total = float(c["revenue"].sum())
    c["revenue_share_pct"] = c["revenue"] / total * 100
    c["cumulative_revenue_share_pct"] = c["revenue"].cumsum() / total * 100
    c["revenue_per_identified_customer_gbp"] = c["revenue"] / c["customers"].replace(0, np.nan)
    c.to_csv(OUT / "country_concentration.csv", index=False)
    return c, {"country_count": int(len(c)), "top_country": str(c.iloc[0]["country"]),
               "top_country_revenue_share_pct": float(c.iloc[0]["revenue_share_pct"]),
               "top_five_country_revenue_share_pct": float(c.head(5)["revenue"].sum() / total * 100),
               "non_top_country_revenue_share_pct": float(100 - c.iloc[0]["revenue_share_pct"])}


def make_product_outputs(sales: pd.DataFrame, products: pd.DataFrame):
    """Build merchandise metrics without failing when no merchandise SKUs exist."""
    p = products.copy()
    p["product_type_clean"] = p["product_type"].astype(str).str.strip()
    for col in ["revenue", "units", "orders"]:
        p[col] = pd.to_numeric(p[col], errors="coerce").fillna(0)
    merchandise_rows = p[p["product_type_clean"].str.lower().eq("merchandise")].copy()
    operational_rows = p[~p["product_type_clean"].str.lower().eq("merchandise")].copy()

    product_columns = [
        "stock_code", "revenue_gbp", "units", "orders", "description",
        "revenue_share_pct", "cumulative_revenue_share_pct",
    ]
    if merchandise_rows.empty:
        product_codes = pd.DataFrame(columns=product_columns)
    else:
        product_codes = (
            merchandise_rows.groupby("stock_code", as_index=False)
            .agg(
                revenue_gbp=("revenue", "sum"),
                units=("units", "sum"),
                orders=("orders", "sum"),
            )
        )
        descriptions = (
            merchandise_rows.sort_values("revenue", ascending=False)
            .drop_duplicates("stock_code")
            .set_index("stock_code")["description"]
        )
        product_codes["description"] = product_codes["stock_code"].map(descriptions)
        product_codes = product_codes.sort_values(
            "revenue_gbp", ascending=False
        ).reset_index(drop=True)

    total_merch = float(product_codes["revenue_gbp"].sum()) if not product_codes.empty else 0.0
    if not product_codes.empty and total_merch > 0:
        product_codes["revenue_share_pct"] = product_codes["revenue_gbp"] / total_merch * 100
        product_codes["cumulative_revenue_share_pct"] = (
            product_codes["revenue_gbp"].cumsum() / total_merch * 100
        )
    elif not product_codes.empty:
        product_codes["revenue_share_pct"] = 0.0
        product_codes["cumulative_revenue_share_pct"] = 0.0

    # Aggregate at invoice + SKU grain before deriving one-invoice maxima.
    sale_rows = sales.copy()
    sale_rows["stock_code_key"] = sale_rows["stock_code"].astype(str)
    sale_rows["invoice_key"] = sale_rows["invoice"].astype(str)
    invoice_sku = (
        sale_rows.groupby(["stock_code_key", "invoice_key"], as_index=False)
        .agg(
            invoice_units=("quantity", "sum"),
            invoice_revenue_gbp=("revenue", "sum"),
        )
    )
    invoice_stats = (
        invoice_sku.groupby("stock_code_key")
        .agg(
            distinct_invoices=("invoice_key", "nunique"),
            max_single_invoice_units=("invoice_units", "max"),
            max_single_invoice_revenue_gbp=("invoice_revenue_gbp", "max"),
        )
        .reset_index()
        .rename(columns={"stock_code_key": "stock_code"})
    )
    product_codes = product_codes.drop(columns=["orders"], errors="ignore").merge(
        invoice_stats, on="stock_code", how="left"
    )
    product_codes["distinct_invoices"] = (
        product_codes["distinct_invoices"].fillna(0).astype(int)
    )
    product_codes["orders"] = product_codes["distinct_invoices"]
    product_codes.to_csv(OUT / "merchandise_product_concentration.csv", index=False)

    one_order = product_codes.loc[product_codes["distinct_invoices"].le(1)].copy()
    one_order = one_order.sort_values("revenue_gbp", ascending=False)
    one_order.to_csv(OUT / "single_invoice_merchandise_products.csv", index=False)

    ops_total = float(operational_rows["revenue"].sum())
    ops_summary = (
        operational_rows.groupby("stock_code", as_index=False)
        .agg(
            description=("description", "first"),
            revenue_gbp=("revenue", "sum"),
            units=("units", "sum"),
            orders=("orders", "sum"),
        )
        .sort_values("revenue_gbp", ascending=False)
    )
    ops_summary.to_csv(OUT / "operational_non_merchandise_codes.csv", index=False)

    pareto = []
    if not product_codes.empty:
        cumulative = product_codes["cumulative_revenue_share_pct"].to_numpy()
        for threshold in [.50, .80, .90]:
            reached = np.flatnonzero(cumulative >= threshold * 100)
            k = int(reached[0] + 1) if len(reached) else len(product_codes)
            pareto.append({
                "revenue_threshold_pct": threshold * 100,
                "stock_codes_required": k,
                "share_of_merchandise_stock_codes_pct": (
                    k / len(product_codes) * 100
                ),
            })

    top10 = (
        float(product_codes.head(10)["revenue_gbp"].sum() / total_merch * 100)
        if total_merch > 0 else 0.0
    )
    metrics = {
        "merchandise_stock_codes": int(product_codes["stock_code"].nunique()),
        "merchandise_revenue_gbp": total_merch,
        "operational_non_merchandise_revenue_gbp": ops_total,
        "operational_non_merchandise_rows": int(len(operational_rows)),
        "top_10_merchandise_stock_code_revenue_share_pct": top10,
        "single_invoice_merchandise_code_count": int(len(one_order)),
        "product_pareto_thresholds": pareto,
    }
    return product_codes, ops_summary, metrics


def make_product_affinity(sales: pd.DataFrame, products: pd.DataFrame):
    """Calculate invoice-level merchandise association rules.

    Each SKU is counted at most once per invoice. Operational/non-merchandise
    codes are excluded. Rules with fewer than max(5, 0.01% of baskets) joint
    invoices are suppressed to reduce one-off noise.
    """
    columns = [
        "antecedent_stock_code", "antecedent_description",
        "consequent_stock_code", "consequent_description",
        "joint_orders", "merchandise_baskets", "support_pct",
        "antecedent_orders", "consequent_orders", "confidence_pct", "lift",
    ]
    product_rows = products.copy()
    product_rows["stock_code"] = product_rows["stock_code"].astype(str)
    product_rows["product_type_clean"] = product_rows["product_type"].astype(str).str.strip().str.lower()
    merchandise = product_rows[product_rows["product_type_clean"].eq("merchandise")]
    merchandise_codes = set(merchandise["stock_code"])
    descriptions = (
        merchandise.sort_values("revenue", ascending=False)
        .drop_duplicates("stock_code")
        .set_index("stock_code")["description"]
        .astype(str)
        .to_dict()
    )

    eligible_sales = sales.loc[
        sales["stock_code_key"].astype(str).isin(merchandise_codes),
        ["invoice_key", "stock_code_key"],
    ].dropna()
    baskets = (
        eligible_sales.groupby("invoice_key")["stock_code_key"]
        .agg(lambda values: sorted(set(values.astype(str))))
        .tolist()
    )

    basket_count = len(baskets)
    item_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for basket in baskets:
        item_counts.update(basket)
        pair_counts.update(combinations(basket, 2))

    minimum_joint_orders = max(5, math.ceil(basket_count * 0.0001))
    rows = []
    for (item_a, item_b), joint_count in pair_counts.items():
        if joint_count < minimum_joint_orders:
            continue
        support = joint_count / basket_count if basket_count else 0.0
        for antecedent, consequent in ((item_a, item_b), (item_b, item_a)):
            antecedent_count = item_counts[antecedent]
            consequent_count = item_counts[consequent]
            confidence = joint_count / antecedent_count if antecedent_count else 0.0
            consequent_support = consequent_count / basket_count if basket_count else 0.0
            lift = confidence / consequent_support if consequent_support else np.nan
            rows.append({
                "antecedent_stock_code": antecedent,
                "antecedent_description": descriptions.get(antecedent, "Unknown product"),
                "consequent_stock_code": consequent,
                "consequent_description": descriptions.get(consequent, "Unknown product"),
                "joint_orders": int(joint_count),
                "merchandise_baskets": int(basket_count),
                "support_pct": support * 100,
                "antecedent_orders": int(antecedent_count),
                "consequent_orders": int(consequent_count),
                "confidence_pct": confidence * 100,
                "lift": float(lift),
            })

    rules = pd.DataFrame(rows, columns=columns)
    if not rules.empty:
        rules = rules.sort_values(
            ["lift", "joint_orders", "confidence_pct"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
    rules.to_csv(OUT / "product_associations.csv", index=False)

    metrics = {
        "merchandise_baskets": int(basket_count),
        "unique_item_pairs_observed": int(len(pair_counts)),
        "qualified_item_pairs": int(sum(count >= minimum_joint_orders for count in pair_counts.values())),
        "association_rule_count": int(len(rules)),
        "minimum_joint_orders": int(minimum_joint_orders),
        "minimum_support_pct": float(minimum_joint_orders / basket_count * 100) if basket_count else None,
        "top_rule_lift": float(rules.iloc[0]["lift"]) if not rules.empty else None,
    }
    return rules, metrics

def make_cohort_outputs(sales: pd.DataFrame):
    """Build point-in-time cohort activity with right-censored future months.

    A zero means the calendar month was observed but no cohort member purchased.
    NaN means that cohort had not yet reached that month before the source ended.
    """
    x = sales.dropna(subset=["customer_id_key", "invoice_date"]).copy()
    if x.empty:
        empty = pd.DataFrame(columns=["cohort_month"])
        empty.to_csv(OUT / "cohort_retention_recomputed.csv", index=False)
        empty.to_csv(OUT / "cohort_active_customer_counts.csv", index=False)
        return pd.DataFrame(columns=[
            "months_since_first_purchase", "eligible_cohorts", "eligible_customers",
            "active_in_that_calendar_month", "weighted_monthly_active_retention_pct",
        ])

    x["invoice_month"] = x["invoice_date"].dt.to_period("M")
    cm = x[["customer_id_key", "invoice_month"]].drop_duplicates()
    first_month = cm.groupby("customer_id_key")["invoice_month"].min().rename("cohort_month")
    cm = cm.merge(first_month, on="customer_id_key", how="left")
    cm["months_since_first_purchase"] = (
        (cm["invoice_month"].dt.year - cm["cohort_month"].dt.year) * 12
        + (cm["invoice_month"].dt.month - cm["cohort_month"].dt.month)
    ).astype(int)

    cohort_sizes = first_month.value_counts().sort_index()
    end_month = x["invoice_month"].max()
    cohort_months = sorted(cohort_sizes.index)
    max_offset = end_month.ordinal - cohort_months[0].ordinal
    offsets = list(range(max_offset + 1))
    row_labels = [str(m) for m in cohort_months]

    active = pd.DataFrame(np.nan, index=row_labels, columns=offsets, dtype=float)
    for cohort_month in cohort_months:
        observed_offsets = end_month.ordinal - cohort_month.ordinal
        observed_counts = (
            cm.loc[cm["cohort_month"].eq(cohort_month)]
            .groupby("months_since_first_purchase")["customer_id_key"]
            .nunique()
            .reindex(range(observed_offsets + 1), fill_value=0)
        )
        active.loc[str(cohort_month), list(range(observed_offsets + 1))] = observed_counts.to_numpy(dtype=float)

    size_by_label = pd.Series(cohort_sizes.to_numpy(dtype=float), index=row_labels)
    rates = active.div(size_by_label, axis=0)
    rates.index.name = "cohort_month"
    active.index.name = "cohort_month"
    rates.to_csv(OUT / "cohort_retention_recomputed.csv")
    active.to_csv(OUT / "cohort_active_customer_counts.csv")

    weighted = []
    for k in [1, 2, 3, 6, 9, 12, 18, 24]:
        eligible_months = [m for m in cohort_months if m + k <= end_month]
        eligible_n = int(cohort_sizes.loc[eligible_months].sum()) if eligible_months else 0
        repeat_n = int(sum(active.loc[str(m), k] for m in eligible_months)) if eligible_months else 0
        weighted.append({
            "months_since_first_purchase": k,
            "eligible_cohorts": len(eligible_months),
            "eligible_customers": eligible_n,
            "active_in_that_calendar_month": repeat_n,
            "weighted_monthly_active_retention_pct": repeat_n / eligible_n * 100 if eligible_n else np.nan,
        })
    weighted_df = pd.DataFrame(weighted)
    weighted_df.to_csv(OUT / "weighted_cohort_retention.csv", index=False)
    return weighted_df


def make_churn_backtest(orders: pd.DataFrame, observation_end: pd.Timestamp):
    """Historical 90-day inactivity backtest with chronological holdout."""
    def write_skipped_outputs() -> None:
        pd.DataFrame(columns=[
            "snapshot_date", "observations", "observed_90d_inactivity_rate_pct",
            "roc_auc", "average_precision",
        ]).to_csv(OUT / "historical_inactivity_monthly_backtest.csv", index=False)
        pd.DataFrame(columns=["feature", "importance"]).to_csv(
            OUT / "historical_inactivity_feature_importance.csv", index=False
        )
        pd.DataFrame(columns=[
            "customer_id_key", "snapshot_date", "inactive_next_90d",
            "recency_days", "lifetime_orders", "lifetime_revenue",
            "orders_90d", "orders_180d", "orders_365d",
            "predicted_inactivity_score", "risk_rank_pct",
        ]).to_csv(OUT / "historical_inactivity_holdout_scores.csv", index=False)

    if orders.empty:
        write_skipped_outputs()
        return {
            "status": "SKIPPED",
            "reason": "No identified-customer order history is available for a 90-day inactivity backtest.",
        }

    start = orders["order_date"].min() + timedelta(days=90)
    end = observation_end - timedelta(days=90)
    first_cut = (start + pd.offsets.MonthEnd(0)).normalize()
    last_cut = end
    cutoffs = pd.date_range(first_cut, last_cut, freq="ME")
    if len(cutoffs) < 8:
        write_skipped_outputs()
        return {"status": "SKIPPED", "reason": "Insufficient monthly snapshots for a meaningful time split."}

    records = []
    for cut in cutoffs:
        hist = orders[orders["order_date"] <= cut]
        if hist.empty:
            continue
        gb = hist.groupby("customer_id_key")
        base = gb.agg(first_order=("order_date", "min"), last_order=("order_date", "max"),
                      lifetime_orders=("invoice_key", "nunique"), lifetime_revenue=("order_revenue", "sum")).reset_index()
        base["recency_days"] = (cut - base["last_order"]).dt.days
        base["tenure_days"] = (cut - base["first_order"]).dt.days
        base["avg_order_value"] = base["lifetime_revenue"] / base["lifetime_orders"].clip(lower=1)
        for days, label in [(90, "90d"), (180, "180d"), (365, "365d")]:
            window = hist[hist["order_date"] > cut - timedelta(days=days)]
            agg = window.groupby("customer_id_key").agg(
                **{f"orders_{label}": ("invoice_key", "nunique"), f"revenue_{label}": ("order_revenue", "sum")})
            base = base.merge(agg, on="customer_id_key", how="left")
            base[f"orders_{label}"] = base[f"orders_{label}"].fillna(0)
            base[f"revenue_{label}"] = base[f"revenue_{label}"].fillna(0)
        future = orders[(orders["order_date"] > cut) & (orders["order_date"] <= cut + timedelta(days=90))]
        future_n = future.groupby("customer_id_key")["invoice_key"].nunique()
        base["future_orders_90d"] = base["customer_id_key"].map(future_n).fillna(0)
        base["inactive_next_90d"] = (base["future_orders_90d"] == 0).astype(int)
        base["snapshot_date"] = cut
        base["snapshot_month"] = cut.month
        records.append(base)

    panel = pd.concat(records, ignore_index=True)
    # Purge the 90-day target horizon between the final training snapshot and
    # the first test snapshot. Training labels must be fully observable before
    # the model is evaluated at the first held-out date.
    split_date = pd.Timestamp("2010-10-31")
    label_horizon = timedelta(days=90)
    train = panel[panel["snapshot_date"] <= split_date].copy()
    test = panel[panel["snapshot_date"] > split_date + label_horizon].copy()
    latest_train_label_end = train["snapshot_date"].max() + label_horizon if not train.empty else pd.NaT
    if not train.empty and not test.empty and latest_train_label_end >= test["snapshot_date"].min():
        raise RuntimeError("Temporal holdout leakage: training label horizon overlaps test snapshots.")
    features = ["recency_days", "tenure_days", "lifetime_orders", "lifetime_revenue", "avg_order_value",
                "orders_90d", "revenue_90d", "orders_180d", "revenue_180d", "orders_365d", "revenue_365d",
                "snapshot_month"]
    if train.empty or test.empty or train["inactive_next_90d"].nunique() < 2 or test["inactive_next_90d"].nunique() < 2:
        write_skipped_outputs()
        return {"status": "SKIPPED", "reason": "Insufficient class coverage in chronological train/test split."}

    model = RandomForestClassifier(n_estimators=250, max_depth=10, min_samples_leaf=25,
                                   n_jobs=-1, class_weight="balanced_subsample", random_state=42)
    model.fit(train[features], train["inactive_next_90d"])
    probabilities = model.predict_proba(test[features])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    y = test["inactive_next_90d"].to_numpy()
    cm = confusion_matrix(y, predictions, labels=[0, 1])
    top_k = max(1, math.ceil(len(test) * .20))
    top_ix = np.argsort(probabilities)[::-1][:top_k]
    top_y = y[top_ix]
    monthly = []
    for date, group in test.groupby("snapshot_date"):
        idx = group.index
        prob = model.predict_proba(group[features])[:, 1]
        labels = group["inactive_next_90d"]
        monthly.append({"snapshot_date": str(date.date()), "observations": int(len(group)),
                        "observed_90d_inactivity_rate_pct": float(labels.mean() * 100),
                        "roc_auc": float(roc_auc_score(labels, prob)) if labels.nunique() > 1 else np.nan,
                        "average_precision": float(average_precision_score(labels, prob)) if labels.sum() > 0 else np.nan})
    pd.DataFrame(monthly).to_csv(OUT / "historical_inactivity_monthly_backtest.csv", index=False)

    scored = test[["customer_id_key", "snapshot_date", "inactive_next_90d", "recency_days", "lifetime_orders",
                   "lifetime_revenue", "orders_90d", "orders_180d", "orders_365d"]].copy()
    scored["predicted_inactivity_score"] = probabilities
    scored["risk_rank_pct"] = scored["predicted_inactivity_score"].rank(pct=True) * 100
    scored.to_csv(OUT / "historical_inactivity_holdout_scores.csv", index=False)
    pd.DataFrame({"feature": features, "importance": model.feature_importances_}).sort_values(
        "importance", ascending=False).to_csv(OUT / "historical_inactivity_feature_importance.csv", index=False)

    metrics = {
        "status": "COMPLETED",
        "target_definition": "No identified-customer invoice during the 90 days after a monthly snapshot date.",
        "snapshot_period": [str(panel.snapshot_date.min().date()), str(panel.snapshot_date.max().date())],
        "training_snapshot_end": str(train.snapshot_date.max().date()),
        "training_label_observation_end": str(latest_train_label_end.date()),
        "test_snapshot_start": str(test.snapshot_date.min().date()),
        "test_snapshot_end": str(test.snapshot_date.max().date()),
        "label_horizon_days": 90,
        "purged_embargo_days": 90,
        "train_snapshot_customer_observations": int(len(train)),
        "test_snapshot_customer_observations": int(len(test)),
        "train_90d_inactivity_prevalence_pct": float(train["inactive_next_90d"].mean() * 100),
        "test_90d_inactivity_prevalence_pct": float(y.mean() * 100),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(average_precision_score(y, probabilities)),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "accuracy_at_0_5": float(accuracy_score(y, predictions)),
        "precision_at_0_5": float(precision_score(y, predictions, zero_division=0)),
        "recall_at_0_5": float(recall_score(y, predictions, zero_division=0)),
        "confusion_matrix_labels_0_then_1": cm.tolist(),
        "top_20pct_risk_observed_inactivity_rate_pct": float(top_y.mean() * 100),
        "top_20pct_risk_capture_recall_pct": float(top_y.sum() / y.sum() * 100),
        "top_20pct_risk_lift": float(top_y.mean() / y.mean()),
        "mean_predicted_probability": float(probabilities.mean()),
        "feature_importance": dict(sorted(zip(features, model.feature_importances_), key=lambda x: x[1], reverse=True)),
        "limitations": [
            "The target is 90-day inactivity, not a verified permanent churn event.",
            "Customer-month observations repeat the same customers; observations are not statistically independent.",
            "The test period is historical (2010-11 to 2011-08), so results do not describe current customers.",
            "Predicted probabilities are not calibrated for direct financial forecasting; use scores for historical ranking only.",
            "The dataset contains only identified-customer orders for this model; anonymous transactions are excluded."
        ]
    }
    return metrics


def make_charts(cust, seg, countries, products, repeat_windows, churn_metrics):
    FIG.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    if cust.empty:
        ax.text(.5, .5, "No identifiable customers in this dataset", ha="center", va="center")
    else:
        ax.plot(cust["customer_share_cumulative"] * 100, cust["revenue_share_cumulative"] * 100)
        ax.axhline(80, linestyle="--", linewidth=1)
        ax.axvline(20, linestyle="--", linewidth=1)
    ax.set(
        title="Identified-customer revenue concentration",
        xlabel="Cumulative share of customers (%)",
        ylabel="Cumulative share of identified-customer revenue (%)",
        xlim=(0, 100), ylim=(0, 100),
    )
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(FIG / "customer_revenue_pareto.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    if seg.empty:
        ax.text(.5, .5, "RFM segments unavailable: no identified customers", ha="center", va="center")
    else:
        ss = seg.sort_values("identified_revenue_share_pct", ascending=True)
        y = np.arange(len(ss))
        ax.barh(y - .18, ss["customer_share_pct"], height=.35, label="Customer share")
        ax.barh(y + .18, ss["identified_revenue_share_pct"], height=.35, label="Revenue share")
        ax.set_yticks(y, ss["rfm_segment"])
        ax.set_xlabel("Share (%)")
        ax.legend()
    ax.set_title("Customer share vs. historical revenue share by RFM segment")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    fig.savefig(FIG / "segment_share_comparison.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    if repeat_windows["eligible_customers"].sum() == 0:
        ax.text(.5, .5, "Repeat-purchase analysis unavailable: no identified customers", ha="center", va="center")
    else:
        ax.bar(repeat_windows["follow_up_days"].astype(str), repeat_windows["second_order_within_window_pct"])
    ax.set(
        title="Identified customers making a second purchase",
        xlabel="Follow-up window (days)",
        ylabel="Customers with second purchase (%)",
    )
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(FIG / "second_purchase_windows.png", dpi=160)
    plt.close(fig)

    top = countries.head(10).sort_values("revenue", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    if top.empty:
        ax.text(.5, .5, "No country-level sales data", ha="center", va="center")
    else:
        ax.barh(top["country"], top["revenue"] / 1_000_000)
    ax.set(title="Revenue by country — top 10", xlabel="Revenue (£ millions)")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    fig.savefig(FIG / "country_revenue_top10.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    if products.empty:
        ax.text(.5, .5, "Merchandise analysis unavailable: no merchandise stock codes", ha="center", va="center")
    else:
        ax.plot(
            np.arange(1, len(products) + 1) / len(products) * 100,
            products["cumulative_revenue_share_pct"],
        )
        ax.axhline(80, linestyle="--", linewidth=1)
    ax.set(
        title="Merchandise revenue concentration by stock code",
        xlabel="Cumulative share of merchandise stock codes (%)",
        ylabel="Cumulative merchandise revenue (%)",
        xlim=(0, 100), ylim=(0, 100),
    )
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(FIG / "merchandise_product_pareto.png", dpi=160)
    plt.close(fig)

    monthly_path = OUT / "historical_inactivity_monthly_backtest.csv"
    if monthly_path.exists():
        m = pd.read_csv(monthly_path)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        if m.empty:
            ax.text(.5, .5, "Historical model skipped", ha="center", va="center")
        else:
            ax.plot(m["snapshot_date"], m["roc_auc"], marker="o")
            ax.axhline(.5, linestyle="--", linewidth=1)
        ax.set(
            title="Historical 90-day inactivity model: monthly holdout ROC-AUC",
            xlabel="Snapshot date", ylabel="ROC-AUC", ylim=(.4, 1.0),
        )
        ax.tick_params(axis="x", rotation=45)
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(FIG / "inactivity_model_monthly_auc.png", dpi=160)
        plt.close(fig)


def build_report(metrics, country_metrics, product_metrics, affinity_metrics, affinity_rules, business_insights, churn_metrics, segments, windows, cohort_summary, kpis):
    """Write a Phase 3 report that treats missing analytical dimensions explicitly."""
    total_sales = float(kpis["gross_sales_revenue_gbp"])
    identified = float(metrics["identified_customer_historical_revenue_gbp"])
    customer_count = int(metrics["identified_customers"])
    risk_names = ["Hibernating", "At Risk", "Cannot Lose Them"]
    risk_seg = segments[segments["rfm_segment"].isin(risk_names)]
    risk_count = int(risk_seg["customers"].sum()) if not risk_seg.empty else 0
    risk_revenue = float(risk_seg["historical_revenue_gbp"].sum()) if not risk_seg.empty else 0.0
    top_customer_rows = pd.read_csv(OUT / "top_customer_concentration.csv")
    product_pareto = pd.DataFrame(product_metrics["product_pareto_thresholds"])
    countries_df = pd.read_csv(OUT / "country_concentration.csv")
    products_df = pd.read_csv(OUT / "merchandise_product_concentration.csv")
    anomalies = pd.read_csv(OUT / "single_invoice_merchandise_products.csv")

    def top_share(pct: float) -> float | None:
        match = top_customer_rows.loc[
            top_customer_rows["top_customer_share_pct"].eq(pct),
            "identified_revenue_share_pct",
        ]
        return float(match.iloc[0]) if not match.empty else None

    lines = [
        "# RetailPulse — Phase 3 Advanced Analytics Report",
        "",
        "**Dataset:** RetailPulse transaction extract",
        f"**Observation window:** {kpis.get('sales_date_min')} to {kpis.get('sales_date_max')}",
        f"**Source sale lines:** {int(kpis['sales_lines']):,}",
        "**Currency:** GBP (£), as recorded in the source",
        "",
        "> This report analyses historical transactions. Revenue is not profit. Historical customer spend is not a forward-looking customer lifetime value (CLV) estimate. The inactivity model predicts a defined 90-day inactivity proxy, not permanent churn.",
        "",
        "## Executive summary",
        "",
        f"- Gross sales-line revenue is **{pct_money(total_sales)}**.",
    ]
    if customer_count:
        lines += [
            f"- Identified-customer RFM reconciles to **{pct_money(identified)}** across **{customer_count:,}** customers ({identified / total_sales * 100 if total_sales else 0:.1f}% of sales revenue).",
            f"- The top 10% of identified customers generate **{top_share(10):.1f}%** of identified-customer revenue; the top 20% generate **{top_share(20):.1f}%**.",
            f"- **{metrics['repeat_customer_share_pct']:.1f}%** of identified customers made at least two purchases within the dataset window.",
        ]
        repeat90 = windows.loc[windows["follow_up_days"].eq(90), "second_order_within_window_pct"]
        if not repeat90.empty and pd.notna(repeat90.iloc[0]):
            lines.append(
                f"- Among customers with a full 90-day follow-up window, **{float(repeat90.iloc[0]):.1f}%** made a second purchase within 90 days."
            )
        else:
            lines.append("- The 90-day repeat-purchase rate is unavailable because no customers had a complete follow-up window.")
    else:
        lines.append(
            "- No usable customer IDs are present. Customer concentration, RFM, repeat-purchase, cohort and customer inactivity analyses are unavailable; sales-level reporting remains valid."
        )

    if not products_df.empty:
        lines.append(
            f"- Merchandise revenue totals **{pct_money(product_metrics['merchandise_revenue_gbp'])}** across **{product_metrics['merchandise_stock_codes']:,}** stock codes."
        )
    else:
        lines.append(
            "- No merchandise stock codes were classified. Merchandise Pareto and product-affinity analyses are unavailable; operational-code revenue is still reported separately."
        )
    lines += [
        f"- The **{country_metrics['top_country']}** accounts for **{country_metrics['top_country_revenue_share_pct']:.1f}%** of gross sales-line revenue; the top five countries account for **{country_metrics['top_five_country_revenue_share_pct']:.1f}%.",
        f"- The processed file contains **{int(kpis.get('rows_missing_customer_id_sales', 0)):,}** sales lines with no customer ID, representing **{float(kpis.get('unidentified_customer_revenue_share_pct', 0)):.1f}%** of sales revenue.",
    ]
    if churn_metrics.get("status") == "COMPLETED":
        lines.append(
            f"- The historical inactivity model achieved a holdout ROC-AUC of **{churn_metrics['roc_auc']:.3f}**. This is a retrospective ranking proof-of-concept, not a deployable churn probability."
        )
    else:
        lines.append(
            f"- The historical inactivity model was skipped: {churn_metrics.get('reason', 'insufficient observations')}."
        )

    lines += [
        "",
        "## 0. Data scope and reconciliation",
        "",
        f"The processed extract classifies **{int(kpis['sales_lines']):,}** sale lines, **{int(kpis['return_or_cancellation_lines']):,}** return/cancellation lines and **{int(kpis.get('rows_neither_sale_nor_return_cancellation', 0)):,}** other valid rows.",
        f"There are **{int(kpis.get('rows_missing_customer_id_sales', 0)):,}** sales lines without customer IDs, representing **{float(kpis.get('unidentified_customer_revenue_share_pct', 0)):.1f}%** of gross sales-line revenue. Identified and unidentified sales revenue reconcile to gross sales-line revenue.",
        "",
        "## 1. Customer value and concentration",
        "",
    ]
    if customer_count:
        lines += [
            f"Identified customers: **{customer_count:,}**. Mean historical spend per identified customer is **{pct_money(metrics['mean_historical_revenue_per_customer_gbp'])}**, while the median is **{pct_money(metrics['median_historical_revenue_per_customer_gbp'])}**.",
            f"The customer revenue Gini coefficient is **{metrics['customer_revenue_gini']:.3f}** (0 = equal distribution; 1 = maximum concentration). The top 1% contribute **{top_share(1):.1f}%** of identified revenue, and the top 5% contribute **{top_share(5):.1f}%**.",
            "",
            "### RFM segment priorities",
            "",
            "| Segment | Customers | Customer share | Historical revenue | Revenue share | Average recency (days) | Average orders |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for _, row in segments.iterrows():
            lines.append(
                f"| {row['rfm_segment']} | {int(row['customers']):,} | {row['customer_share_pct']:.1f}% | {pct_money(row['historical_revenue_gbp'])} | {row['identified_revenue_share_pct']:.1f}% | {row['avg_recency_days']:.1f} | {row['avg_orders_per_customer']:.2f} |"
            )
        lines.append(
            f"The combined Hibernating, At Risk and Cannot Lose Them groups contain **{risk_count:,} customers** ({risk_count / customer_count * 100:.1f}% of the identified base), with historical spend of **{pct_money(risk_revenue)}**. This is historical spend, not expected future revenue at risk."
        )
    else:
        lines.append(
            "No valid customer identifiers were present. RFM segments, customer concentration, customer value distributions and customer-level prioritisation cannot be estimated from this dataset."
        )

    lines += ["", "## 2. Repeat purchasing and retention", ""]
    if customer_count:
        median_days = metrics["median_days_to_second_order_among_repeaters"]
        median_days_text = f"{median_days:.1f} days" if median_days is not None else "unavailable"
        lines += [
            f"The mean number of orders per identified customer is **{metrics['mean_orders_per_customer']:.2f}**, with a median of **{metrics['median_orders_per_customer']:.0f}**. **{metrics['repeat_customers']:,}** customers purchased more than once, while **{metrics['single_order_customers']:,}** purchased once.",
            f"The median interval from first to second order among repeat buyers is **{median_days_text}**.",
            "",
            "| Follow-up window | Eligible first-time customers | Second purchase within window |",
            "|---:|---:|---:|",
        ]
        for _, row in windows.iterrows():
            rate = f"{row['second_order_within_window_pct']:.1f}%" if pd.notna(row["second_order_within_window_pct"]) else "N/A"
            lines.append(
                f"| {int(row['follow_up_days'])} days | {int(row['eligible_customers']):,} | {rate} |"
            )
        lines += [
            "",
            "Cohort values represent point-in-time calendar-month activity relative to the first purchase. They are not cumulative survival probabilities. Blank cells are unobserved follow-up, not zero retention.",
            "",
            "| Months after first purchase | Eligible customers | Active in that exact calendar month |",
            "|---:|---:|---:|",
        ]
        for _, row in cohort_summary.iterrows():
            if pd.notna(row["weighted_monthly_active_retention_pct"]):
                lines.append(
                    f"| {int(row['months_since_first_purchase'])} | {int(row['eligible_customers']):,} | {row['weighted_monthly_active_retention_pct']:.1f}% |"
                )
    else:
        lines.append(
            "Customer repeat-purchase and cohort retention analyses are unavailable because the source contains no usable customer IDs. No customers are fabricated or inferred from anonymous invoices."
        )

    lines += ["", "## 3. Merchandise and product concentration", ""]
    if not products_df.empty:
        lines += [
            f"The merchandise table contains **{product_metrics['merchandise_stock_codes']:,} stock codes** with total recorded revenue of **{pct_money(product_metrics['merchandise_revenue_gbp'])}**. The top 10 stock codes contribute **{product_metrics['top_10_merchandise_stock_code_revenue_share_pct']:.1f}%** of merchandise revenue.",
            "",
            "| Merchandise Pareto threshold | Stock codes required | Share of merchandise codes |",
            "|---:|---:|---:|",
        ]
        for _, row in product_pareto.iterrows():
            lines.append(
                f"| {row['revenue_threshold_pct']:.0f}% of merchandise revenue | {int(row['stock_codes_required']):,} | {row['share_of_merchandise_stock_codes_pct']:.1f}% |"
            )
        if not anomalies.empty:
            a = anomalies.iloc[0]
            lines += [
                "",
                "### Product record requiring manual review",
                "",
                f"Stock code **{a['stock_code']}** ({a['description']}) records **{int(a['units']):,} units**, **{int(a['distinct_invoices']):,} distinct invoice(s)** and **{pct_money(a['revenue_gbp'])}** revenue. The record is retained and flagged for source-document review rather than removed as an assumed error.",
            ]
        lines += [
            "",
            "Operational/non-merchandise codes are excluded from merchandise rankings, but their sales-line revenue remains part of gross sales. Revenue is not profitability.",
            "",
            "### Top merchandise stock codes",
            "",
            "| Stock code | Product description | Revenue | Distinct invoices | Units |",
            "|---|---|---:|---:|---:|",
        ]
        for _, row in products_df.head(10).iterrows():
            lines.append(
                f"| {row['stock_code']} | {row['description']} | {pct_money(row['revenue_gbp'])} | {int(row['distinct_invoices']):,} | {int(row['units']):,} |"
            )
    else:
        lines.append(
            "No merchandise stock codes were classified in this dataset. The product-affinity and merchandise Pareto analyses are unavailable; operational/non-merchandise transaction values are retained in sales-level totals and reported separately."
        )

    lines += [
        "",
        "### Products frequently purchased together",
        "",
        f"Invoice-level baskets include **{affinity_metrics['merchandise_baskets']:,} merchandise invoices**. The minimum co-purchase threshold is **{affinity_metrics['minimum_joint_orders']:,} invoices**.",
    ]
    if affinity_rules.empty:
        lines.append("No product pairs met the minimum co-purchase frequency threshold in this dataset.")
    else:
        lines += [
            "",
            "| Anchor product | Frequently paired with | Joint invoices | Support | Confidence | Lift |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for _, row in affinity_rules.head(10).iterrows():
            lines.append(
                f"| {row['antecedent_stock_code']} — {row['antecedent_description']} "
                f"| {row['consequent_stock_code']} — {row['consequent_description']} "
                f"| {int(row['joint_orders']):,} | {row['support_pct']:.3f}% "
                f"| {row['confidence_pct']:.1f}% | {row['lift']:.2f}x |"
            )
        lines.append(
            "These are historical co-purchase associations, not causal effects or proof that a bundle will increase profit. Validate merchandising changes with a controlled experiment and margin data."
        )

    lines += [
        "",
        "## 4. Country concentration",
        "",
        f"The source includes **{country_metrics['country_count']} countries**. {country_metrics['top_country']} contributes **{country_metrics['top_country_revenue_share_pct']:.1f}%** of total sales-line revenue, and the top five countries contribute **{country_metrics['top_five_country_revenue_share_pct']:.1f}%.",
        "",
        "| Country | Revenue | Revenue share | Orders | Identified customers |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in countries_df.head(10).iterrows():
        lines.append(
            f"| {row['country']} | {pct_money(row['revenue'])} | {row['revenue_share_pct']:.2f}% | {int(row['orders']):,} | {int(row['customers']):,} |"
        )

    lines += ["", "## 5. Historical 90-day inactivity model", ""]
    if churn_metrics.get("status") == "COMPLETED":
        lines += [
            f"A Random Forest model was trained on monthly customer snapshots up to **{churn_metrics['training_snapshot_end']}**. The latest training label window ends **{churn_metrics['training_label_observation_end']}**. A 90-day temporal embargo is applied; held-out snapshots begin **{churn_metrics['test_snapshot_start']}** and run through **{churn_metrics['test_snapshot_end']}**. There were **{churn_metrics['train_snapshot_customer_observations']:,}** training and **{churn_metrics['test_snapshot_customer_observations']:,}** test customer-snapshot observations.",
            "",
            "| Metric | Historical holdout result |",
            "|---|---:|",
            f"| ROC-AUC | {churn_metrics['roc_auc']:.3f} |",
            f"| Average precision | {churn_metrics['average_precision']:.3f} |",
            f"| Brier score | {churn_metrics['brier_score']:.3f} |",
        ]
    else:
        lines.append(
            f"Model status: {churn_metrics.get('status')}. {churn_metrics.get('reason', '')}"
        )
    lines += [
        "",
        "### Model limitations",
        "",
        "- The target is no recorded order within 90 days, not permanent customer loss.",
        "- A 90-day embargo ensures the final training snapshot's inactivity label is observable before the first held-out snapshot; test snapshots still overlap one another in their 90-day outcome windows.",
        "- Customer-month snapshots repeatedly include the same people; rows are correlated, so row counts should not be interpreted as independent customers.",
        "- The model is a retrospective proof-of-concept, not calibrated for expected revenue loss or campaign economics.",
        "- This historical dataset ends on 9 December 2011; it cannot estimate current customer risk.",
        "",
        "## 6. Business decision brief",
        "",
    ]
    if business_insights:
        lines += [
            "The following rules were triggered by the observed historical metrics. Each action is a testable hypothesis, not an automatic decision.",
            "",
            "| Priority | Area | Finding | Evidence | Recommended next action |",
            "|---|---|---|---|---|",
        ]
        for insight in business_insights:
            headline = insight["headline"].replace("|", "\\|")
            evidence = insight["evidence"].replace("|", "\\|")
            action = insight["recommended_action"].replace("|", "\\|")
            lines.append(
                f"| {insight['priority']} | {insight['area']} | {headline} | {evidence} | {action} |"
            )
        lines += ["", "### Interpretation guardrails", ""]
        for insight in business_insights:
            lines.append(f"- **{insight['insight_id']}** — {insight['guardrail']}")
    else:
        lines.append(
            "No pre-defined decision rule crossed its evidence threshold in this run. This is not evidence that no business risk or opportunity exists."
        )

    lines += [
        "",
        "## 7. Definitions and caveats",
        "",
        "- Gross sales-line revenue is not profit and is not net of recorded returns/cancellations.",
        "- Historical customer revenue is not a forecast of future lifetime value.",
        "- Repeat purchase is a second distinct invoice associated with a known customer ID.",
        "- 90-day inactivity is a historical proxy, not permanent churn.",
        "- RFM segments and business insight rules are diagnostic heuristics.",
        "- Merchandise stock-code concentration excludes operational/non-merchandise types.",
        "",
        "## 8. Reproducibility",
        "",
        "Run from the RetailPulse project root: python scripts/run_phase3_analysis.py",
        "Outputs are written to reports/phase3/ from completed core pipeline exports.",
        "",
    ]
    (OUT / "PHASE3_ADVANCED_ANALYTICS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    sales, rfm, segments_source, products, countries, kpis, pipeline_manifest = load_inputs()
    phase3_manifest_path = OUT / "phase3_manifest.json"
    write_json_atomic(phase3_manifest_path, {
        "schema_version": 1,
        "status": "building",
        "pipeline_run_id": pipeline_manifest["run_id"],
        "source_sha256": pipeline_manifest["source"]["sha256"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    # Check primary reconciliation before generating advanced outputs.
    sale_revenue = float(sales["revenue"].sum())
    identified_revenue = float(rfm["monetary"].sum())
    if not np.isclose(sale_revenue, float(kpis["gross_sales_revenue_gbp"]), atol=0.02):
        raise ValueError("Sales-line revenue does not reconcile to kpis.json")
    if not np.isclose(identified_revenue, float(kpis["identified_customer_sales_revenue_gbp"]), atol=0.02):
        raise ValueError("RFM customer revenue does not reconcile to kpis.json")

    cust, seg, orders, customer_metrics = make_customer_outputs(sales, rfm, kpis)
    country_table, country_metrics = make_country_outputs(countries)
    product_table, operational, product_metrics = make_product_outputs(sales, products)
    affinity_rules, affinity_metrics = make_product_affinity(sales, products)
    cohort_summary = make_cohort_outputs(sales)
    business_insights = generate_business_insights(
        kpis=kpis,
        customer_metrics=customer_metrics,
        country_metrics=country_metrics,
        product_metrics=product_metrics,
        repeat_purchase_windows=customer_metrics["repeat_purchase_windows"],
        affinity_rules=affinity_rules.to_dict(orient="records"),
    )
    pd.DataFrame(business_insights, columns=INSIGHT_COLUMNS).to_csv(
        OUT / "business_insights.csv", index=False
    )
    churn_metrics = make_churn_backtest(orders, sales["invoice_date"].max().normalize())
    windows = pd.read_csv(OUT / "repeat_purchase_windows.csv")
    make_charts(cust, seg, country_table, product_table, windows, churn_metrics)
    build_report(customer_metrics, country_metrics, product_metrics, affinity_metrics, affinity_rules, business_insights, churn_metrics, seg, windows, cohort_summary, kpis)

    summary = {
        "source": pipeline_manifest["source"]["file_name"],
        "pipeline_run_id": pipeline_manifest["run_id"],
        "source_sha256": pipeline_manifest["source"]["sha256"],
        "source_start": kpis.get("sales_date_min"),
        "source_end": kpis.get("sales_date_max"),
        "gross_sales_revenue_gbp": float(kpis["gross_sales_revenue_gbp"]),
        "sales_line_count": int(kpis["sales_lines"]),
        "return_cancellation_line_count": int(kpis["return_or_cancellation_lines"]),
        "customer_metrics": customer_metrics,
        "country_metrics": country_metrics,
        "product_metrics": product_metrics,
        "product_affinity_metrics": affinity_metrics,
        "business_insights": business_insights,
        "business_insight_count": len(business_insights),
        "high_priority_business_insight_count": sum(
            item["priority"] == "High" for item in business_insights
        ),
        "historical_inactivity_model": churn_metrics,
        "important_caveat": "Historical analysis only; no profit/cost data and no current customer activity after 2011-12-09.",
    }
    write_json_atomic(OUT / "phase3_summary.json", summary)
    current_pipeline_manifest = read_json_object(DATA / "pipeline_manifest.json")
    if current_pipeline_manifest.get("run_id") != pipeline_manifest.get("run_id"):
        raise RuntimeError(
            "The core pipeline changed while Phase 3 was running. Re-run Phase 3 against the latest core outputs."
        )
    phase3_manifest = {
        "schema_version": 1,
        "status": "complete",
        "pipeline_run_id": pipeline_manifest["run_id"],
        "source_sha256": pipeline_manifest["source"]["sha256"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(phase3_manifest_path, phase3_manifest)
    print(json.dumps({
        "status": "SUCCESS",
        "output_dir": str(OUT),
        "identified_customers": customer_metrics["identified_customers"],
        "repeat_customer_share_pct": round(customer_metrics["repeat_customer_share_pct"], 2),
        "customer_revenue_gini": (
            round(customer_metrics["customer_revenue_gini"], 3)
            if customer_metrics["customer_revenue_gini"] is not None else None
        ),
        "top_country": country_metrics["top_country"],
        "top_country_revenue_share_pct": round(country_metrics["top_country_revenue_share_pct"], 2),
        "historical_inactivity_model_status": churn_metrics.get("status"),
        "report": str(OUT / "PHASE3_ADVANCED_ANALYTICS.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
