import numpy as np
import pandas as pd

from power_risk.ingestion.smard import TRANSITION, boundary


def expected_index(start, end):
    start, end = boundary(start), boundary(end)
    parts = []
    if start < min(end, TRANSITION):
        parts.append(pd.date_range(start, min(end, TRANSITION), freq="h", inclusive="left"))
    if max(start, TRANSITION) < end:
        parts.append(pd.date_range(max(start, TRANSITION), end, freq="15min", inclusive="left"))
    return parts[0].append(parts[1:]) if parts else pd.DatetimeIndex([], tz="UTC")


def audit_prices(frame, start, end):
    expected = expected_index(start, end)
    if frame.delivery_start.duplicated().any():
        raise ValueError("Duplicate delivery intervals")
    if not frame.delivery_start.isin(expected).all():
        raise ValueError("Unexpected or misaligned intervals")
    required_duration = np.where(frame.delivery_start < TRANSITION, 60, 15)
    if not np.array_equal(frame.interval_minutes.to_numpy(), required_duration):
        raise ValueError("Incorrect native market time unit")
    if not ((frame.delivery_end - frame.delivery_start).dt.total_seconds() == required_duration * 60).all():
        raise ValueError("Incorrect interval endpoints")
    values = pd.to_numeric(frame.price_eur_mwh, errors="raise")
    if np.isinf(values).any():
        raise ValueError("Infinite price")
    valid = frame.loc[values.notna(), "delivery_start"]
    missing = expected.difference(valid)
    return {"expected_intervals": len(expected), "retrieved_rows": len(frame),
            "missing_intervals": len(missing), "missing_rate": len(missing) / len(expected),
            "duplicates": 0, "start_utc": str(expected.min()), "end_exclusive_utc": str(boundary(end)),
            "missing_timestamps": [str(x) for x in missing]}


def hourly_prices(frame):
    """Duration-weighted mean, requiring complete coverage; never forward fill."""
    f = frame.set_index("delivery_start").sort_index()
    valid_minutes = f.interval_minutes.where(f.price_eur_mwh.notna(), 0)
    coverage = valid_minutes.resample("h").sum()
    weighted = (f.price_eur_mwh * f.interval_minutes).resample("h").sum(min_count=1)
    result = (weighted / coverage).where(coverage == 60).to_frame("price_eur_mwh")
    result["coverage_minutes"] = coverage
    return result
