"""Expanding monthly research backtest, fixed parameters, strictly lagged prices."""
import numpy as np
import pandas as pd

from power_risk.backtesting.validation import calibration, summarize
from power_risk.features.calendar import calendar
from power_risk.reporting.research import html_report


def design(hourly):
    frame = calendar(hourly.index)
    frame["target"] = hourly.price_eur_mwh
    for lag in [48, 168]:
        frame[f"price_lag_{lag}"] = hourly.price_eur_mwh.shift(lag)
    frame["past_mean_7d"] = hourly.price_eur_mwh.shift(48).rolling(168).mean()
    frame["past_std_7d"] = hourly.price_eur_mwh.shift(48).rolling(168).std()
    return frame


def run(advanced=False):
    if advanced:
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        from sklearn.linear_model import QuantileRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    hourly = pd.read_parquet("data/processed/prices_hourly.parquet")
    f = design(hourly).dropna()
    columns = ["hour", "weekday", "month", "weekend", "holiday", "dst", "price_lag_48", "price_lag_168", "past_mean_7d", "past_std_7d"]
    results = []
    # Monthly refits before the first delivery day's issuance cutoff.
    months = sorted(set(f.loc[f.index >= pd.Timestamp("2024-01-01", tz="Europe/Berlin"), "market_date"].str[:7]))
    for month in months:
        first = pd.Timestamp(month + "-01", tz="Europe/Berlin")
        next_month = first + pd.offsets.MonthBegin(1)
        cutoff = first - pd.DateOffset(days=1) + pd.Timedelta(hours=11)
        train = f.loc[f.index < cutoff.tz_convert("UTC")]
        test = f.loc[(f.index >= first.tz_convert("UTC")) & (f.index < next_month.tz_convert("UTC"))]
        if len(train) < 24 * 180 or test.empty:
            continue
        x, y, xt = train[columns], train.target, test[columns]
        names = ["seasonal_history", "linear_quantile", "gradient_boosting"] if advanced else ["seasonal_history"]
        for name in names:
            out = pd.DataFrame(index=test.index)
            out["actual"] = test.target
            out["model"] = name
            out["fit_cutoff"] = cutoff.tz_convert("UTC")
            for q, label in [(.1, "q10"), (.5, "q50"), (.9, "q90")]:
                if name == "seasonal_history":
                    residual = train.target - train.price_lag_168
                    offsets = residual.groupby(train.hour).quantile(q)
                    out[label] = test.price_lag_168 + test.hour.map(offsets)
                else:
                    model = (make_pipeline(StandardScaler(), QuantileRegressor(quantile=q, alpha=.1, solver="highs"))
                             if name == "linear_quantile" else
                             HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=60, max_leaf_nodes=15,
                                                           min_samples_leaf=48, early_stopping=False, random_state=42))
                    # Fixed recent 90-day window bounds linear-program solver cost.
                    model.fit(x.iloc[-2160:] if name == "linear_quantile" else x,
                              y.iloc[-2160:] if name == "linear_quantile" else y)
                    out[label] = model.predict(xt)
            out[["q10", "q50", "q90"]] = np.sort(out[["q10", "q50", "q90"]].to_numpy(), axis=1)
            for event, col in [(y < 0, "p_negative"), (y >= 200, "p_spike")]:
                if name != "gradient_boosting" or event.nunique() < 2:
                    rate = event.groupby(train.hour).mean()
                    out[col] = test.hour.map(rate)
                else:
                    classifier = HistGradientBoostingClassifier(max_iter=60, max_leaf_nodes=15, min_samples_leaf=48,
                                                               early_stopping=False, random_state=42)
                    classifier.fit(x, event)
                    out[col] = classifier.predict_proba(xt)[:, 1]
            results.append(out)
        print(f"Completed {month}: {len(test)} hourly predictions per model", flush=True)
    if not results:
        raise ValueError("Insufficient history for walk-forward evaluation")
    forecasts = pd.concat(results).sort_index()
    save_results(forecasts)


def save_results(forecasts):
    forecasts.to_parquet("reports/price_risk_forecasts.parquet")
    comparison = summarize(forecasts)
    comparison.to_csv("reports/model_comparison.csv", index=False)
    reliability = calibration(forecasts)
    reliability.to_csv("reports/probability_calibration.csv", index=False)
    seasonal = forecasts.copy()
    seasonal[["hour", "season"]] = calendar(forecasts.index)[["hour", "season"]].to_numpy()
    for key in ["hour", "season"]:
        pd.concat([summarize(g).assign(**{key: label}) for label, g in seasonal.groupby(key)]).to_csv(f"reports/validation_by_{key}.csv", index=False)
    daily = forecasts.assign(day=forecasts.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")).groupby(["model", "day"]).agg(
        predicted_dispersion=("q50", "std"), actual_dispersion=("actual", "std"))
    daily.to_csv("reports/daily_dispersion_forecasts.csv")
    html_report("reports/forecast_validation.html", "Exploratory price-risk backtest",
        "Actual SMARD targets, monthly expanding fits from 2024. D−1 11:00 Berlin cutoff; price features lagged at least "
        "48 hours. Linear quantile model uses a fixed recent 90-day training window; other fits expand. "
        "Fixed model settings; quantiles rearranged to prevent crossing. Seasonal baseline uses prior-week "
        "price plus training-only delivery-hour residual quantiles. Linear quantile probabilities reuse the seasonal "
        "classifier benchmark. Calibration is assessed out of sample, not fitted on test labels. Daily q50 dispersion "
        "is a point proxy and excludes conditional residual variance. Source publication/vintage history is unavailable: "
        "these are exploratory historical results, NOT a verified executable ex-ante strategy. No fundamental or weather "
        "features are used. No claim of statistically significant superiority; uncertainty intervals remain future work.",
        {"Walk-forward comparison": comparison, "Probability reliability": reliability})
