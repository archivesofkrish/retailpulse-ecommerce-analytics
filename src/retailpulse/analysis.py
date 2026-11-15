"""Core, testable analytics transformations for RetailPulse."""
from __future__ import annotations

from pathlib import Path
import json
import re

import numpy as np
import pandas as pd

COLUMN_ALIASES = {
    "invoice": ["invoice", "invoiceno", "invoice no", "invoice_no"],
    "stock_code": ["stockcode", "stock code", "stock_code"],
    "description": ["description", "product description"],
    "quantity": ["quantity", "qty"],
    "invoice_date": ["invoicedate", "invoice date", "invoice_date"],
    "unit_price": ["unitprice", "unit price", "price", "unit_price"],
    "customer_id": ["customerid", "customer id", "customer_id"],
    "country": ["country"],
}
REQUIRED_COLUMNS = {"invoice", "stock_code", "quantity", "invoice_date", "unit_price", "country"}

# Stock codes used by the source retailer for fees, adjustments, samples, and
# other operational lines rather than ordinary merchandise. Keep source-code
# case distinctions (for example, M and m) because they occur separately.
NON_MERCHANDISE_STOCK_CODES = {
    "M", "m", "DOT", "POST", "AMAZONFEE", "C2", "B",
    "ADJUST", "ADJUST2", "BANK CHARGES", "D", "S", "PADS",
}


def _normalise_header(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def read_source(path: str | Path) -> pd.DataFrame:
    """Read a CSV or all sheets of an Excel workbook."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None)
        frames = [frame.assign(_source_sheet=name) for name, frame in sheets.items() if frame is not None and not frame.empty]
        if not frames:
            raise ValueError("The workbook contains no non-empty worksheets.")
        return pd.concat(frames, ignore_index=True, sort=False)
    raise ValueError(f"Unsupported file type: {suffix}. Use CSV or Excel.")


def _normalise_customer_id(value: object) -> object:
    """Normalise customer identifiers without collapsing zero-padded string IDs."""
    if pd.isna(value) or isinstance(value, (bool, np.bool_)):
        return pd.NA
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        return str(int(numeric)) if np.isfinite(numeric) and numeric.is_integer() else pd.NA

    text = str(value).strip()
    if text.casefold() in {"", "nan", "none", "null", "<na>", "nat", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        return pd.NA
    # Keep integer strings exactly as supplied (for example, "00123").
    if re.fullmatch(r"[+-]?[0-9]+", text):
        return text
    numeric_pattern = r"[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?"
    if re.fullmatch(numeric_pattern, text):
        numeric = float(text)
        return str(int(numeric)) if np.isfinite(numeric) and numeric.is_integer() else pd.NA
    return text


def standardise_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """Map source headers to a stable schema and reject ambiguous aliases."""
    out = raw.copy()
    lookup: dict[str, list[object]] = {}
    for column in out.columns:
        lookup.setdefault(_normalise_header(column), []).append(column)

    duplicate_headers = [key for key, columns in lookup.items() if len(columns) > 1]
    if duplicate_headers:
        raise ValueError(f"Ambiguous source headers after normalisation: {sorted(duplicate_headers)}")

    rename = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        matches = [lookup[alias][0] for alias in aliases if alias in lookup]
        if len(matches) > 1:
            raise ValueError(
                f"Multiple source columns map to '{canonical}': {matches}. "
                "Keep one source column or resolve the ambiguity before ingestion."
            )
        if matches:
            rename[matches[0]] = canonical

    out = out.rename(columns=rename)
    missing = sorted(REQUIRED_COLUMNS - set(out.columns))
    if missing:
        raise ValueError(f"Missing required columns after standardisation: {missing}. Found: {list(out.columns)}")
    if "description" not in out:
        out["description"] = "Unknown product"
    if "customer_id" not in out:
        out["customer_id"] = pd.NA
    return out


def prepare_transactions(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean input and add row classifications and line values.

    Customer IDs are optional for sales-level reporting. They are required only
    for customer-level analysis. Cancellations and negative-quantity rows are
    excluded from positive sales, but preserved in the returned dataframe for
    a transparent return/cancellation summary.
    """
    df = standardise_columns(raw)
    stats = {"rows_received": int(len(df))}

    for col in ["invoice", "stock_code", "description", "country"]:
        df[col] = df[col].astype("string").str.strip()
    df["invoice"] = df["invoice"].str.upper().replace("", pd.NA)
    df["description"] = df["description"].replace({"": pd.NA}).fillna("Unknown product")
    df["country"] = df["country"].replace({"": pd.NA}).fillna("Unknown")
    df["stock_code"] = df["stock_code"].replace({"": pd.NA})

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", dayfirst=True)

    original_customer_id = df["customer_id"].copy()
    df["customer_id"] = df["customer_id"].map(_normalise_customer_id).astype("string")
    stats["rows_invalid_customer_id"] = int(
        original_customer_id.notna().sum() - df["customer_id"].notna().sum()
    )

    quantity_values = df["quantity"].to_numpy(dtype=float, na_value=np.nan)
    price_values = df["unit_price"].to_numpy(dtype=float, na_value=np.nan)
    quantity_finite = pd.Series(np.isfinite(quantity_values), index=df.index)
    price_finite = pd.Series(np.isfinite(price_values), index=df.index)
    stats["rows_non_finite_numeric_values"] = int(
        ((~quantity_finite & df["quantity"].notna()) | (~price_finite & df["unit_price"].notna())).sum()
    )

    required_valid = (
        df["invoice"].notna() & df["stock_code"].notna() & df["invoice_date"].notna()
        & quantity_finite & price_finite & df["unit_price"].ge(0)
    )
    stats["rows_dropped_invalid_core_fields"] = int((~required_valid).sum())
    df = df.loc[required_valid].copy()
    with np.errstate(over="ignore", invalid="ignore"):
        df["line_value"] = df["quantity"] * df["unit_price"]
    finite_line_value = np.isfinite(df["line_value"].to_numpy(dtype=float, na_value=np.nan))
    stats["rows_dropped_non_finite_line_value"] = int((~finite_line_value).sum())
    stats["rows_dropped_invalid_core_fields"] += stats["rows_dropped_non_finite_line_value"]
    df = df.loc[finite_line_value].copy()
    df["is_cancellation"] = df["invoice"].str.startswith("C", na=False)
    df["is_return_or_cancellation"] = df["is_cancellation"] | df["quantity"].lt(0)
    df["is_sale"] = (~df["is_return_or_cancellation"]) & df["quantity"].gt(0) & df["unit_price"].gt(0)
    df["order_month"] = df["invoice_date"].dt.to_period("M").astype(str)
    df["invoice_date_day"] = df["invoice_date"].dt.date.astype(str)

    stats["rows_after_core_validation"] = int(len(df))
    stats["sale_line_rows"] = int(df["is_sale"].sum())
    stats["return_or_cancellation_rows"] = int(df["is_return_or_cancellation"].sum())
    stats["rows_missing_customer_id"] = int(df["customer_id"].isna().sum())
    stats["rows_missing_customer_id_sales"] = int((df["is_sale"] & df["customer_id"].isna()).sum())
    stats["rows_neither_sale_nor_return_cancellation"] = int((~df["is_sale"] & ~df["is_return_or_cancellation"]).sum())
    stats["rows_zero_quantity"] = int(df["quantity"].eq(0).sum())
    stats["rows_zero_unit_price"] = int(df["unit_price"].eq(0).sum())
    stats["date_min"] = df["invoice_date"].min().isoformat() if len(df) else None
    stats["date_max"] = df["invoice_date"].max().isoformat() if len(df) else None
    return df, stats


def _quintile_score(series: pd.Series, high_is_good: bool = True) -> pd.Series:
    """Create stable 1..5 scores even when metric values contain many ties."""
    pct = series.rank(method="average", pct=True)
    score = np.ceil(pct * 5).clip(1, 5).astype(int)
    if not high_is_good:
        score = 6 - score
    return score


def build_customer_rfm(sales: pd.DataFrame) -> pd.DataFrame:
    """Build customer-level Recency, Frequency, Monetary value and segments."""
    customer_sales = sales.loc[sales["customer_id"].notna()].copy()
    if customer_sales.empty:
        return pd.DataFrame(columns=["customer_id", "recency_days", "frequency", "monetary", "R", "F", "M", "rfm_segment"])

    snapshot_date = customer_sales["invoice_date"].max().normalize() + pd.DateOffset(days=1)
    customer = customer_sales.groupby("customer_id", as_index=False).agg(
        last_purchase=("invoice_date", "max"),
        first_purchase=("invoice_date", "min"),
        frequency=("invoice", "nunique"),
        monetary=("line_value", "sum"),
        units=("quantity", "sum"),
    )
    customer["recency_days"] = (snapshot_date - customer["last_purchase"].dt.normalize()).dt.days
    customer["customer_tenure_days"] = (customer["last_purchase"].dt.normalize() - customer["first_purchase"].dt.normalize()).dt.days
    customer["R"] = _quintile_score(customer["recency_days"], high_is_good=False)
    customer["F"] = _quintile_score(customer["frequency"], high_is_good=True)
    customer["M"] = _quintile_score(customer["monetary"], high_is_good=True)

    def segment(row):
        r, f, m = int(row.R), int(row.F), int(row.M)
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        if f >= 4 and r >= 3:
            return "Loyal Customers"
        if r >= 4 and f >= 2:
            return "Potential Loyalists"
        if r >= 4 and f <= 1:
            return "New Customers"
        if r <= 2 and f >= 4 and m >= 4:
            return "Cannot Lose Them"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2:
            return "Hibernating"
        return "Needs Attention"

    customer["rfm_segment"] = customer.apply(segment, axis=1)
    customer["average_order_value"] = customer["monetary"] / customer["frequency"].replace(0, np.nan)
    return customer.sort_values(["monetary", "frequency"], ascending=False).reset_index(drop=True)


def build_cohort_retention(sales: pd.DataFrame) -> pd.DataFrame:
    """Return cohort retention with unobserved future months left as NaN.

    A zero means the month was observed and no customer returned. NaN means
    the dataset ends before that cohort could have reached that month.
    """
    known = sales.loc[sales["customer_id"].notna(), ["customer_id", "invoice", "invoice_date"]].drop_duplicates()
    if known.empty:
        return pd.DataFrame()

    known = known.copy()
    known["order_month"] = known["invoice_date"].dt.to_period("M")
    first = known.groupby("customer_id")["order_month"].min().rename("cohort_month")
    known = known.join(first, on="customer_id")
    known["cohort_index"] = (
        (known["order_month"].dt.year - known["cohort_month"].dt.year) * 12
        + (known["order_month"].dt.month - known["cohort_month"].dt.month) + 1
    ).astype(int)

    counts = known.groupby(["cohort_month", "cohort_index"])["customer_id"].nunique()
    first_month = known["cohort_month"].min()
    latest_month = known["order_month"].max()
    max_observable_index = latest_month.ordinal - first_month.ordinal + 1
    columns = [f"Month_{i}" for i in range(max_observable_index)]
    cohort_months = sorted(known["cohort_month"].unique())
    retention = pd.DataFrame(np.nan, index=[str(m) for m in cohort_months], columns=columns, dtype=float)
    retention.index.name = "cohort_month"

    for cohort_month in cohort_months:
        observable_months = latest_month.ordinal - cohort_month.ordinal + 1
        cohort_counts = counts.loc[cohort_month].reindex(range(1, observable_months + 1), fill_value=0)
        cohort_size = int(cohort_counts.loc[1])
        if cohort_size <= 0:
            continue
        retention.loc[str(cohort_month), columns[:observable_months]] = (
            cohort_counts.to_numpy(dtype=float) / cohort_size
        )

    return retention


def calculate_analytics(df: pd.DataFrame, stats: dict) -> dict[str, pd.DataFrame | dict]:
    """Calculate the core reporting tables from prepared transactions."""
    sales = df.loc[df["is_sale"]].copy()
    returns = df.loc[df["is_return_or_cancellation"]].copy()
    non_sales_non_returns = df.loc[~df["is_sale"] & ~df["is_return_or_cancellation"]].copy()
    if sales.empty:
        raise ValueError("No positive sale rows remain after validation; cannot calculate sales KPIs.")

    sales["revenue"] = sales["line_value"]
    monthly = sales.groupby("order_month", as_index=False).agg(
        revenue=("revenue", "sum"), orders=("invoice", "nunique"),
        units=("quantity", "sum"), customers=("customer_id", "nunique"),
    )
    monthly["average_order_value"] = monthly["revenue"] / monthly["orders"].replace(0, np.nan)

    products = sales.groupby(["stock_code", "description"], as_index=False).agg(
        revenue=("revenue", "sum"), units=("quantity", "sum"), orders=("invoice", "nunique"),
    ).sort_values("revenue", ascending=False)
    products["product_type"] = np.where(
        products["stock_code"].astype(str).isin(NON_MERCHANDISE_STOCK_CODES),
        "Operational / non-merchandise", "Merchandise",
    )
    merchandise_products = products.loc[products["product_type"].eq("Merchandise")].copy()
    non_merchandise_products = products.loc[products["product_type"].eq("Operational / non-merchandise")].copy()

    countries = sales.groupby("country", as_index=False).agg(
        revenue=("revenue", "sum"), orders=("invoice", "nunique"),
        customers=("customer_id", "nunique"), units=("quantity", "sum"),
    ).sort_values("revenue", ascending=False)

    rfm = build_customer_rfm(sales)
    if not rfm.empty:
        segment_summary = rfm.groupby("rfm_segment", as_index=False).agg(
            customers=("customer_id", "nunique"), monetary=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"), avg_frequency=("frequency", "mean"),
        ).sort_values("monetary", ascending=False)
    else:
        segment_summary = pd.DataFrame(columns=["rfm_segment", "customers", "monetary", "avg_recency_days", "avg_frequency"])

    retention = build_cohort_retention(sales)
    day_hour = sales.assign(weekday=sales["invoice_date"].dt.day_name(), hour=sales["invoice_date"].dt.hour)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = day_hour.groupby("weekday", as_index=False).agg(orders=("invoice", "nunique"), revenue=("revenue", "sum"))
    weekday["weekday"] = pd.Categorical(weekday["weekday"], categories=weekday_order, ordered=True)
    weekday = weekday.sort_values("weekday")
    hourly = day_hour.groupby("hour", as_index=False).agg(orders=("invoice", "nunique"), revenue=("revenue", "sum"))

    gross_revenue = float(sales["revenue"].sum())
    return_cancel_value = float(returns["line_value"].abs().sum())
    order_count = int(sales["invoice"].nunique())
    customer_count = int(sales["customer_id"].nunique())
    identified_customer_revenue = float(sales.loc[sales["customer_id"].notna(), "revenue"].sum())
    unidentified_customer_revenue = float(sales.loc[sales["customer_id"].isna(), "revenue"].sum())
    kpis = {
        **stats,
        "gross_sales_revenue_gbp": round(gross_revenue, 2),
        "recorded_return_cancellation_value_gbp": round(return_cancel_value, 2),
        "sales_orders": order_count,
        "identified_customers": customer_count,
        "identified_customer_sales_revenue_gbp": round(identified_customer_revenue, 2),
        "unidentified_customer_sales_revenue_gbp": round(unidentified_customer_revenue, 2),
        "identified_customer_revenue_share_pct": round((identified_customer_revenue / gross_revenue) * 100, 2) if gross_revenue else 0,
        "unidentified_customer_revenue_share_pct": round((unidentified_customer_revenue / gross_revenue) * 100, 2) if gross_revenue else 0,
        "operational_non_merchandise_revenue_gbp": round(float(non_merchandise_products["revenue"].sum()), 2),
        "operational_non_merchandise_revenue_share_pct": round((float(non_merchandise_products["revenue"].sum()) / gross_revenue) * 100, 2) if gross_revenue else 0,
        "merchandise_revenue_gbp": round(float(merchandise_products["revenue"].sum()), 2),
        "operational_non_merchandise_stock_codes": int(non_merchandise_products["stock_code"].nunique()),
        "unique_products": int(sales["stock_code"].nunique()),
        "countries": int(sales["country"].nunique()),
        "average_order_value_gbp": round(gross_revenue / order_count, 2) if order_count else 0,
        "average_revenue_per_identified_customer_gbp": round(identified_customer_revenue / customer_count, 2) if customer_count else 0,
        "sales_date_min": sales["invoice_date"].min().date().isoformat(),
        "sales_date_max": sales["invoice_date"].max().date().isoformat(),
        "return_or_cancellation_lines": int(len(returns)),
        "sales_lines": int(len(sales)),
    }
    return {
        "sales": sales, "returns": returns, "non_sales_non_returns": non_sales_non_returns,
        "monthly": monthly, "products": products,
        "merchandise_products": merchandise_products, "non_merchandise_products": non_merchandise_products,
        "countries": countries, "rfm": rfm, "segment_summary": segment_summary,
        "cohort_retention": retention, "weekday": weekday, "hourly": hourly, "kpis": kpis,
    }


def run_pipeline(input_path: str | Path, output_dir: str | Path) -> dict:
    """Run the complete data pipeline and persist reusable analysis outputs."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = read_source(input_path)
    prepared, stats = prepare_transactions(raw)
    result = calculate_analytics(prepared, stats)

    exports = {
        "sales_lines.csv": result["sales"],
        "return_cancellation_lines.csv": result["returns"],
        "excluded_non_sale_non_return_lines.csv": result["non_sales_non_returns"],
        "monthly_sales.csv": result["monthly"],
        "product_performance.csv": result["products"],
        "country_performance.csv": result["countries"],
        "customer_rfm.csv": result["rfm"],
        "rfm_segment_summary.csv": result["segment_summary"],
        "cohort_retention.csv": result["cohort_retention"],
        "weekday_performance.csv": result["weekday"],
        "hourly_performance.csv": result["hourly"],
    }
    for name, frame in exports.items():
        frame.to_csv(output_dir / name, index=(Path(name).stem == "cohort_retention"))
    (output_dir / "kpis.json").write_text(json.dumps(result["kpis"], indent=2), encoding="utf-8")
    return result
