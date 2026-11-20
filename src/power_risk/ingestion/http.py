"""Low-rate HTTP retrieval with immutable response caching and provenance."""
import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

import requests

LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


def get_json(url, cache="data/raw", refresh=False):
    folder = Path(cache)
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    body, meta = folder / f"{key}.json", folder / f"{key}.meta.json"
    if body.exists() and meta.exists() and not refresh:
        metadata = json.loads(meta.read_text())
        if hashlib.sha256(body.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("Cached response checksum mismatch")
        return json.loads(body.read_text()), json.loads(meta.read_text())
    for attempt in range(4):
        try:
            global _LAST_REQUEST
            with _LOCK:
                time.sleep(max(0, .25 - (time.monotonic() - _LAST_REQUEST)))
                _LAST_REQUEST = time.monotonic()
            response = requests.get(url, timeout=60, headers={"User-Agent": "power-risk-research/0.1"})
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            payload = response.json()
            metadata = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "sha256": hashlib.sha256(response.content).hexdigest(),
                        "status_code": response.status_code}
            body.write_bytes(response.content)
            meta.write_text(json.dumps(metadata, indent=2))
            time.sleep(0.25)
            return payload, metadata
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            LOG.warning("HTTP retry %s", attempt + 1)
            time.sleep(2 ** attempt)

