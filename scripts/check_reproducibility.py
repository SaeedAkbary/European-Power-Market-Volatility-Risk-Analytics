"""Rerun local research and compare numerical evidence; never download or synthesize data."""
import subprocess
import sys

import pandas as pd

FILES = ["quantified_market_findings.csv", "model_comparison_enhanced.csv", "portfolio_risk_enhanced.csv",
         "renewable_capture_price_analysis.csv", "cross_border_associations.csv"]
before = {name: pd.read_csv("reports/" + name) for name in FILES}
subprocess.run([sys.executable, "scripts/reproduce_upgrade.py"], check=True)
for name in FILES:
    pd.testing.assert_frame_equal(before[name], pd.read_csv("reports/" + name), rtol=1e-12, atol=1e-12)
print("Reproducibility passed for five numerical evidence tables (rtol/atol 1e-12)")
