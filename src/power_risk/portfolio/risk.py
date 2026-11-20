"""Hypothetical exposure scenarios. Positive P&L is favorable for either side."""
from pathlib import Path

import numpy as np
import pandas as pd

from power_risk.reporting.research import html_report


def scenario_pnl(prices, exposure_mw, duration_hours, reference_price, side="purchase"):
    prices = np.asarray(prices, dtype=float)
    exposure = np.asarray(exposure_mw, dtype=float)
    duration = np.asarray(duration_hours, dtype=float)
    if side not in {"purchase", "generation"}:
        raise ValueError("side must be purchase or generation")
    if not all(np.isfinite(x).all() for x in [prices, exposure, duration, np.asarray(reference_price)]):
        raise ValueError("All scenario inputs must be observed finite numbers")
    if (exposure < 0).any() or (duration <= 0).any():
        raise ValueError("Exposure must be nonnegative; durations positive")
    sign = -1 if side == "purchase" else 1
    return sign * (prices - reference_price) * exposure * duration


def risk_summary(pnl, alpha=.95):
    pnl = np.asarray(pnl, dtype=float)
    if not 0 < alpha < 1 or pnl.size == 0 or not np.isfinite(pnl).all():
        raise ValueError("Finite nonempty scenarios and 0<alpha<1 required")
    losses = -pnl
    var = float(np.quantile(losses, alpha))
    # Fractional tail mass: empirical integral of the loss quantile function.
    ordered = np.sort(losses)[::-1]
    mass = (1 - alpha) * len(ordered)
    whole = int(np.floor(mass))
    tail = ordered[:whole].sum()
    if whole < len(ordered):
        tail += (mass - whole) * ordered[whole]
    return {"scenarios": len(pnl), "confidence": alpha, "mean_pnl_eur": float(pnl.mean()),
            "var_loss_eur": var, "expected_shortfall_loss_eur": float(tail / mass)}


def daily_scenarios(hourly, exposure=1., reference=100., side="purchase", hours=24):
    """Nonoverlapping complete UTC-day blocks; 24h horizon, not local delivery days."""
    if hours != 24:
        raise ValueError("This historical sampler currently supports a 24-hour horizon")
    groups = hourly.price_eur_mwh.groupby(hourly.index.floor("D"))
    rows = []
    for day, values in groups:
        if len(values) == 24 and values.notna().all():
            rows.append({"scenario_start": day, "pnl_eur": scenario_pnl(values, exposure, 1., reference, side).sum()})
    return pd.DataFrame(rows)


def run():
    hourly = pd.read_parquet("data/processed/prices_hourly.parquet")
    scenarios = daily_scenarios(hourly)
    scenarios.to_csv("reports/portfolio_scenarios.csv", index=False)
    result = pd.DataFrame([risk_summary(scenarios.pnl_eur)])
    result.to_csv("reports/portfolio_risk.csv", index=False)
    stress = pd.DataFrame({"price_eur_mwh": [-100., 0., 100., 300., 1000.]})
    stress["pnl_eur"] = scenario_pnl(stress.price_eur_mwh, 1., 24., 100.)
    stress.to_csv("reports/stress_tests.csv", index=False)
    html_report(Path("reports/portfolio_risk_report.html"), "Hypothetical procurement risk",
        "1 MW flat purchase, 24-hour UTC horizon, 100 EUR/MWh reference. P&L=(reference−spot)×MW×hours. "
        "Historical complete-day blocks preserve within-day dependence; equal scenario weights assume historical "
        "representativeness. Loss=−P&L; VaR is the loss quantile; ES averages the worst 5% with fractional tail mass. "
        "Stress prices are deliberately hypothetical, not market observations. No hedge recommendation is implied.",
        {"Historical scenario risk": result, "Hypothetical fixed-price stress": stress})
