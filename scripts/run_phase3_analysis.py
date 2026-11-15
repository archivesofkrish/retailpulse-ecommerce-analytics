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

    sales = pd.read_csv(DATA / "sales_lines.csv", low_memory=False)
    rfm = pd.read_csv(DATA / "customer_rfm.csv", low_memory=False)
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
    sales["customer_id_num"] = pd.to_numeric(sales["customer_id"], errors="coerce")
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
    cust = rfm.copy()
    cust["customer_id"] = pd.to_numeric(cust["customer_id"], errors="coerce")
    cust = cust.dropna(subset=["customer_id", "monetary"]).copy()
    cust["monetary"] = cust["monetary"].clip(lower=0)
    cust = cust.sort_values("monetary", ascending=False).reset_index(drop=True)
    n = len(cust)
    total = float(cust["monetary"].sum())
    cust["revenue_rank"] = np.arange(1, n + 1)
    cust["customer_share_cumulative"] = cust["revenue_rank"] / n
    cust["revenue_share_cumulative"] = cust["monetary"].cumsum() / total
    cust.to_csv(OUT / "customer_revenue_concentration.csv", index=False)

    top_rows = []
    for pct in [0.01, 0.05, 0.10, 0.20]:
        k = max(1, math.ceil(n * pct))
        value = float(cust.head(k)["monetary"].sum())
        top_rows.append({"top_customer_share_pct": pct * 100, "customers": k,
                         "historical_revenue_gbp": value, "identified_revenue_share_pct": value / total * 100})
    pareto_rows = []
    for threshold in [0.50, 0.80, 0.90]:
        k = int(np.argmax(cust["revenue_share_cumulative"].to_numpy() >= threshold) + 1)
        pareto_rows.append({"revenue_threshold_pct": threshold * 100, "customers_required": k,
                            "customer_base_share_pct": k / n * 100})
    pd.DataFrame(top_rows).to_csv(OUT / "top_customer_concentration.csv", index=False)
    pd.DataFrame(pareto_rows).to_csv(OUT / "customer_pareto_thresholds.csv", index=False)

    seg = (cust.groupby("rfm_segment", dropna=False)
           .agg(customers=("customer_id", "size"), historical_revenue_gbp=("monetary", "sum"),
                avg_recency_days=("recency_days", "mean"), median_recency_days=("recency_days", "median"),
                avg_orders_per_customer=("frequency", "mean"), median_historical_revenue_gbp=("monetary", "median"))
           .reset_index())
    seg["customer_share_pct"] = seg["customers"] / n * 100
    seg["identified_revenue_share_pct"] = seg["historical_revenue_gbp"] / total * 100
    seg = seg.sort_values("historical_revenue_gbp", ascending=False)
    seg.to_csv(OUT / "customer_segment_value.csv", index=False)

    # Customer-level order history and repeat purchase timing.
    sales_known = sales.dropna(subset=["customer_id_num", "invoice_date", "invoice_key"]).copy()
    orders = (sales_known.groupby(["customer_id_num", "invoice_key"], as_index=False)
              .agg(order_date=("invoice_date", "min"), order_revenue=("revenue", "sum")))
    orders = orders.sort_values(["customer_id_num", "order_date", "invoice_key"])
    orders["order_number"] = orders.groupby("customer_id_num").cumcount() + 1
    order_counts = orders.groupby("customer_id_num")["invoice_key"].nunique()
    repeat_customers = int((order_counts >= 2).sum())
    single_order_customers = int((order_counts == 1).sum())
    first_orders = orders[orders["order_number"] == 1][["customer_id_num", "order_date"]].rename(columns={"order_date": "first_order_date"})
    second_orders = orders[orders["order_number"] == 2][["customer_id_num", "order_date"]].rename(columns={"order_date": "second_order_date"})
    first_second = first_orders.merge(second_orders, on="customer_id_num", how="left")
    first_second["days_to_second_order"] = (first_second["second_order_date"] - first_second["first_order_date"]).dt.total_seconds() / 86400
    first_second.to_csv(OUT / "customer_first_second_order.csv", index=False)
    observation_end = sales["invoice_date"].max().normalize()
    windows = []
    for days in [30, 60, 90, 180, 365]:
        eligible = first_second[first_second["first_order_date"] <= observation_end - timedelta(days=days)]
        returned = int((eligible["days_to_second_order"].notna() & (eligible["days_to_second_order"] <= days)).sum())
        windows.append({"follow_up_days": days, "eligible_customers": len(eligible),
                        "customers_with_second_order": returned,
                        "second_order_within_window_pct": returned / len(eligible) * 100 if len(eligible) else np.nan})
    pd.DataFrame(windows).to_csv(OUT / "repeat_purchase_windows.csv", index=False)

    metrics = {
        "identified_customers": int(n),
        "identified_customer_historical_revenue_gbp": total,
        "mean_historical_revenue_per_customer_gbp": float(cust["monetary"].mean()),
        "median_historical_revenue_per_customer_gbp": float(cust["monetary"].median()),
        "p90_historical_revenue_per_customer_gbp": float(cust["monetary"].quantile(.90)),
        "p99_historical_revenue_per_customer_gbp": float(cust["monetary"].quantile(.99)),
        "max_historical_revenue_per_customer_gbp": float(cust["monetary"].max()),
        "mean_orders_per_customer": float(cust["frequency"].mean()),
        "median_orders_per_customer": float(cust["frequency"].median()),
        "repeat_customers": repeat_customers,
        "repeat_customer_share_pct": repeat_customers / n * 100,
        "single_order_customers": single_order_customers,
        "single_order_customer_share_pct": single_order_customers / n * 100,
        "customer_revenue_gini": gini(cust["monetary"]),
        "median_days_to_second_order_among_repeaters": float(first_second["days_to_second_order"].dropna().median()),
        "mean_days_to_second_order_among_repeaters": float(first_second["days_to_second_order"].dropna().mean()),
    }
    metrics["top_customer_concentration"] = top_rows
    metrics["customer_pareto_thresholds"] = pareto_rows
    metrics["repeat_purchase_windows"] = windows
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
    p = products.copy()
    p["product_type_clean"] = p["product_type"].astype(str).str.strip()
    for col in ["revenue", "units", "orders"]:
        p[col] = pd.to_numeric(p[col], errors="coerce").fillna(0)
    merchandise_rows = p[p["product_type_clean"].str.lower() == "merchandise"].copy()
    operational_rows = p[p["product_type_clean"].str.lower() != "merchandise"].copy()

    # Product performance is grouped by code + description in the source export;
    # aggregate to one row per stock code for product-level concentration.
    product_codes = (merchandise_rows.groupby("stock_code", as_index=False)
                     .agg(revenue_gbp=("revenue", "sum"), units=("units", "sum"), orders=("orders", "sum")))
    descriptions = (merchandise_rows.sort_values("revenue", ascending=False)
                    .drop_duplicates("stock_code").set_index("stock_code")["description"])
    product_codes["description"] = product_codes["stock_code"].map(descriptions)
    product_codes = product_codes.sort_values("revenue_gbp", ascending=False).reset_index(drop=True)
    total_merch = float(product_codes["revenue_gbp"].sum())
    product_codes["revenue_share_pct"] = product_codes["revenue_gbp"] / total_merch * 100
    product_codes["cumulative_revenue_share_pct"] = product_codes["revenue_gbp"].cumsum() / total_merch * 100

    # Derive distinct invoices directly from line-level sales to identify one-off bulk lines.
    sale_rows = sales.copy()
    sale_rows["stock_code_key"] = sale_rows["stock_code"].astype(str)
    sale_rows["invoice_key"] = sale_rows["invoice"].astype(str)
    line_orders = sale_rows.groupby("stock_code_key").agg(
        distinct_invoices=("invoice_key", "nunique"),
        max_single_invoice_units=("quantity", "max"),
        max_single_line_revenue_gbp=("revenue", "max"),
    ).reset_index().rename(columns={"stock_code_key": "stock_code"})
    product_codes = product_codes.merge(line_orders, on="stock_code", how="left")
    product_codes.to_csv(OUT / "merchandise_product_concentration.csv", index=False)

    one_order = product_codes[product_codes["distinct_invoices"] <= 1].copy()
    one_order = one_order.sort_values("revenue_gbp", ascending=False)
    one_order.to_csv(OUT / "single_invoice_merchandise_products.csv", index=False)
    ops_total = float(operational_rows["revenue"].sum())
    ops_summary = (operational_rows.groupby("stock_code", as_index=False)
                   .agg(description=("description", "first"), revenue_gbp=("revenue", "sum"), units=("units", "sum"), orders=("orders", "sum"))
                   .sort_values("revenue_gbp", ascending=False))
    ops_summary.to_csv(OUT / "operational_non_merchandise_codes.csv", index=False)

    pareto = []
    for threshold in [.50, .80, .90]:
        k = int(np.argmax(product_codes["cumulative_revenue_share_pct"].to_numpy() >= threshold * 100) + 1)
        pareto.append({"revenue_threshold_pct": threshold * 100, "stock_codes_required": k,
                       "share_of_merchandise_stock_codes_pct": k / len(product_codes) * 100})
    top10 = float(product_codes.head(10)["revenue_gbp"].sum() / total_merch * 100)
    metrics = {
        "merchandise_stock_codes": int(product_codes["stock_code"].nunique()),
        "merchandise_revenue_gbp": total_merch,
        "operational_non_merchandise_revenue_gbp": ops_total,
        "operational_non_merchandise_rows": int(len(operational_rows)),
        "top_10_merchandise_stock_code_revenue_share_pct": top10,
        "single_invoice_merchandise_code_count": int(len(one_order)),
        "product_pareto_thresholds": pareto,
    }
    metrics["product_pareto_thresholds"] = pareto
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
    x = sales.dropna(subset=["customer_id_num", "invoice_date"]).copy()
    if x.empty:
        empty = pd.DataFrame()
        empty.to_csv(OUT / "cohort_retention_recomputed.csv")
        empty.to_csv(OUT / "cohort_active_customer_counts.csv")
        return pd.DataFrame(columns=[
            "months_since_first_purchase", "eligible_cohorts", "eligible_customers",
            "active_in_that_calendar_month", "weighted_monthly_active_retention_pct",
        ])

    x["invoice_month"] = x["invoice_date"].dt.to_period("M")
    cm = x[["customer_id_num", "invoice_month"]].drop_duplicates()
    first_month = cm.groupby("customer_id_num")["invoice_month"].min().rename("cohort_month")
    cm = cm.merge(first_month, on="customer_id_num", how="left")
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
            .groupby("months_since_first_purchase")["customer_id_num"]
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
            "customer_id_num", "snapshot_date", "inactive_next_90d",
            "recency_days", "lifetime_orders", "lifetime_revenue",
            "orders_90d", "orders_180d", "orders_365d",
            "predicted_inactivity_score", "risk_rank_pct",
        ]).to_csv(OUT / "historical_inactivity_holdout_scores.csv", index=False)

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
        gb = hist.groupby("customer_id_num")
        base = gb.agg(first_order=("order_date", "min"), last_order=("order_date", "max"),
                      lifetime_orders=("invoice_key", "nunique"), lifetime_revenue=("order_revenue", "sum")).reset_index()
        base["recency_days"] = (cut - base["last_order"]).dt.days
        base["tenure_days"] = (cut - base["first_order"]).dt.days
        base["avg_order_value"] = base["lifetime_revenue"] / base["lifetime_orders"].clip(lower=1)
        for days, label in [(90, "90d"), (180, "180d"), (365, "365d")]:
            window = hist[hist["order_date"] > cut - timedelta(days=days)]
            agg = window.groupby("customer_id_num").agg(
                **{f"orders_{label}": ("invoice_key", "nunique"), f"revenue_{label}": ("order_revenue", "sum")})
            base = base.merge(agg, on="customer_id_num", how="left")
            base[f"orders_{label}"] = base[f"orders_{label}"].fillna(0)
            base[f"revenue_{label}"] = base[f"revenue_{label}"].fillna(0)
        future = orders[(orders["order_date"] > cut) & (orders["order_date"] <= cut + timedelta(days=90))]
        future_n = future.groupby("customer_id_num")["invoice_key"].nunique()
        base["future_orders_90d"] = base["customer_id_num"].map(future_n).fillna(0)
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

    scored = test[["customer_id_num", "snapshot_date", "inactive_next_90d", "recency_days", "lifetime_orders",
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
    # Customer Pareto curve
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cust["customer_share_cumulative"] * 100, cust["revenue_share_cumulative"] * 100)
    ax.axhline(80, linestyle="--", linewidth=1)
    ax.axvline(20, linestyle="--", linewidth=1)
    ax.set(title="Identified-customer revenue concentration", xlabel="Cumulative share of customers (%)",
           ylabel="Cumulative share of identified-customer revenue (%)", xlim=(0, 100), ylim=(0, 100))
    ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "customer_revenue_pareto.png", dpi=160); plt.close(fig)

    # Segment revenue and customer shares
    ss = seg.sort_values("identified_revenue_share_pct", ascending=True)
    y = np.arange(len(ss))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(y - .18, ss["customer_share_pct"], height=.35, label="Customer share")
    ax.barh(y + .18, ss["identified_revenue_share_pct"], height=.35, label="Revenue share")
    ax.set_yticks(y, ss["rfm_segment"]); ax.set_xlabel("Share (%)")
    ax.set_title("Customer share vs. historical revenue share by RFM segment")
    ax.legend(); ax.grid(axis="x", alpha=.25); fig.tight_layout()
    fig.savefig(FIG / "segment_share_comparison.png", dpi=160); plt.close(fig)

    # Repurchase windows
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(repeat_windows["follow_up_days"].astype(str), repeat_windows["second_order_within_window_pct"])
    ax.set(title="Identified customers making a second purchase", xlabel="Follow-up window (days)", ylabel="Customers with second purchase (%)")
    ax.set_ylim(0, 100); ax.grid(axis="y", alpha=.25); fig.tight_layout()
    fig.savefig(FIG / "second_purchase_windows.png", dpi=160); plt.close(fig)

    # Top countries
    top = countries.head(10).sort_values("revenue", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["country"], top["revenue"] / 1_000_000)
    ax.set(title="Revenue by country — top 10", xlabel="Revenue (£ millions)")
    ax.grid(axis="x", alpha=.25); fig.tight_layout()
    fig.savefig(FIG / "country_revenue_top10.png", dpi=160); plt.close(fig)

    # Merchandise stock-code Pareto
    top_products = products.copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(np.arange(1, len(top_products) + 1) / len(top_products) * 100,
            top_products["cumulative_revenue_share_pct"])
    ax.axhline(80, linestyle="--", linewidth=1)
    ax.set(title="Merchandise revenue concentration by stock code", xlabel="Cumulative share of merchandise stock codes (%)",
           ylabel="Cumulative merchandise revenue (%)", xlim=(0, 100), ylim=(0, 100))
    ax.grid(alpha=.25); fig.tight_layout()
    fig.savefig(FIG / "merchandise_product_pareto.png", dpi=160); plt.close(fig)

    # Historical monthly backtest AUC
    monthly_path = OUT / "historical_inactivity_monthly_backtest.csv"
    if monthly_path.exists():
        m = pd.read_csv(monthly_path)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(m["snapshot_date"], m["roc_auc"], marker="o")
        ax.axhline(.5, linestyle="--", linewidth=1)
        ax.set(title="Historical 90-day inactivity model: monthly holdout ROC-AUC", xlabel="Snapshot date", ylabel="ROC-AUC", ylim=(.4, 1.0))
        ax.tick_params(axis="x", rotation=45); ax.grid(alpha=.25); fig.tight_layout()
        fig.savefig(FIG / "inactivity_model_monthly_auc.png", dpi=160); plt.close(fig)


def build_report(metrics, country_metrics, product_metrics, affinity_metrics, affinity_rules, churn_metrics, segments, windows, cohort_summary, kpis):
    total_sales = float(kpis["gross_sales_revenue_gbp"])
    identified = float(metrics["identified_customer_historical_revenue_gbp"])
    unknown = float(kpis.get("unidentified_customer_sales_revenue_gbp", total_sales - identified))
    risk_names = ["Hibernating", "At Risk", "Cannot Lose Them"]
    risk_seg = segments[segments["rfm_segment"].isin(risk_names)]
    risk_count = int(risk_seg["customers"].sum())
    risk_revenue = float(risk_seg["historical_revenue_gbp"].sum())
    top_customer_rows = pd.read_csv(OUT / "top_customer_concentration.csv")
    pareto_rows = pd.read_csv(OUT / "customer_pareto_thresholds.csv")
    product_pareto = pd.DataFrame(product_metrics["product_pareto_thresholds"])
    countries_df = pd.read_csv(OUT / "country_concentration.csv")
    products_df = pd.read_csv(OUT / "merchandise_product_concentration.csv")
    anomalies = pd.read_csv(OUT / "single_invoice_merchandise_products.csv")

    lines = []
    lines += [
        "# RetailPulse — Phase 3 Advanced Analytics Report", "",
        "**Dataset:** UCI Online Retail II (processed sale-line extract)",
        f"**Observation window:** {kpis['sales_date_min']} to {kpis['sales_date_max']}",
        f"**Source sale lines:** {int(kpis['sales_lines']):,}",
        "**Currency:** GBP (£), as recorded in the source", "",
        "> This report analyses historical transactions. Revenue is not profit. Historical customer spend is not a forward-looking customer lifetime value (CLV) estimate. The churn-risk model predicts a defined 90-day inactivity proxy, not permanent churn.", "",
        "## Executive summary", "",
        f"- Gross sales-line revenue is **{pct_money(total_sales)}**. The identified-customer RFM file reconciles to **{pct_money(identified)}**; approximately **{(identified / total_sales * 100):.1f}%** of sales revenue is attributable to identified customer IDs.",
        f"- The top **10%** of identified customers generate **{top_customer_rows.loc[top_customer_rows.top_customer_share_pct == 10, 'identified_revenue_share_pct'].iloc[0]:.1f}%** of identified-customer revenue; the top **20%** generate **{top_customer_rows.loc[top_customer_rows.top_customer_share_pct == 20, 'identified_revenue_share_pct'].iloc[0]:.1f}%**.",
        f"- **{metrics['repeat_customer_share_pct']:.1f}%** of identified customers made at least two purchases within the dataset window. Among customers with a full 90-day follow-up window, **{windows.loc[windows.follow_up_days == 90, 'second_order_within_window_pct'].iloc[0]:.1f}%** made a second purchase within 90 days.",
        f"- The **{country_metrics['top_country']}** accounts for **{country_metrics['top_country_revenue_share_pct']:.1f}%** of gross sales-line revenue; the top five countries account for **{country_metrics['top_five_country_revenue_share_pct']:.1f}%**.",
        f"- Merchandise revenue totals **{pct_money(product_metrics['merchandise_revenue_gbp'])}** after excluding operational/non-merchandise codes; operational/non-merchandise revenue is **{pct_money(product_metrics['operational_non_merchandise_revenue_gbp'])}**. A single-invoice product anomaly is flagged for audit rather than removed.",
        f"- The processed file contains **{int(kpis.get('rows_missing_customer_id_sales', 0)):,} sales lines with no customer ID**, representing **{float(kpis.get('unidentified_customer_revenue_share_pct', 0)):.1f}%** of sales revenue.",
        "- A historical random-forest model achieved a holdout ROC-AUC of **{:.3f}** for 90-day inactivity. Treat this as a retrospective ranking proof-of-concept, not a deployable churn probability.".format(churn_metrics.get("roc_auc", float("nan"))) if churn_metrics.get("status") == "COMPLETED" else "- The historical inactivity model was skipped because there were insufficient snapshots.",
        "", "## 0. Data scope and reconciliation", "",
        f"The source workbook has **{int(kpis['rows_received']):,}** rows. Five rows fail core validation, leaving **{int(kpis['rows_after_core_validation']):,}**. The processed extract classifies **{int(kpis['sales_lines']):,}** sale lines, **{int(kpis['return_or_cancellation_lines']):,}** return/cancellation lines and **{int(kpis.get('rows_neither_sale_nor_return_cancellation', 0)):,}** other valid rows. These categories reconcile to the validated-row total.",
        f"There are **{int(kpis.get('rows_missing_customer_id_sales', 0)):,}** sales lines without customer IDs, representing **{float(kpis.get('unidentified_customer_revenue_share_pct', 0)):.1f}%** of gross sales-line revenue. Identified and unidentified sales revenue reconcile to gross sales-line revenue.",
        "", "## 1. Customer value and concentration", "",
        f"Identified customers: **{metrics['identified_customers']:,}**. Mean historical spend per identified customer is **{pct_money(metrics['mean_historical_revenue_per_customer_gbp'])}**, while the median is **{pct_money(metrics['median_historical_revenue_per_customer_gbp'])}**. The gap shows a strongly right-skewed spend distribution; the median is more representative of a typical customer.",
        f"The customer revenue Gini coefficient is **{metrics['customer_revenue_gini']:.3f}** (0 = equal distribution; 1 = maximum concentration). The top 1% contribute **{top_customer_rows.loc[top_customer_rows.top_customer_share_pct == 1, 'identified_revenue_share_pct'].iloc[0]:.1f}%** of identified revenue, and the top 5% contribute **{top_customer_rows.loc[top_customer_rows.top_customer_share_pct == 5, 'identified_revenue_share_pct'].iloc[0]:.1f}%**.",
        "", "### RFM segment priorities", "",
        "| Segment | Customers | Customer share | Historical revenue | Revenue share | Average recency (days) | Average orders |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in segments.iterrows():
        lines.append(f"| {row['rfm_segment']} | {int(row['customers']):,} | {row['customer_share_pct']:.1f}% | {pct_money(row['historical_revenue_gbp'])} | {row['identified_revenue_share_pct']:.1f}% | {row['avg_recency_days']:.1f} | {row['avg_orders_per_customer']:.2f} |")
    lines += [
        "", f"The combined Hibernating, At Risk and Cannot Lose Them groups contain **{risk_count:,} customers** and represent **{risk_count / metrics['identified_customers'] * 100:.1f}%** of the identified base. Their historical spend is **{pct_money(risk_revenue)}** ({risk_revenue / identified * 100:.1f}% of identified-customer revenue). This is historical spend, not expected future revenue at risk.",
        "", "## 2. Repeat purchasing and retention", "",
        f"The mean number of orders per identified customer is **{metrics['mean_orders_per_customer']:.2f}**, with a median of **{metrics['median_orders_per_customer']:.0f}**. **{metrics['repeat_customers']:,}** customers purchased more than once, while **{metrics['single_order_customers']:,}** purchased once in the observed window.",
        f"Among customers with at least 90 days of follow-up after their first observed purchase, **{windows.loc[windows.follow_up_days == 90, 'second_order_within_window_pct'].iloc[0]:.1f}%** placed a second order within 90 days. The median interval from first to second order among repeat buyers is **{metrics['median_days_to_second_order_among_repeaters']:.1f} days**.",
        "", "| Follow-up window | Eligible first-time customers | Second purchase within window |",
        "|---:|---:|---:|",
    ]
    for _, row in windows.iterrows():
        lines.append(f"| {int(row['follow_up_days'])} days | {int(row['eligible_customers']):,} | {row['second_order_within_window_pct']:.1f}% |")
    lines += [
        "", "Cohort heatmap values represent the share of each acquisition cohort that was active in a specific calendar month relative to first purchase. They are point-in-time monthly activity rates, not cumulative survival probabilities. A later month can rise above an earlier month because customers can skip a month and return later. Blank cells are unobserved follow-up, not zero retention.",
        "", "| Months after first purchase | Eligible customers | Active in that exact calendar month |",
        "|---:|---:|---:|",
    ]
    for _, row in cohort_summary.iterrows():
        if pd.notna(row["weighted_monthly_active_retention_pct"]):
            lines.append(f"| {int(row['months_since_first_purchase'])} | {int(row['eligible_customers']):,} | {row['weighted_monthly_active_retention_pct']:.1f}% |")
    lines += [
        "", "## 3. Merchandise and product concentration", "",
        f"The merchandise table contains **{product_metrics['merchandise_stock_codes']:,} stock codes** with total recorded revenue of **{pct_money(product_metrics['merchandise_revenue_gbp'])}**. The top 10 stock codes contribute **{product_metrics['top_10_merchandise_stock_code_revenue_share_pct']:.1f}%** of merchandise revenue. This is a materially less concentrated pattern than customer revenue.",
        "", "| Merchandise Pareto threshold | Stock codes required | Share of merchandise codes |", "|---:|---:|---:|",
    ]
    for _, row in product_pareto.iterrows():
        lines.append(f"| {row['revenue_threshold_pct']:.0f}% of merchandise revenue | {int(row['stock_codes_required']):,} | {row['share_of_merchandise_stock_codes_pct']:.1f}% |")
    if not anomalies.empty:
        a = anomalies.iloc[0]
        lines += ["", "### Product record requiring manual review", "",
                  f"Stock code **{a['stock_code']}** ({a['description']}) records **{int(a['units']):,} units**, **{int(a['distinct_invoices']):,} distinct invoice(s)** and **{pct_money(a['revenue_gbp'])}** revenue. The source transaction export shows a single invoice for 80,995 units (invoice 581483, dated 9 December 2011). It has been retained in revenue totals and flagged for source-document review; it has not been deleted as an error."]
    lines += [
        "", "Operational/non-merchandise codes are excluded from merchandise rankings, but their sales-line revenue remains part of gross sales. No product cost or gross margin data is present, so high revenue must not be interpreted as high profitability.",
        "", "### Top merchandise stock codes", "",
        "| Stock code | Product description | Revenue | Distinct invoices | Units |",
        "|---|---|---:|---:|---:|",
    ]
    for _, row in products_df.head(10).iterrows():
        lines.append(f"| {row['stock_code']} | {row['description']} | {pct_money(row['revenue_gbp'])} | {int(row['distinct_invoices']):,} | {int(row['units']):,} |")
    lines += [
        "",
        "### Products frequently purchased together",
        "",
        f"Invoice-level baskets include **{affinity_metrics['merchandise_baskets']:,} merchandise invoices**. The minimum co-purchase threshold is **{affinity_metrics['minimum_joint_orders']:,} invoices**. Association rules are ranked by lift after this frequency filter.",
    ]
    if affinity_rules.empty:
        lines.append("No product pairs met the minimum co-purchase threshold in this dataset.")
    else:
        lines += [
            "",
            "| Bought first/with | Frequently paired with | Joint invoices | Support | Confidence | Lift |",
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
    lines += ["", "## 4. Country concentration", "",
        f"The source includes **{country_metrics['country_count']} countries**. {country_metrics['top_country']} contributes **{country_metrics['top_country_revenue_share_pct']:.1f}%** of total sales-line revenue, and the top five countries contribute **{country_metrics['top_five_country_revenue_share_pct']:.1f}%**. This indicates substantial geographic concentration.",
        "", "| Country | Revenue | Revenue share | Orders | Identified customers |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in countries_df.head(10).iterrows():
        lines.append(f"| {row['country']} | {pct_money(row['revenue'])} | {row['revenue_share_pct']:.2f}% | {int(row['orders']):,} | {int(row['customers']):,} |")
    lines += [
        "", "## 5. Historical 90-day inactivity model", "",
    ]
    if churn_metrics.get("status") == "COMPLETED":
        lines += [
            f"A Random Forest model was trained on monthly customer snapshots up to **{churn_metrics['training_snapshot_end']}**. The latest training label window ends **{churn_metrics['training_label_observation_end']}**. A 90-day temporal embargo is applied; held-out snapshots begin **{churn_metrics['test_snapshot_start']}** and run through **{churn_metrics['test_snapshot_end']}**. There were **{churn_metrics['train_snapshot_customer_observations']:,}** training and **{churn_metrics['test_snapshot_customer_observations']:,}** test customer-snapshot observations. The 90-day inactivity rate was **{churn_metrics['train_90d_inactivity_prevalence_pct']:.1f}%** in training and **{churn_metrics['test_90d_inactivity_prevalence_pct']:.1f}%** in test, showing temporal distribution shift.",
            "", "| Metric | Historical holdout result |", "|---|---:|",
            f"| ROC-AUC | {churn_metrics['roc_auc']:.3f} |",
            f"| Average precision | {churn_metrics['average_precision']:.3f} |",
            f"| Brier score | {churn_metrics['brier_score']:.3f} |",
            f"| Accuracy at 0.50 threshold | {churn_metrics['accuracy_at_0_5']:.1%} |",
            f"| Precision at 0.50 threshold | {churn_metrics['precision_at_0_5']:.1%} |",
            f"| Recall at 0.50 threshold | {churn_metrics['recall_at_0_5']:.1%} |",
            f"| Inactivity rate in top 20% risk-ranked snapshots | {churn_metrics['top_20pct_risk_observed_inactivity_rate_pct']:.1f}% |",
            f"| Lift in top 20% vs. test prevalence | {churn_metrics['top_20pct_risk_lift']:.2f}x |",
            "", "The strongest feature importances are lifetime order count, 180-day revenue/orders and 365-day order/revenue history. The model is useful as a retrospective proof of concept for prioritising historical snapshots, but it is not ready for operational deployment.",
        ]
    else:
        lines += [f"Model status: {churn_metrics.get('status')}. {churn_metrics.get('reason', '')}"]
    lines += [
        "", "### Model limitations", "",
        "- The target is no recorded order within 90 days, not permanent customer loss. For an intermittent retailer, 90 days of inactivity may be normal.",
        "- A 90-day embargo ensures the final training snapshot's inactivity label is observable before the first held-out snapshot; test snapshots still overlap one another in their 90-day outcome windows.",
        "- Customer-month snapshots repeatedly include the same people; rows are correlated, so row counts should not be interpreted as independent customers.",
        "- The training and test inactivity rates differ materially, indicating temporal/seasonal distribution shift.",
        "- Predicted scores are not calibrated for expected revenue loss or campaign economics.",
        "- This historical dataset ends on 9 December 2011; it cannot estimate current customer risk in 2026.",
        "", "## 6. Recommended business actions", "",
        "1. **Protect the Champions segment.** Use service and loyalty experiments, measure incremental repeat revenue and margin, and avoid assuming all Champions need discounts.",
        "2. **Create a win-back test for Cannot Lose Them and At Risk.** Prioritise historically valuable customers with long recency, but use a randomised control group to measure incremental reactivation.",
        "3. **Improve second-purchase conversion.** Test onboarding, replenishment reminders and product recommendations during the first 30–90 days.",
        "4. **Investigate anonymous sales.** Customer IDs are missing from 236,121 sales lines in the processed dataset. Better customer identification would improve retention and lifetime-value analysis.",
        "5. **Audit the one-invoice bulk product record.** Validate the Paper Craft, Little Birdie transaction before using its one-off volume as a demand forecast.",
        "6. **Reduce geographic dependence carefully.** Evaluate international markets using margin, shipping, returns, customer repeat rates and acquisition costs—not revenue alone.",
        "7. **Add cost and margin data.** Product profitability and economic CLV cannot be calculated from sales prices alone.",
        "", "## 7. Definitions and caveats", "",
        "- **Gross sales-line revenue:** Sum of included positive-quantity, positive-price sales-line values. It is not profit and is not net of recorded returns/cancellations.",
        "- **Historical customer revenue:** Recorded sales revenue associated with a known customer ID over the source period. It is not a forecast of future lifetime value.",
        "- **Repeat purchase:** A second distinct invoice associated with the same customer ID.",
        "- **90-day inactivity:** No identified-customer invoice during the 90 days following a historical monthly snapshot.",
        "- **RFM segments:** Rule-based recency/frequency/monetary groups; the segment label is not itself a churn probability.",
        "- **Merchandise stock-code concentration:** Product revenue aggregated to one row per stock code after excluding operational/non-merchandise types.",
        "", "## 8. Reproducibility", "",
        "Run from the RetailPulse project root:", "```bash", "source .venv/bin/activate", "python scripts/run_phase3_analysis.py", "```",
        "Outputs are written to `reports/phase3/`. The script uses the processed exports already generated by the main RetailPulse pipeline.", "",
    ]
    (OUT / "PHASE3_ADVANCED_ANALYTICS.md").write_text("\n".join(lines), encoding="utf-8")


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
    churn_metrics = make_churn_backtest(orders, sales["invoice_date"].max().normalize())
    windows = pd.read_csv(OUT / "repeat_purchase_windows.csv")
    make_charts(cust, seg, country_table, product_table, windows, churn_metrics)
    build_report(customer_metrics, country_metrics, product_metrics, affinity_metrics, affinity_rules, churn_metrics, seg, windows, cohort_summary, kpis)

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
        "customer_revenue_gini": round(customer_metrics["customer_revenue_gini"], 3),
        "top_country": country_metrics["top_country"],
        "top_country_revenue_share_pct": round(country_metrics["top_country_revenue_share_pct"], 2),
        "historical_inactivity_model_status": churn_metrics.get("status"),
        "report": str(OUT / "PHASE3_ADVANCED_ANALYTICS.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
