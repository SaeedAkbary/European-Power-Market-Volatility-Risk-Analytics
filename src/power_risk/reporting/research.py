import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from power_risk.spikes.events import negative_runs
from power_risk.validation.quality import hourly_prices
from power_risk.volatility.metrics import calculate


def html_report(path, title, description, tables):
    path = Path(path)
    path.write_text("<!doctype html><html><meta charset='utf-8'><title>" + title +
                   "</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;color:#152c40}"
                   "table{border-collapse:collapse}td,th{padding:7px;border:1px solid #ddd}</style>" +
                   f"<h1>{title}</h1><p>{description}</p>" + "".join(
                       f"<h2>{name}</h2>{table.to_html()}" for name, table in tables.items()) + "</html>", encoding="utf-8")


def run():
    reports = Path("reports")
    native = pd.read_parquet("data/processed/prices.parquet")
    hourly = hourly_prices(native)
    hourly.to_parquet("data/processed/prices_hourly.parquet")
    f, daily = calculate(hourly)
    f.to_parquet(reports / "volatility_metrics.parquet")
    f.to_parquet("data/features/market_features.parquet")
    daily.to_csv(reports / "daily_price_metrics.csv")
    events = f.loc[f.positive_spike.eq(True) | f.quantile_spike.eq(True) | f.sharp_ramp.eq(True)]
    events.to_csv(reports / "extreme_price_events.csv")
    runs = negative_runs(native)
    runs.to_csv(reports / "negative_price_events.csv", index=False)
    valid = native.price_eur_mwh.notna()
    negative_hours = native.loc[valid & native.price_eur_mwh.lt(0), "interval_minutes"].sum() / 60
    summary = {"native_intervals": len(native), "valid_hourly_observations": int(f.price_eur_mwh.count()),
        "mean_hourly_price_eur_mwh": float(f.price_eur_mwh.mean()),
        "native_min_price": float(native.price_eur_mwh.min()), "native_max_price": float(native.price_eur_mwh.max()),
        "negative_price_hours": float(negative_hours),
        "negative_time_share": float(negative_hours / (native.loc[valid, "interval_minutes"].sum() / 60)),
        "negative_episodes": len(runs), "mean_daily_spread": float(daily.spread.mean()),
        "absolute_change_lag1_correlation": float(f.absolute_change.autocorr())}
    (reports / "market_summary.json").write_text(json.dumps(summary, indent=2))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(f.price_eur_mwh.dropna(), bins=100, color="#137c8b")
    ax.set(xlabel="Hourly-equivalent day-ahead price (EUR/MWh)", ylabel="Delivery hours",
           title="DE-LU price distribution | Bundesnetzagentur / SMARD.de")
    fig.tight_layout()
    fig.savefig(reports / "price_distribution.png", dpi=160)
    plt.close(fig)
    matrix = f.pivot_table(index="weekday", columns="hour", values="price_eur_mwh", aggfunc="std")
    fig, ax = plt.subplots(figsize=(12, 4))
    plot = ax.imshow(matrix, aspect="auto", cmap="magma")
    ax.set(yticks=range(7), yticklabels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], xlabel="Europe/Berlin delivery hour",
           title="Price standard deviation by weekday and hour (EUR/MWh)")
    fig.colorbar(plot, ax=ax)
    fig.tight_layout()
    fig.savefig(reports / "volatility_heatmap.png", dpi=160)
    plt.close(fig)
    description = ("Actual SMARD observations; source: Bundesnetzagentur | SMARD.de. Hourly prices after October 2025 "
        "are complete duration-weighted averages. This loses intrahour extremes; negative duration uses native intervals. "
        "No log returns, winsorization or imputation. Price-change clustering is descriptive, not a significance test.")
    html_report(reports / "volatility_report.html", "German electricity volatility", description,
                {"Summary": pd.Series(summary).to_frame("value"),
                 "By season": f.groupby("season").price_eur_mwh.agg(["count", "mean", "std"]),
                 "By hour": f.groupby("hour").price_eur_mwh.agg(["count", "mean", "std"])})
    html_report(reports / "price_spike_analysis.html", "Extreme-price events", description +
        " Fixed spike >=200 EUR/MWh; ramp >=100 EUR/MWh per hour. Rolling 99th percentile uses only prior observations; "
        "90-day window with 30-day warm-up. These are research thresholds, not optimized trading rules.",
        {"Longest native negative-price episodes": runs.sort_values("duration_hours", ascending=False).head(20),
         "Largest complete-day spreads": daily.sort_values("spread", ascending=False).head(20)})
    print(json.dumps(summary, indent=2))
