"""Free-token raw XML connector. Retains document times; does not imply vintage availability."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ZONE = "10Y1001A1001A82H"
QUERIES = {
    "prices": {"documentType": "A44", "in_Domain": ZONE, "out_Domain": ZONE},
    "actual_load": {"documentType": "A65", "processType": "A16", "outBiddingZone_Domain": ZONE},
    "forecast_load": {"documentType": "A65", "processType": "A01", "outBiddingZone_Domain": ZONE},
    "actual_generation": {"documentType": "A75", "processType": "A16", "in_Domain": ZONE},
    "forecast_renewables": {"documentType": "A69", "processType": "A01", "in_Domain": ZONE},
    "physical_flows": {"documentType": "A11"},
    "commercial_schedules": {"documentType": "A09", "contract_MarketAgreement.Type": "A01"},
    "transfer_capacity": {"documentType": "A61", "contract_MarketAgreement.Type": "A01"},
}


def download(dataset, start_utc, end_utc, cache="data/raw/entsoe", **domains):
    """Dates YYYYMMDDHHMM UTC; use short (e.g. monthly) requests. Border queries need domains."""
    token = os.environ.get("ENTSOE_API_TOKEN")
    if not token:
        raise RuntimeError("Set ENTSOE_API_TOKEN using free Transparency Platform registration")
    params = dict(QUERIES[dataset], periodStart=start_utc, periodEnd=end_utc, **domains)
    if dataset in {"physical_flows", "commercial_schedules", "transfer_capacity"}:
        if not {"in_Domain", "out_Domain"} <= params.keys():
            raise ValueError("Border queries require distinct in_Domain and out_Domain")
    folder = Path(cache)
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = folder / f"{key}.xml"
    if path.exists():
        return path
    for attempt in range(4):
        try:
            response = requests.get("https://web-api.tp.entsoe.eu/api", params={**params, "securityToken": token}, timeout=90)
            if response.status_code == 200:
                if b"Acknowledgement_MarketDocument" in response.content:
                    raise RuntimeError("ENTSO-E returned acknowledgement/no data; no observations saved")
                path.write_bytes(response.content)
                path.with_suffix(".meta.json").write_text(json.dumps({"query": params,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "sha256": hashlib.sha256(response.content).hexdigest()}, indent=2))
                return path
            if response.status_code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"ENTSO-E HTTP {response.status_code}; credentials/parameters require checking")
        except requests.RequestException:
            pass  # Do not expose request URLs containing credentials in exceptions or logs.
        time.sleep(2 ** attempt)
    raise RuntimeError("ENTSO-E unavailable after four attempts; token not logged")

