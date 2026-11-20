import argparse
import logging


def main():
    parser = argparse.ArgumentParser(description="Free German power-market research")
    parser.add_argument("command", choices=["audit", "analyze", "forecast", "portfolio", "fundamentals", "drivers", "native", "calibrate", "portfolio-enhanced"])
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-11-19", help="exclusive local market date")
    parser.add_argument("--advanced", action="store_true", help="Include sklearn quantile and boosting models")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.command == "audit":
        from power_risk.ingestion.audit import run
        print(run(args.start, args.end).to_string(index=False))
    elif args.command == "analyze":
        from power_risk.reporting.research import run
        run()
    elif args.command == "forecast":
        from power_risk.forecasting.models import run
        run(advanced=args.advanced)
    elif args.command == "portfolio":
        from power_risk.portfolio.risk import run
        run()
    elif args.command == "fundamentals":
        from power_risk.ingestion.fundamentals import run
        run(args.start, args.end)
    elif args.command == "drivers":
        from power_risk.fundamentals.research import run
        run()
    elif args.command == "native":
        from power_risk.volatility.native import run
        run()
    elif args.command == "calibrate":
        from power_risk.forecasting.enhanced import run
        run()
    else:
        from power_risk.portfolio.enhanced import run
        run()


if __name__ == "__main__":
    main()
