import numpy as np
import pandas as pd

from power_risk.forecasting.models import design
from power_risk.regimes.model import classify


def test_predictive_features_unchanged_by_future_targets():
    index = pd.date_range("2023-01-01", periods=600, freq="h", tz="UTC")
    frame = pd.DataFrame({"price_eur_mwh": np.arange(600, dtype=float)}, index=index)
    a = design(frame)
    frame.iloc[400:, 0] = -10000
    b = design(frame)
    for col in ["price_lag_48", "price_lag_168", "past_mean_7d", "past_std_7d"]:
        pd.testing.assert_series_equal(a[col].iloc[:448], b[col].iloc[:448])


def test_regime_cutpoints_fixed_before_evaluation():
    index = pd.date_range("2023-01-01", periods=1000, freq="h", tz="UTC")
    series = pd.Series(np.arange(1000), index=index)
    _, cuts = classify(series, index[800])
    series.iloc[800:] = 1e6
    _, changed = classify(series, index[800])
    np.testing.assert_array_equal(cuts, changed)
