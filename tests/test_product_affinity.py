from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import scripts.run_phase3_analysis as phase3


def test_product_affinity_uses_unique_merchandise_skus_per_invoice(tmp_path, monkeypatch):
    monkeypatch.setattr(phase3, "OUT", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

    rows = []
    for invoice in range(1, 6):
        rows.extend([
            {"invoice_key": str(invoice), "stock_code_key": "A"},
            {"invoice_key": str(invoice), "stock_code_key": "A"},  # duplicate line is one basket item
            {"invoice_key": str(invoice), "stock_code_key": "B"},
        ])
    rows.extend([
        {"invoice_key": "6", "stock_code_key": "A"},
        {"invoice_key": "7", "stock_code_key": "C"},
        {"invoice_key": "1", "stock_code_key": "POST"},  # operational code is excluded
        {"invoice_key": "8", "stock_code_key": "POST"},  # no merchandise item, not a merchandise basket
    ])
    sales = pd.DataFrame(rows)
    products = pd.DataFrame([
        {"stock_code": "A", "description": "Alpha", "product_type": "Merchandise", "revenue": 100.0},
        {"stock_code": "B", "description": "Beta", "product_type": "Merchandise", "revenue": 80.0},
        {"stock_code": "C", "description": "Gamma", "product_type": "Merchandise", "revenue": 20.0},
        {"stock_code": "POST", "description": "Postage", "product_type": "Operational", "revenue": 10.0},
    ])

    rules, metrics = phase3.make_product_affinity(sales, products)
    a_to_b = rules.set_index(["antecedent_stock_code", "consequent_stock_code"]).loc[("A", "B")]

    assert metrics["merchandise_baskets"] == 7
    assert metrics["qualified_item_pairs"] == 1
    assert metrics["association_rule_count"] == 2
    assert a_to_b["joint_orders"] == 5
    assert a_to_b["antecedent_orders"] == 6
    assert a_to_b["consequent_orders"] == 5
    assert a_to_b["support_pct"] == pytest.approx(5 / 7 * 100)
    assert a_to_b["confidence_pct"] == pytest.approx(5 / 6 * 100)
    assert a_to_b["lift"] == pytest.approx((5 / 6) / (5 / 7))
    assert (tmp_path / "product_associations.csv").exists()


def test_product_affinity_emits_schema_when_no_pair_meets_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(phase3, "OUT", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    sales = pd.DataFrame([
        {"invoice_key": "1", "stock_code_key": "A"},
        {"invoice_key": "2", "stock_code_key": "A"},
        {"invoice_key": "3", "stock_code_key": "B"},
    ])
    products = pd.DataFrame([
        {"stock_code": "A", "description": "Alpha", "product_type": "Merchandise", "revenue": 2.0},
        {"stock_code": "B", "description": "Beta", "product_type": "Merchandise", "revenue": 1.0},
    ])

    rules, metrics = phase3.make_product_affinity(sales, products)

    assert rules.empty
    assert list(rules.columns)[0:4] == [
        "antecedent_stock_code", "antecedent_description",
        "consequent_stock_code", "consequent_description",
    ]
    assert metrics["association_rule_count"] == 0
    assert metrics["merchandise_baskets"] == 3
