import pandas as pd

from retailpulse.value import build_customer_value_panel


def _sales(last_date: str = "2020-02-28") -> pd.DataFrame:
    return pd.DataFrame([
        {"customer_id_key": "A", "invoice_key": "A-1", "invoice_date": "2020-01-03", "revenue": 60.0},
        {"customer_id_key": "A", "invoice_key": "A-1", "invoice_date": "2020-01-03", "revenue": 40.0},
        {"customer_id_key": "B", "invoice_key": "B-1", "invoice_date": "2020-01-20", "revenue": 100.0},
        {"customer_id_key": "A", "invoice_key": "A-2", "invoice_date": "2020-02-10", "revenue": 50.0},
        {"customer_id_key": "C", "invoice_key": "C-1", "invoice_date": last_date, "revenue": 80.0},
    ])


def test_cohort_value_aggregates_invoice_lines_and_tracks_cumulative_value():
    panel = build_customer_value_panel(_sales())
    january_start = panel.loc[
        panel["cohort_month"].eq("2020-01") & panel["age_month"].eq(0)
    ].iloc[0]
    january_followup = panel.loc[
        panel["cohort_month"].eq("2020-01") & panel["age_month"].eq(1)
    ].iloc[0]

    assert january_start["cohort_customers"] == 2
    assert january_start["active_customers"] == 2
    assert january_start["retention_pct"] == 100.0
    assert january_start["observed_revenue_gbp"] == 200.0
    assert january_start["revenue_per_acquired_customer_gbp"] == 100.0
    assert january_followup["active_customers"] == 1
    assert january_followup["retention_pct"] == 50.0
    assert january_followup["revenue_per_acquired_customer_gbp"] == 25.0
    assert january_followup["cumulative_revenue_per_acquired_customer_gbp"] == 125.0
    assert january_followup["revenue_per_active_customer_gbp"] == 50.0


def test_last_calendar_month_is_flagged_partial_when_observation_ends_early():
    panel = build_customer_value_panel(_sales("2020-02-09"))
    february = panel.loc[panel["activity_month"].eq("2020-02")]
    assert not february.empty
    assert february["is_partial_period"].all()


def test_fully_observed_final_calendar_month_is_not_flagged_partial():
    panel = build_customer_value_panel(_sales("2020-02-29"))
    february = panel.loc[panel["activity_month"].eq("2020-02")]
    assert not february["is_partial_period"].any()


def test_customer_value_panel_handles_missing_customer_identifiers():
    sales = pd.DataFrame([
        {"customer_id_key": None, "invoice_key": "A-1", "invoice_date": "2020-01-01", "revenue": 10.0},
        {"customer_id_key": " ", "invoice_key": "B-1", "invoice_date": "2020-01-02", "revenue": 20.0},
    ])
    panel = build_customer_value_panel(sales)
    assert panel.empty
    assert "cumulative_revenue_per_acquired_customer_gbp" in panel.columns


def test_customer_value_panel_returns_schema_for_empty_dimensions():
    panel = build_customer_value_panel(pd.DataFrame(columns=[
        "customer_id_key", "invoice_key", "invoice_date", "revenue"
    ]))
    assert panel.empty
    assert list(panel.columns)[0] == "cohort_month"


def test_customer_value_panel_preserves_opaque_customer_ids():
    sales = pd.DataFrame([
        {"customer_id_key": "00123", "invoice_key": "A-1", "invoice_date": "2020-01-01", "revenue": 10.0},
        {"customer_id_key": "123", "invoice_key": "B-1", "invoice_date": "2020-01-02", "revenue": 20.0},
    ])
    panel = build_customer_value_panel(sales)
    cohort = panel.loc[panel["age_month"].eq(0)].iloc[0]
    assert cohort["cohort_customers"] == 2
