from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retailpulse.insights import generate_business_insights


def _base_inputs():
    return {
        "kpis": {"unidentified_customer_revenue_share_pct": 15.4},
        "customer_metrics": {
            "top_customer_concentration": [
                {"top_customer_share_pct": 20.0, "customers": 100, "identified_revenue_share_pct": 62.0}
            ]
        },
        "country_metrics": {"top_country": "United Kingdom", "top_country_revenue_share_pct": 85.2},
        "product_metrics": {
            "merchandise_stock_codes": 2500,
            "top_10_merchandise_stock_code_revenue_share_pct": 68.0,
        },
        "repeat_purchase_windows": [
            {"follow_up_days": 90, "eligible_customers": 4000, "second_order_within_window_pct": 32.0}
        ],
        "affinity_rules": [
            {
                "antecedent_stock_code": "A",
                "antecedent_description": "Alpha",
                "consequent_stock_code": "B",
                "consequent_description": "Beta",
                "joint_orders": 250,
                "support_pct": 2.5,
                "confidence_pct": 45.0,
                "lift": 1.8,
            }
        ],
    }


def test_rules_generate_deterministic_evidence_backed_business_insights():
    kwargs = _base_inputs()
    first = generate_business_insights(**kwargs)
    second = generate_business_insights(**kwargs)

    assert first == second
    assert {item["insight_id"] for item in first} == {
        "customer_identity_gap",
        "geographic_concentration",
        "customer_revenue_concentration",
        "second_purchase_conversion",
        "product_cross_sell_candidate",
        "merchandise_assortment_concentration",
    }
    assert all(item["evidence"] and item["trigger_rule"] and item["guardrail"] for item in first)
    assert [item["priority"] for item in first] == ["High", "High", "Medium", "Medium", "Medium", "Medium"]


def test_rules_do_not_trigger_on_missing_or_non_finite_metrics():
    kwargs = {
        "kpis": {"unidentified_customer_revenue_share_pct": float("nan")},
        "customer_metrics": {"top_customer_concentration": []},
        "country_metrics": {"top_country": None, "top_country_revenue_share_pct": None},
        "product_metrics": {"merchandise_stock_codes": 0, "top_10_merchandise_stock_code_revenue_share_pct": float("nan")},
        "repeat_purchase_windows": [],
        "affinity_rules": [],
    }

    assert generate_business_insights(**kwargs) == []


def test_repeat_purchase_rule_requires_sufficient_eligible_customers():
    kwargs = _base_inputs()
    kwargs["repeat_purchase_windows"] = [
        {"follow_up_days": 90, "eligible_customers": 19, "second_order_within_window_pct": 5.0}
    ]
    insights = generate_business_insights(**kwargs)

    assert "second_purchase_conversion" not in {item["insight_id"] for item in insights}


def test_affinity_rule_requires_both_frequency_and_lift_thresholds():
    kwargs = _base_inputs()
    kwargs["affinity_rules"] = [
        {"antecedent_stock_code": "A", "consequent_stock_code": "B", "joint_orders": 19, "lift": 9.0}
    ]
    insights = generate_business_insights(**kwargs)

    assert "product_cross_sell_candidate" not in {item["insight_id"] for item in insights}
