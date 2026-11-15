from datetime import timedelta

import pandas as pd


def purged_split(panel: pd.DataFrame, split_date: str, horizon_days: int = 90):
    split = pd.Timestamp(split_date)
    horizon = timedelta(days=horizon_days)
    train = panel[panel["snapshot_date"] <= split].copy()
    test = panel[panel["snapshot_date"] > split + horizon].copy()
    return train, test, horizon


def test_90_day_label_horizon_does_not_overlap_first_test_snapshot():
    panel = pd.DataFrame({
        "snapshot_date": pd.to_datetime([
            "2010-08-31", "2010-09-30", "2010-10-31", "2010-11-30",
            "2010-12-31", "2011-01-31", "2011-02-28"
        ])
    })
    train, test, horizon = purged_split(panel, "2010-10-31", 90)
    assert train["snapshot_date"].max() == pd.Timestamp("2010-10-31")
    assert test["snapshot_date"].min() == pd.Timestamp("2011-01-31")
    assert train["snapshot_date"].max() + horizon < test["snapshot_date"].min()


def test_all_snapshots_inside_embargo_are_excluded_from_test():
    panel = pd.DataFrame({
        "snapshot_date": pd.to_datetime([
            "2010-10-31", "2010-11-30", "2010-12-31", "2011-01-31"
        ])
    })
    train, test, _ = purged_split(panel, "2010-10-31", 90)
    assert list(train["snapshot_date"].dt.strftime("%Y-%m-%d")) == ["2010-10-31"]
    assert list(test["snapshot_date"].dt.strftime("%Y-%m-%d")) == ["2011-01-31"]
