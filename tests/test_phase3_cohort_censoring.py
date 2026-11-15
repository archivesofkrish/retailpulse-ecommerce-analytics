import pandas as pd

import scripts.run_phase3_analysis as phase3


def test_phase3_cohort_matrix_distinguishes_observed_zero_from_unobserved(tmp_path, monkeypatch):
    monkeypatch.setattr(phase3, "OUT", tmp_path)
    sales = pd.DataFrame({
        "customer_id_num": [1, 1, 2, 3],
        "invoice": ["1001", "1002", "1003", "1004"],
        "invoice_date": pd.to_datetime([
            "2011-03-10", "2011-05-10", "2011-04-12", "2011-05-15"
        ]),
    })

    phase3.make_cohort_outputs(sales)
    retention = pd.read_csv(tmp_path / "cohort_retention_recomputed.csv", index_col=0)

    # The March cohort was observed in April with zero activity, then returned in May.
    assert retention.loc["2011-03", "1"] == 0.0
    assert retention.loc["2011-03", "2"] == 1.0
    # April is observed in May, but there were no repeat purchases.
    assert retention.loc["2011-04", "1"] == 0.0
    # May has no June follow-up in the source window; it must remain missing.
    assert pd.isna(retention.loc["2011-05", "1"])
