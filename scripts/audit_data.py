"""Run the real-data availability audit without requiring the console entrypoint."""
import argparse

from power_risk.ingestion.audit import run

parser = argparse.ArgumentParser()
parser.add_argument("--start", default="2023-01-01")
parser.add_argument("--end", default="2026-11-19", help="Exclusive local delivery date")
args = parser.parse_args()
print(run(args.start, args.end).to_string(index=False))
