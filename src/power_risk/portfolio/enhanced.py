"""Hypothetical purchaser and national-shape renewable portfolios at native delivery resolution."""
import numpy as np
import pandas as pd

from power_risk.features.calendar import calendar
from power_risk.portfolio.risk import risk_summary, scenario_pnl
from power_risk.reporting.research import html_report


def capture_price(price, mw, hours):
    price, mw, hours = [np.asarray(x, dtype=float) for x in [price, mw, hours]]
    if not all(np.isfinite(x).all() for x in [price, mw, hours]) or (mw < 0).any() or (hours <= 0).any():
        raise ValueError("Capture price requires finite prices, nonnegative MW, positive durations")
    energy = mw * hours
    if energy.sum() == 0:
        return np.nan
    return float((price * energy).sum() / energy.sum())


def prices_on_quarters(prices, index):
    """Apply an hourly contract within its known duration; never carry through missing intervals."""
    left = pd.DataFrame({"quarter_start": index}).sort_values("quarter_start")
    right = prices[["delivery_start", "delivery_end", "price_eur_mwh"]].sort_values("delivery_start")
    joined = pd.merge_asof(left, right, left_on="quarter_start", right_on="delivery_start", direction="backward")
    return joined.price_eur_mwh.where(joined.quarter_start < joined.delivery_end).set_axis(index)


def run(reference=100.):
    physical = pd.read_parquet("data/processed/fundamentals_native.parquet")
    price = prices_on_quarters(pd.read_parquet("data/processed/prices.parquet"), physical.index)
    cal = calendar(physical.index)
    regimes = pd.read_parquet("reports/market_regimes.parquet").regime
    wind = physical[["actual_wind_onshore_mw", "actual_wind_offshore_mw"]].sum(axis=1, min_count=2)
    solar = physical.actual_solar_mw
    profiles = {"purchaser": pd.Series(1., index=physical.index), "solar": solar / solar.max(), "wind": wind / wind.max()}
    scenarios, captures, periods = [], [], []
    for case, profile in profiles.items():
        f = cal.copy()
        f["price"] = price
        f["exposure_mw"] = profile
        f["regime"] = regimes.reindex(f.index.floor("h")).to_numpy()
        f = f.dropna(subset=["price", "exposure_mw"])
        f["mwh"] = f.exposure_mw * .25
        f["spot_cash_eur"] = f.price * f.mwh
        f["pnl_eur"] = scenario_pnl(f.price, f.exposure_mw, .25, reference,
                                    "purchase" if case == "purchaser" else "generation")
        f["negative_mwh"] = f.mwh.where(f.price < 0, 0.)
        f["spike_pnl_eur"] = f.pnl_eur.where(f.price >= 200, 0.)
        for period, group in [("all", f), *list(f.groupby("season"))]:
            captures.append({"case": case, "period": period, "intervals": len(group), "energy_mwh": group.mwh.sum(),
                "capture_price_eur_mwh": capture_price(group.price, group.exposure_mw, .25),
                "baseload_price_eur_mwh": group.price.mean(), "negative_energy_share": group.negative_mwh.sum()/group.mwh.sum(),
                "spot_cash_eur": group.spot_cash_eur.sum(), "reference_eur_mwh": reference})
        hourly = f.groupby("hour").agg(energy_mwh=("mwh", "sum"), spot_cash_eur=("spot_cash_eur", "sum"),
            pnl_eur=("pnl_eur", "sum"), negative_mwh=("negative_mwh", "sum"))
        periods.append(hourly.assign(case=case).reset_index())
        for day, g in f.groupby("market_date"):
            start = pd.Timestamp(day, tz="Europe/Berlin")
            expected = int(((start + pd.DateOffset(days=1)) - start).total_seconds()/900)
            if len(g) != expected:
                continue
            scenarios.append({"case": case, "market_date": day, "season": g.season.iloc[0], "regime": g.regime.iloc[0],
                "intervals": len(g), "energy_mwh": g.mwh.sum(), "pnl_eur": g.pnl_eur.sum(),
                "spot_cash_eur": g.spot_cash_eur.sum(), "spike_pnl_eur": g.spike_pnl_eur.sum(),
                "negative_mwh": g.negative_mwh.sum()})
    scenarios = pd.DataFrame(scenarios)
    scenarios.to_csv("reports/portfolio_scenario_comparison.csv", index=False)
    pd.concat(periods).to_csv("reports/portfolio_delivery_exposure.csv", index=False)
    pd.DataFrame(captures).to_csv("reports/renewable_capture_price_analysis.csv", index=False)
    risks = []
    for case, sample in scenarios.groupby("case"):
        risks.append({"case": case, "grouping": "all", "group": "all", **risk_summary(sample.pnl_eur)})
        for key in ["season", "regime"]:
            for group, block in sample.groupby(key):
                risks.append({"case": case, "grouping": key, "group": group, **risk_summary(block.pnl_eur)})
    risk = pd.DataFrame(risks)
    risk.to_csv("reports/portfolio_risk_enhanced.csv", index=False)
    html_report("reports/portfolio_risk_report_enhanced.html", "Purchaser, solar and wind exposure",
        "HYPOTHETICAL portfolios: purchaser 1 MW flat; generators follow observed German aggregate solar/wind output "
        "scaled to 1 MW at the full-sample observed peak, not installed capacity or an individual plant. Renewable "
        "capture price is sum(price × MWh)/sum(MWh); it excludes subsidy, fees, curtailment decisions, imbalance and "
        "basis risk. MW × 0.25 gives MWh. Before the MTU change, the known hourly contract applies to its four quarters; "
        "afterward genuine quarter-hour prices are used. No missing prices are forward-filled beyond contract end. "
        "Reference 100 EUR/MWh: generation P&L=(spot-reference)×MWh; purchaser reverses sign. Loss=-P&L. "
        "Scenarios are complete local delivery days (23/24/25 hours), so horizon varies on DST days. Regime is the "
        "first-hour descriptive state, including calibration-year states. VaR/ES assume historical days are representative; "
        "small regime strata imply unstable tails. Equal peak scaling does not equalize energy or commercial risk.",
        {"Full-sample risk": risk[risk.grouping == "all"], "Capture economics": pd.DataFrame(captures),
         "Seasonal and regime risk": risk[risk.grouping != "all"]})
    return risk
