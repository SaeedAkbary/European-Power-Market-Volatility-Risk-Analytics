"""Verified SMARD fields; quarter-hour energy is MWh, not MW."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from power_risk.fundamentals.analysis import residual_load
from power_risk.ingestion.http import get_json
from power_risk.ingestion.smard import boundary, fetch_series
from power_risk.reporting.research import html_report

# Category IDs confirmed against SMARD's official forecast article chart parameters.
# Raw files retain original energy values; normalized physical quantities describe Germany.
SERIES = {
    "actual_load_mw": 410, "forecast_load_mw": 411,
    "actual_wind_onshore_mw": 4067, "actual_wind_offshore_mw": 1225, "actual_solar_mw": 4068,
    "forecast_wind_onshore_mw": 123, "forecast_wind_offshore_mw": 3791, "forecast_solar_mw": 125,
    "actual_gas_mw": 4071, "actual_hard_coal_mw": 4069, "actual_lignite_mw": 1223,
    "actual_hydro_mw": 1226, "actual_biomass_mw": 4066, "actual_other_conventional_mw": 1227,
    "actual_other_renewable_mw": 1228, "actual_nuclear_mw": 1224,
    "fr_price_eur_mwh": 254, "nl_price_eur_mwh": 256,
    "commercial_fr_export_mw": 4404, "commercial_fr_import_mw": 4546,
    "physical_fr_export_mw": 4737, "physical_fr_import_mw": 4881,
}


def normalize(frame, start, end, energy=True):
    expected = pd.date_range(boundary(start), boundary(end), freq="15min", inclusive="left")
    if frame.delivery_start.duplicated().any():
        raise ValueError("Duplicate fundamental timestamps")
    if not frame.delivery_start.isin(expected).all():
        raise ValueError("Misaligned fundamental timestamps")
    values = pd.to_numeric(frame.set_index("delivery_start").value, errors="raise")
    if np.isinf(values).any() or (energy and values.dropna().lt(0).any()):
        raise ValueError("Invalid physical energy or nonfinite values")
    return values.reindex(expected) * (4. if energy else 1.)


def hourly_complete(native):
    numeric = native.select_dtypes("number")
    return numeric.resample("h").mean().where(numeric.resample("h").count() == 4)


def net_import(import_mw, export_mw):
    """Positive into Germany; never use a physical series as a commercial schedule."""
    return import_mw - export_mw


def run(start="2023-01-01", end="2026-11-19"):
    catalog, _ = get_json("https://www.smard.de/app/chart_configuration/market_data_configuration.json")
    modules = [module for main in catalog["main"] for sub in main["sub"]
               for group in sub.get("module", {}).values() for module in group]
    for variable, code in SERIES.items():
        matches = [m for m in modules if m["data_id"] == code and "DE" in m["region"]]
        unit = "VD-Einheit.MWh" if variable.endswith("_mw") else "VD-Einheit.Euro/MWh"
        if not matches or not all(m["unit"] == unit for m in matches):
            raise ValueError(f"Provider catalogue unit/region mismatch for {variable}")
    Path("reports/smard_field_catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    native = pd.DataFrame(index=pd.date_range(boundary(start), boundary(end), freq="15min", inclusive="left"))
    native.index.name = "delivery_start"
    quality, manifests = [], {}

    def retrieve(name, code):
        frame = fetch_series(start, end, code, "quarterhour")
        normalized_frame = frame.copy()
        if name.endswith("_import_mw"):
            # SMARD import chart observations are signed negative; normalized direction is explicit.
            normalized_frame["value"] = -normalized_frame.value
        values = normalize(normalized_frame, start, end, energy=name.endswith("_mw"))
        return name, code, frame, values

    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {executor.submit(retrieve, name, code): name for name, code in SERIES.items()}
        for future in as_completed(pending):
            name = pending[future]
            try:
                name, code, frame, values = future.result()
                native[name] = values
                quality.append({"variable": name, "filter_id": code, "expected_intervals": len(values),
                    "observed_intervals": int(values.notna().sum()), "missing_rate": values.isna().mean(),
                    "first_valid": str(values.first_valid_index()), "last_valid": str(values.last_valid_index()),
                    "duplicates": 0, "unit": "MW" if name.endswith("_mw") else "EUR/MWh",
                    "status": "VERIFIED" if values.notna().all() else "PARTIALLY_VERIFIED"})
                manifests[name] = {"filter_id": code, "raw_unit": "MWh/15min" if name.endswith("_mw") else "EUR/MWh",
                    "area": "DE" if name.endswith("_mw") else name[:2].upper(),
                    "urls": sorted(frame.source_url.unique().tolist()), "retrieved_at": sorted(frame.retrieved_at.unique().tolist()),
                    "publication_time": None, "issue_time": None, "historical_vintage_verified": False}
                manifests[name]["normalization"] = "raw times -4; import magnitude into DE" if name.endswith("_import_mw") else "raw times 4 for energy; prices unchanged"
                print(f"{name}: {values.notna().sum()}/{len(values)} observed", flush=True)
            except Exception as exc:
                quality.append({"variable": name, "filter_id": SERIES[name], "status": "UNAVAILABLE", "error": str(exc)})
                print(f"{name}: unavailable ({type(exc).__name__})", flush=True)
            pd.DataFrame(quality).to_csv("reports/fundamental_data_quality.csv", index=False)
    for prefix in ["actual_", "forecast_"]:
        required = [prefix + c for c in ["load_mw", "wind_onshore_mw", "wind_offshore_mw", "solar_mw"]]
        if all(c in native for c in required):
            native[prefix + "residual_load_mw"] = residual_load(native, prefix)
    for kind in ["physical", "commercial"]:
        cols = [kind + "_fr_import_mw", kind + "_fr_export_mw"]
        if all(c in native for c in cols):
            native[kind + "_fr_net_import_mw"] = net_import(native[cols[0]], native[cols[1]])
    hourly = hourly_complete(native)
    native["delivery_end"] = native.index + pd.Timedelta(minutes=15)
    native["interval_minutes"] = 15
    native["market_date"] = native.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")
    native["publication_time"] = pd.NaT
    native["forecast_issue_time"] = pd.NaT
    native.to_parquet("data/processed/fundamentals_native.parquet")
    hourly.to_parquet("data/processed/fundamentals_hourly.parquet")
    Path("reports/fundamental_provenance.json").write_text(json.dumps(manifests, indent=2))
    q = pd.DataFrame(quality).sort_values("variable")
    q.to_csv("reports/fundamental_data_quality.csv", index=False)
    html_report("reports/fundamental_coverage.html", "SMARD fundamental coverage",
        f"Requested {start} to {end} exclusive. Source: Bundesnetzagentur | SMARD.de. Physical series are German "
        "net grid-load/generation, not DE-LU total demand. MWh per quarter-hour divided by 0.25 gives MW. "
        "Only four observed quarters produce an hourly mean. No zero-filling. Forecasts are latest snapshots with "
        "unknown original issue/publication times and are NOT certified pre-auction inputs. Neighbor prices before "
        "October 2025 are repeated hourly contracts displayed at quarter-hour resolution. No physical/commercial "
        "flow substitutions. French-border import magnitudes are positive into DE, exports positive out, net import=import-export. "
        "Commercial exchanges are reported trade, not certified pre-clearing schedules.", {"Coverage": q})
    inventory = pd.read_csv("reports/data_availability_report.csv")
    inventory = inventory.loc[~((inventory.provider == "SMARD") & inventory.dataset.isin(SERIES))]
    rows = [dict(dataset=r["variable"], provider="SMARD", access_type="public HTTPS", free_access=True,
        registration_required=False, historical_start=r.get("first_valid"), historical_end=r.get("last_valid"),
        frequency="15min display; original units retained in raw", publication_time_available=False,
        missing_rate=r.get("missing_rate"), license="CC BY 4.0; Bundesnetzagentur | SMARD.de",
        limitations="Latest snapshot; original forecast vintages unavailable; DE physical area versus DE-LU price",
        decision="retrospective analysis only", verification_status=r["status"], token_required=False,
        tested_start=start, tested_end=end) for r in quality]
    pd.concat([inventory, pd.DataFrame(rows)], ignore_index=True).to_csv("reports/data_availability_report.csv", index=False)
    return q
