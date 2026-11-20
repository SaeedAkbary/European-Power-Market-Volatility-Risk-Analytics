import pandas as pd

from power_risk.features.availability import asof_features
from power_risk.fundamentals.analysis import residual_load


def test_future_and_unknown_vintages_excluded():
    f = pd.DataFrame({"delivery_start": ["2024-01-02"] * 3, "variable": ["load"] * 3,
        "publication_time": ["2024-01-01T09:00Z", "2024-01-01T12:00Z", None],
        "forecast_issue_time": ["2024-01-01T08:00Z"] * 3, "value": [10, 20, 30]})
    assert asof_features(f, "2024-01-01T10:00Z").value.tolist() == [10]


def test_residual_load_requires_all_components():
    f = pd.DataFrame({"actual_load_mw": [100, 100], "actual_wind_onshore_mw": [20, 20],
                      "actual_wind_offshore_mw": [10, None], "actual_solar_mw": [30, 30]})
    result = residual_load(f)
    assert result.iloc[0] == 40
    assert pd.isna(result.iloc[1])
