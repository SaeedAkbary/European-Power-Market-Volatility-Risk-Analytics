"""Local deterministic report workflow; download is opt-in and always uses free sources."""
import argparse
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

parser = argparse.ArgumentParser()
parser.add_argument("--download", action="store_true", help="Retrieve/reuse full-period SMARD fundamentals")
args = parser.parse_args()
if args.download:
    from power_risk.ingestion.fundamentals import run
    run()
from power_risk.fundamentals.research import run as drivers  # noqa: E402
from power_risk.volatility.native import run as native  # noqa: E402
from power_risk.forecasting.enhanced import run as calibrate  # noqa: E402
from power_risk.portfolio.enhanced import run as portfolio  # noqa: E402

drivers()
native()
calibrate()
portfolio()
print("Upgrade research outputs regenerated from actual cached observations")
