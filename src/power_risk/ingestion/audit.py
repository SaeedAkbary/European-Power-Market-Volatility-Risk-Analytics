"""Executable availability audit; tested windows are never global coverage claims."""
import json
from pathlib import Path

import pandas as pd

from power_risk.ingestion.http import get_json
from power_risk.ingestion.smard import fetch_prices
from power_risk.validation.quality import audit_prices


def run(start, end, root="."):
    root = Path(root)
    for name in ["raw", "processed", "features"]:
        (root / "data" / name).mkdir(parents=True, exist_ok=True)
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    rows = []

    def row(dataset, provider, **kwargs):
        record = dict(dataset=dataset, provider=provider, access_type="public HTTPS", free_access=True,
                      registration_required=False, historical_start="unknown", historical_end="unknown",
                      frequency="unknown", publication_time_available="unknown", missing_rate=None,
                      license="see docs/data_sources.md", limitations="", decision="NOT_TESTED",
                      verification_status="NOT_TESTED", token_required=False, tested_start=start, tested_end=end)
        record.update(kwargs)
        rows.append(record)
        return record

    price = row("day_ahead_prices", "SMARD", frequency="60min before 2025-10-01; 15min after",
                publication_time_available=False, license="CC BY 4.0; wholesale licensing review ongoing",
                limitations="Public chart endpoint; no documented SLA/rate limit or revision archive")
    try:
        frame = fetch_prices(start, end, root / "data/raw")
        quality = audit_prices(frame, start, end)
        (reports / "data_quality.json").write_text(json.dumps(quality, indent=2))
        price.update(historical_start=str(frame.delivery_start.min()), historical_end=str(frame.delivery_end.max()),
                     missing_rate=quality["missing_rate"], decision="include retrospective research",
                     verification_status="VERIFIED" if quality["missing_rate"] == 0 else "PARTIALLY_VERIFIED")
        try:
            frame.to_parquet(root / "data/processed/prices.parquet", index=False)
        except ImportError:
            frame.to_csv(root / "data/processed/prices.csv", index=False)
            price["limitations"] += "; Parquet backend unavailable; CSV saved, install a working backend"
    except Exception as exc:
        price.update(verification_status="UNAVAILABLE", decision="retry retrieval", limitations=str(exc))
    for dataset in ["day_ahead_prices", "actual_load", "day_ahead_load_forecast", "wind_solar_actual",
                    "wind_solar_forecast", "generation_by_fuel", "neighbor_prices", "commercial_schedules",
                    "physical_flows", "transfer_capacity"]:
        row(dataset, "ENTSO-E", registration_required=True, token_required=True,
            frequency="15/30/60min by document", publication_time_available="document creation time; not guaranteed first publication",
            limitations="Free token required; live retrieval not run. Country/category coverage and revisions unverified.",
            decision="connector available; authenticate and audit before integration")
    for dataset, host, route in [("weather_reanalysis", "archive-api", "archive"),
                                 ("weather_stitched_forecast", "historical-forecast-api", "forecast")]:
        item = row(dataset, "Open-Meteo", frequency="hourly", publication_time_available=False,
                   license="CC BY 4.0 data; hosted free API non-commercial only",
                   limitations="Sample only; equal-location mean is not generation-capacity weighted")
        url = (f"https://{host}.open-meteo.com/v1/{route}?latitude=53.55,52.37,48.14"
               "&longitude=9.99,9.73,11.58&start_date=2023-01-01&end_date=2023-01-07"
               "&hourly=temperature_2m,wind_speed_10m,shortwave_radiation&timezone=UTC&wind_speed_unit=ms")
        try:
            payload, _ = get_json(url, root / "data/raw")
            locations = payload if isinstance(payload, list) else [payload]
            values = [v for loc in locations for key, series in loc["hourly"].items() if key != "time" for v in series]
            item.update(historical_start="2023-01-01", historical_end="2023-01-07",
                        tested_start="2023-01-01", tested_end="2023-01-07", missing_rate=sum(v is None for v in values)/len(values),
                        verification_status="PARTIALLY_VERIFIED", decision="retrospective only; sample retrieved")
        except Exception as exc:
            item.update(verification_status="UNAVAILABLE", decision="retry sample", limitations=str(exc))
    row("weather_individual_runs", "Open-Meteo", frequency="model dependent", decision="exclude until run availability audited",
        limitations="Documented IFS archive March 2024; other models April 2026. Init time is not publication time.")
    row("calendar", "local Python holidays", access_type="local", frequency="delivery interval",
        decision="generate", limitations="National German holidays; state-specific holidays not nationwide")
    row("optional_carbon_gas_outages", "various official providers", decision="exclude from mandatory workflow",
        limitations="No free usable series verified in this audit")
    result = pd.DataFrame(rows)
    result.to_csv(reports / "data_availability_report.csv", index=False)
    return result

