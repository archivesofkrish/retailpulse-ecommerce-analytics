"""Historical customer-cohort revenue yield and retention metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

VALUE_PANEL_COLUMNS = [
    "cohort_month",
    "activity_month",
    "age_month",
    "cohort_customers",
    "active_customers",
    "retention_pct",
    "observed_revenue_gbp",
    "revenue_per_acquired_customer_gbp",
    "cumulative_revenue_per_acquired_customer_gbp",
    "revenue_per_active_customer_gbp",
    "is_partial_period",
    "observation_end_date",
]


def build_customer_value_panel(sales: pd.DataFrame) -> pd.DataFrame:
    """Build a right-censored cohort panel using observed historical gross revenue.

    A customer's cohort is the calendar month of their first identified invoice.
    Revenue yield always uses the original cohort size as its denominator.
    Future periods beyond the source observation window are not imputed.
    """
    if not isinstance(sales, pd.DataFrame):
        raise ValueError("sales must be a pandas DataFrame")
    customer_column = (
        "customer_id_key" if "customer_id_key" in sales.columns else "customer_id"
    )
    invoice_column = "invoice_key" if "invoice_key" in sales.columns else "invoice"
    required = {"invoice_date", "revenue", customer_column, invoice_column}
    if not required.issubset(sales.columns):
        return pd.DataFrame(columns=VALUE_PANEL_COLUMNS)

    work = pd.DataFrame({
        "customer_id": sales[customer_column].astype("string").str.strip(),
        "invoice_key": sales[invoice_column].astype("string").str.strip(),
        "invoice_date": pd.to_datetime(sales["invoice_date"], errors="coerce"),
        "revenue": pd.to_numeric(sales["revenue"], errors="coerce"),
    })
    work["customer_id"] = work["customer_id"].mask(
        work["customer_id"].isna() | work["customer_id"].eq(""), pd.NA
    )
    work["invoice_key"] = work["invoice_key"].mask(
        work["invoice_key"].isna() | work["invoice_key"].eq(""), pd.NA
    )
    numeric = work["revenue"].to_numpy(dtype=float, na_value=np.nan)
    valid = (
        work["customer_id"].notna()
        & work["invoice_key"].notna()
        & work["invoice_date"].notna()
        & np.isfinite(numeric)
    )
    work = work.loc[valid].copy()
    if work.empty:
        return pd.DataFrame(columns=VALUE_PANEL_COLUMNS)

    orders = (
        work.groupby(["customer_id", "invoice_key"], as_index=False)
        .agg(order_date=("invoice_date", "min"), order_revenue=("revenue", "sum"))
    )
    orders = orders.loc[
        np.isfinite(orders["order_revenue"].to_numpy(dtype=float))
    ].copy()
    if orders.empty:
        return pd.DataFrame(columns=VALUE_PANEL_COLUMNS)

    orders["order_month"] = orders["order_date"].dt.to_period("M")
    first_month = (
        orders.groupby("customer_id")["order_month"].min().rename("cohort_period")
    )
    orders = orders.merge(first_month, on="customer_id", how="left")
    orders["age_month"] = (
        (orders["order_month"].dt.year - orders["cohort_period"].dt.year) * 12
        + orders["order_month"].dt.month
        - orders["cohort_period"].dt.month
    ).astype(int)

    cohort_sizes = orders.groupby("cohort_period")["customer_id"].nunique().sort_index()
    activity = (
        orders.groupby(["cohort_period", "age_month"])
        .agg(
            active_customers=("customer_id", "nunique"),
            observed_revenue_gbp=("order_revenue", "sum"),
        )
        .to_dict("index")
    )
    end_month = orders["order_month"].max()
    observation_end = orders["order_date"].max().normalize()
    partial_final_month = observation_end.day < observation_end.days_in_month

    rows = []
    for cohort_period, cohort_size in cohort_sizes.items():
        maximum_age = end_month.ordinal - cohort_period.ordinal
        cumulative_revenue = 0.0
        for age_month in range(maximum_age + 1):
            activity_month = cohort_period + age_month
            observed = activity.get(
                (cohort_period, age_month),
                {"active_customers": 0, "observed_revenue_gbp": 0.0},
            )
            active_customers = int(observed["active_customers"])
            monthly_revenue = float(observed["observed_revenue_gbp"])
            cumulative_revenue += monthly_revenue
            rows.append({
                "cohort_month": str(cohort_period),
                "activity_month": str(activity_month),
                "age_month": age_month,
                "cohort_customers": int(cohort_size),
                "active_customers": active_customers,
                "retention_pct": active_customers / cohort_size * 100,
                "observed_revenue_gbp": monthly_revenue,
                "revenue_per_acquired_customer_gbp": monthly_revenue / cohort_size,
                "cumulative_revenue_per_acquired_customer_gbp": (
                    cumulative_revenue / cohort_size
                ),
                "revenue_per_active_customer_gbp": (
                    monthly_revenue / active_customers if active_customers else 0.0
                ),
                "is_partial_period": bool(
                    activity_month == end_month and partial_final_month
                ),
                "observation_end_date": observation_end.date().isoformat(),
            })

    return pd.DataFrame(rows, columns=VALUE_PANEL_COLUMNS)
