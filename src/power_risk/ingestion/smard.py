"""SMARD chart endpoint: raw values retained; prices in EUR/MWh."""
import pandas as pd

from power_risk.ingestion.http import get_json

BASE = "https://www.smard.de/app/chart_data"
TRANSITION = pd.Timestamp("2025-10-01", tz="Europe/Berlin").tz_convert("UTC")


def boundary(value):
    ts = pd.Timestamp(value)
    return ts.tz_localize("Europe/Berlin").tz_convert("UTC") if ts.tz is None else ts.tz_convert("UTC")


def fetch_series(start, end, filter_id=4169, resolution="hour", cache="data/raw"):
    start, end = boundary(start), boundary(end)
    if end <= start:
        raise ValueError("end must be after start (exclusive)")
    index, _ = get_json(f"{BASE}/{filter_id}/DE/index_{resolution}.json", cache)
    stamps = sorted(index["timestamps"])
    rows = []
    for i, stamp in enumerate(stamps):
        left = pd.Timestamp(stamp, unit="ms", tz="UTC")
        right = pd.Timestamp(stamps[i + 1], unit="ms", tz="UTC") if i + 1 < len(stamps) else left + pd.Timedelta(days=8)
        if left >= end or right <= start:
            continue
        url = f"{BASE}/{filter_id}/DE/{filter_id}_DE_{resolution}_{stamp}.json"
        payload, meta = get_json(url, cache)
        for timestamp, value in payload["series"]:
            delivery = pd.Timestamp(timestamp, unit="ms", tz="UTC")
            if start <= delivery < end:
                rows.append({"delivery_start": delivery, "value": value, "source_url": url,
                             "retrieved_at": meta["retrieved_at"]})
    if not rows:
        raise ValueError("No SMARD observations in requested window")
    result = pd.DataFrame(rows).sort_values("delivery_start")
    if result.delivery_start.duplicated().any():
        raise ValueError("Duplicate SMARD timestamps; inspect source chunks")
    return result


def fetch_prices(start, end, cache="data/raw"):
    start, end = boundary(start), boundary(end)
    frames = []
    for left, right, resolution, minutes in [(start, min(end, TRANSITION), "hour", 60),
                                             (max(start, TRANSITION), end, "quarterhour", 15)]:
        if left >= right:
            continue
        frame = fetch_series(left, right, resolution=resolution, cache=cache)
        frame["interval_minutes"] = minutes
        frames.append(frame)
    if not frames:
        raise ValueError("Empty date range")
    frame = pd.concat(frames, ignore_index=True).rename(columns={"value": "price_eur_mwh"})
    frame["delivery_end"] = frame.delivery_start + pd.to_timedelta(frame.interval_minutes, unit="min")
    frame["bidding_zone"] = "DE-LU"
    local = frame.delivery_start.dt.tz_convert("Europe/Berlin")
    frame["local_delivery_hour"] = local.dt.hour
    frame["market_date"] = local.dt.strftime("%Y-%m-%d")
    frame["provider"] = "Bundesnetzagentur | SMARD.de"
    frame["publication_time"] = pd.NaT
    frame["forecast_issue_time"] = pd.NaT
    return frame

