import pandas as pd


def asof_features(vintages, cutoff):
    """Fail closed for missing publication or issue times; select latest available vintage."""
    cutoff = pd.Timestamp(cutoff)
    if cutoff.tzinfo is None:
        raise ValueError("Cutoff must be timezone-aware")
    f = vintages.copy()
    for col in ["publication_time", "forecast_issue_time"]:
        f[col] = pd.to_datetime(f[col], utc=True)
    eligible = f.publication_time.notna() & f.forecast_issue_time.notna()
    eligible &= f.publication_time.le(cutoff) & f.forecast_issue_time.le(cutoff)
    return (f.loc[eligible].sort_values(["publication_time", "forecast_issue_time"])
            .drop_duplicates(["delivery_start", "variable"], keep="last"))
