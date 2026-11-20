import pandas as pd

from power_risk.features.calendar import calendar


def calculate(hourly):
    f = hourly.join(calendar(hourly.index))
    p = f.price_eur_mwh
    f["price_change"] = p.diff()
    f["absolute_change"] = p.diff().abs()
    f["rolling_std_7d"] = p.rolling(168, min_periods=168).std()
    past = p.shift(1)
    f["historical_q01"] = past.rolling(24 * 90, min_periods=24 * 30).quantile(.01)
    f["historical_q99"] = past.rolling(24 * 90, min_periods=24 * 30).quantile(.99)
    f["bollinger_mid"] = p.rolling(24, min_periods=24).mean()
    f["bollinger_upper"] = f.bollinger_mid + 2 * p.rolling(24).std()
    f["bollinger_lower"] = f.bollinger_mid - 2 * p.rolling(24).std()
    f["hour_baseline"] = f.groupby("hour").price_eur_mwh.transform(lambda x: x.shift().rolling(60, min_periods=30).median())
    f["anomaly"] = p - f.hour_baseline
    f["negative"] = p.lt(0).where(p.notna())
    f["positive_spike"] = p.ge(200).where(p.notna())
    f["quantile_spike"] = p.gt(f.historical_q99).where(f.historical_q99.notna() & p.notna())
    f["sharp_ramp"] = f.absolute_change.ge(100).where(f.absolute_change.notna())
    daily = f.groupby("market_date").price_eur_mwh.agg(["min", "max", "first", "last", "count"])
    daily["spread"] = daily["max"] - daily["min"]
    local_days = pd.DatetimeIndex(pd.to_datetime(daily.index)).tz_localize("Europe/Berlin")
    expected = [(d + pd.DateOffset(days=1) - d).total_seconds() / 3600 for d in local_days]
    daily["complete"] = daily["count"].to_numpy() == expected
    daily.loc[~daily.complete, "spread"] = float("nan")
    previous_close = daily["last"].shift()
    daily["true_range"] = pd.concat([daily.spread, (daily["max"] - previous_close).abs(),
                                    (daily["min"] - previous_close).abs()], axis=1).max(axis=1).where(daily.complete)
    daily["atr_14d"] = daily.true_range.rolling(14, min_periods=14).mean()
    return f, daily

