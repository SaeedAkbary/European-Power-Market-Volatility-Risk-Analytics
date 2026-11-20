"""Synthetic mechanics tests, never included in market research outputs."""
import hashlib
import json
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
import requests

from power_risk.forecasting.enhanced import calibrate_month, conformal_expansion
from power_risk.ingestion.fundamentals import hourly_complete, net_import, normalize
from power_risk.ingestion.http import get_json
from power_risk.portfolio.enhanced import capture_price, prices_on_quarters


def test_native_energy_conversion_and_missing_hour():
    idx = pd.date_range("2024-01-01", periods=4, freq="15min", tz="Europe/Berlin").tz_convert("UTC")
    raw = pd.DataFrame({"delivery_start": idx, "value": [10., 20., None, 40.]})
    normalized = normalize(raw, idx[0], idx[-1] + pd.Timedelta(minutes=15))
    assert normalized.iloc[0] == 40
    assert np.isnan(hourly_complete(normalized.to_frame("actual_load_mw")).iloc[0, 0])
    with pytest.raises(ValueError, match="Duplicate"):
        normalize(pd.concat([raw, raw.iloc[:1]]), idx[0], idx[-1] + pd.Timedelta(minutes=15))


def test_physical_invalid_value_and_price_negative_valid():
    idx = pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC")
    raw = pd.DataFrame({"delivery_start": idx, "value": [-10.] * 4})
    with pytest.raises(ValueError, match="Invalid"):
        normalize(raw, idx[0], idx[-1] + pd.Timedelta(minutes=15))
    assert normalize(raw, idx[0], idx[-1] + pd.Timedelta(minutes=15), energy=False).iloc[0] == -10


def test_actual_and_forecast_columns_stay_distinct():
    idx = pd.date_range("2024-03-31", periods=92, freq="15min", tz="Europe/Berlin").tz_convert("UTC")
    data = pd.DataFrame({"actual_load_mw": 40., "forecast_load_mw": 50.}, index=idx)
    result = hourly_complete(data)
    assert len(result) == 23
    assert (result.actual_load_mw == 40).all() and (result.forecast_load_mw == 50).all()


def test_border_direction_keeps_import_positive_into_de():
    assert net_import(300, 100) == 200
    assert net_import(100, 300) == -200


def test_capture_weighting_zero_output_and_invalid():
    assert capture_price([100, -20], [1, 3], [.25, .25]) == 10
    assert np.isnan(capture_price([100], [0], [.25]))
    with pytest.raises(ValueError):
        capture_price([100], [-1], [.25])


def test_contract_price_never_carried_beyond_end():
    start = pd.Timestamp("2024-01-01", tz="UTC")
    prices = pd.DataFrame({"delivery_start": [start], "delivery_end": [start + pd.Timedelta(hours=1)], "price_eur_mwh": [-10.]})
    index = pd.date_range(start, periods=5, freq="15min")
    result = prices_on_quarters(prices, index)
    assert result.iloc[:4].tolist() == [-10.] * 4
    assert np.isnan(result.iloc[4])


def calibration_fixture():
    idx = pd.date_range("2024-01-01", periods=240, freq="h", tz="UTC")
    f = pd.DataFrame({"actual": np.tile([-20., 220.], 120), "q10": 0., "q50": 100., "q90": 200.,
                      "p_negative": .2, "p_spike": .2}, index=idx)
    return f


def test_calibration_expansion_and_no_test_label_use():
    f = calibration_fixture()
    assert conformal_expansion(f) == 20
    test = f.iloc[:24].copy()
    test.index = test.index + pd.Timedelta(days=20)
    cutoff = f.index[-1] + pd.Timedelta(hours=1)
    a = calibrate_month(f, test, cutoff)
    test.actual = 1000000
    b = calibrate_month(f, test, cutoff)
    pd.testing.assert_frame_equal(a[["q10", "q90", "p_negative"]], b[["q10", "q90", "p_negative"]])
    with pytest.raises(ValueError, match="precede"):
        calibrate_month(f, test, f.index[-1])


def test_http_cache_integrity_and_retry(tmp_path, monkeypatch):
    content = json.dumps({"series": [[1, 2]]}).encode()
    response = Mock(status_code=200, content=content)
    response.json.return_value = json.loads(content)
    response.raise_for_status.return_value = None
    getter = Mock(side_effect=[requests.Timeout("test"), response])
    monkeypatch.setattr("power_risk.ingestion.http.requests.get", getter)
    monkeypatch.setattr("power_risk.ingestion.http.time.sleep", lambda _: None)
    url = "https://example.invalid/test"
    assert get_json(url, tmp_path)[0] == json.loads(content)
    assert getter.call_count == 2
    get_json(url, tmp_path)
    assert getter.call_count == 2
    key = hashlib.sha256(url.encode()).hexdigest()
    (tmp_path / (key + ".json")).write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        get_json(url, tmp_path)


def test_http_terminal_failure(tmp_path, monkeypatch):
    getter = Mock(side_effect=requests.Timeout("test failure"))
    monkeypatch.setattr("power_risk.ingestion.http.requests.get", getter)
    monkeypatch.setattr("power_risk.ingestion.http.time.sleep", lambda _: None)
    with pytest.raises(requests.Timeout):
        get_json("https://example.invalid/failure", tmp_path)
    assert getter.call_count == 4
