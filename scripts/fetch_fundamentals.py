import argparse

from power_risk.ingestion.fundamentals import run

parser = argparse.ArgumentParser()
parser.add_argument("--start", default="2023-01-01")
parser.add_argument("--end", default="2026-11-19")
args = parser.parse_args()
run(args.start, args.end)
