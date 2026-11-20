"""Native market-time-unit risk, compared with aggregation on identical delivery hours."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

from power_risk.reporting.research import html_report


def ljung_box(series, lags):
    values = pd.Series(series).dropna()
    n = len(values)
    correlations = np.array([values.autocorr(k) for k in range(1, lags + 1)])
    statistic = n * (n + 2) * np.sum(correlations ** 2 / (n - np.arange(1, lags + 1)))
    return {"n": n, "lags": lags, "statistic": statistic, "p_value": chi2.sf(statistic, lags)}


def run():
    native = pd.read_parquet("data/processed/prices.parquet").set_index("delivery_start").sort_index()
    native["price_change"] = native.price_eur_mwh.diff().where(
        native.index.to_series().eq(native.delivery_end.shift()) & native.interval_minutes.eq(native.interval_minutes.shift()))
    native["abs_price_change"] = native.price_change.abs()
    native.to_parquet("reports/native_interval_volatility.parquet")
    quarter = native.loc[native.interval_minutes == 15]
    groups = quarter.price_eur_mwh.resample("h")
    hours = groups.agg(["count", "mean", "min", "max", "std"])
    hours = hours.loc[hours["count"] == 4]
    hours["spread"] = hours["max"] - hours["min"]
    hidden_negative = hours["min"].lt(0) & hours["mean"].ge(0)
    hidden_spike = hours["max"].ge(200) & hours["mean"].lt(200)
    summary = {"complete_quarterhour_hours": len(hours), "mean_intrahour_spread_eur_mwh": hours.spread.mean(),
        "max_intrahour_spread_eur_mwh": hours.spread.max(), "hidden_negative_hours": int(hidden_negative.sum()),
        "hidden_positive_spike_hours": int(hidden_spike.sum()),
        "native_price_std": quarter.price_eur_mwh.std(), "hourly_mean_price_std": hours["mean"].std()}
    Path("reports/intrahour_summary.json").write_text(json.dumps(summary, indent=2))
    hours.to_csv("reports/intrahour_metrics.csv")
    hourly = pd.read_parquet("reports/volatility_metrics.parquet")
    rows = []
    for name, values in [("absolute_hourly_changes", hourly.absolute_change),
                          ("squared_hour_adjusted_anomalies", hourly.anomaly ** 2)]:
        for lag in [24, 168]:
            rows.append({"series": name, **ljung_box(values, lag)})
    pd.DataFrame(rows).to_csv("reports/volatility_clustering_tests.csv", index=False)
    positive = native.price_eur_mwh.ge(200)
    contiguous = native.index.to_series().eq(native.delivery_end.shift())
    run_id = (~positive | ~positive.shift(fill_value=False) | ~contiguous).cumsum()
    episodes = []
    for _, block in native.loc[positive].groupby(run_id[positive]):
        episodes.append({"start": block.index.min(), "end": block.delivery_end.iloc[-1],
                         "hours": block.interval_minutes.sum() / 60, "max_price": block.price_eur_mwh.max()})
    pd.DataFrame(episodes).to_csv("reports/consecutive_positive_spikes.csv", index=False)
    html_report("reports/intrahour_price_risk.html", "Risk concealed by hourly averaging",
        "Observed quarter-hour contracts only, from 1 October 2025. Hidden negative/spike hours have at least one "
        "qualifying quarter but an hourly mean outside that event. Spread is max minus min within the same physical hour. "
        "Clustering tests use hourly levels/changes, not invalid log returns. Ljung-Box p-values are asymptotic diagnostics; "
        "seasonality, nonstationarity and rolling benchmark dependence preclude a causal or fully adjusted inference.",
        {"Same-period comparison": pd.Series(summary).to_frame("value"), "Clustering diagnostics": pd.DataFrame(rows)})
    return summary
