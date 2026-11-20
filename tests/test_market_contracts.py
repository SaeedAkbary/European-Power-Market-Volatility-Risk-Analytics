"""Synthetic fixtures test mechanics only; never used as market evidence."""
import pandas as pd
import pytest

from power_risk.ingestion.smard import TRANSITION
from power_risk.spikes.events import negative_runs
from power_risk.validation.quality import audit_prices, expected_index, hourly_prices
from power_risk.volatility.metrics import calculate


def native(index, prices, minutes=60):
    return pd.DataFrame({"delivery_start": index, "delivery_end": index + pd.Timedelta(minutes=minutes),
                         "interval_minutes": minutes, "price_eur_mwh": prices})


def test_dst_days_and_transition():
    assert len(expected_index("2024-03-31", "2024-04-01")) == 23
    assert len(expected_index("2024-10-27", "2024-10-28")) == 25
    assert len(expected_index("2025-10-26", "2025-10-27")) == 100
    assert len(expected_index("2025-09-30", "2025-10-02")) == 120


def test_missing_quarter_invalidates_hour_and_negative_is_valid():
    index = pd.date_range(TRANSITION, periods=4, freq="15min")
    frame = native(index, [-40., 0., 20., 40.], 15)
    assert hourly_prices(frame).price_eur_mwh.iloc[0] == 5
    assert pd.isna(hourly_prices(frame.iloc[:3]).price_eur_mwh.iloc[0])
    frame.loc[1, "price_eur_mwh"] = None
    assert pd.isna(hourly_prices(frame).price_eur_mwh.iloc[0])


def test_quality_counts_missing_and_rejects_duplicates():
    idx = expected_index("2024-01-01", "2024-01-02")
    frame = native(idx, [-10.] * 24)
    assert audit_prices(frame, "2024-01-01", "2024-01-02")["missing_rate"] == 0
    assert audit_prices(frame.iloc[:-1], "2024-01-01", "2024-01-02")["missing_intervals"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        audit_prices(pd.concat([frame, frame.iloc[:1]]), "2024-01-01", "2024-01-02")


def test_negative_runs_break_at_gap_and_null():
    idx = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
    frame = native(idx, [-1., -2., None, -3., -4.])
    runs = negative_runs(frame)
    assert list(runs.duration_hours) == [2., 2.]
    assert len(negative_runs(frame.drop(index=1))) == 2


def test_future_prices_do_not_change_past_thresholds():
    idx = pd.date_range("2024-01-01", periods=2400, freq="h", tz="UTC")
    f = pd.DataFrame({"price_eur_mwh": [float(i % 24) for i in range(2400)]}, index=idx)
    before, _ = calculate(f)
    f.iloc[2000:, 0] = 10000
    after, _ = calculate(f)
    pd.testing.assert_series_equal(before.historical_q99.iloc[:2001], after.historical_q99.iloc[:2001])
