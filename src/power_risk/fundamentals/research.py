"""Observed physical conditions, transparent conditional comparisons and descriptive models."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from power_risk.backtesting.uncertainty import block_indices
from power_risk.features.calendar import calendar
from power_risk.reporting.research import html_report


def dataset():
    physical = pd.read_parquet("data/processed/fundamentals_hourly.parquet")
    price = pd.read_parquet("data/processed/prices_hourly.parquet")[["price_eur_mwh"]]
    f = price.join(physical).join(calendar(price.index))
    components = ["actual_wind_onshore_mw", "actual_wind_offshore_mw", "actual_solar_mw"]
    f["wind_mw"] = f[components[:2]].sum(axis=1, min_count=2)
    f["renewable_share"] = f[components].sum(axis=1, min_count=3) / f.actual_load_mw.where(f.actual_load_mw > 0)
    f["negative"] = f.price_eur_mwh.lt(0).where(f.price_eur_mwh.notna())
    f["spike"] = f.price_eur_mwh.ge(200).where(f.price_eur_mwh.notna())
    f["de_fr_spread"] = f.price_eur_mwh - f.fr_price_eur_mwh
    f["de_nl_spread"] = f.price_eur_mwh - f.nl_price_eur_mwh
    return f


def bins(frame, variable, outcome, count=5):
    f = frame[[variable, outcome]].dropna().copy()
    f["bin"] = pd.qcut(f[variable], count, duplicates="drop")
    result = f.groupby("bin", observed=True).agg(n=(outcome, "size"), x=(variable, "mean"),
        mean=(outcome, "mean"), median=(outcome, "median"), std=(outcome, "std"))
    return result


def contrast(frame, variable, outcome, title):
    f = frame[[variable, outcome, "market_date"]].dropna().copy()
    lower, upper = f[variable].quantile([.25, .75])
    f["group"] = np.where(f[variable] <= lower, "low", np.where(f[variable] >= upper, "high", "middle"))
    extreme = f[f.group != "middle"]
    mean = extreme.groupby("group")[outcome].mean()
    daily = extreme.pivot_table(index="market_date", columns="group", values=outcome, aggfunc=["sum", "count"], fill_value=0)
    # Reinsert every calendar day; empty strata contribute zero denominator, not zero outcomes.
    daily = daily.reindex(sorted(f.market_date.unique()), fill_value=0)
    rng = np.random.default_rng(42)
    draws = []
    for _ in range(500):
        sample = daily.iloc[block_indices(len(daily), rng)]
        draws.append(sample["sum"]["high"].sum()/sample["count"]["high"].sum() -
                     sample["sum"]["low"].sum()/sample["count"]["low"].sum())
    ci = np.quantile(draws, [.025, .975])
    return {"finding": title, "variable": variable, "outcome": outcome,
        "period_start": str(f.index.min()), "period_end": str(f.index.max()), "complete_rows": len(f),
        "low_threshold": lower, "high_threshold": upper, "low_n": int((extreme.group == "low").sum()),
        "high_n": int((extreme.group == "high").sum()), "low_mean": mean["low"], "high_mean": mean["high"],
        "difference": mean["high"] - mean["low"], "ci_low": ci[0], "ci_high": ci[1],
        "method": "Full-sample descriptive quartiles; 500 moving 7-day block bootstraps; no causal inference"}


def save_figure(fig, filename):
    fig.tight_layout()
    fig.savefig("reports/" + filename, dpi=160, bbox_inches="tight")
    plt.close(fig)


def run():
    f = dataset()
    core = ["price_eur_mwh", "actual_residual_load_mw", "actual_load_mw", "wind_mw", "actual_solar_mw", "renewable_share"]
    clean = f.dropna(subset=core)
    midday = clean.loc[clean.hour.between(10, 15)]
    findings = pd.DataFrame([
        contrast(clean, "actual_residual_load_mw", "price_eur_mwh", "Residual-load price gradient"),
        contrast(clean, "wind_mw", "negative", "Wind and negative-price incidence"),
        contrast(midday, "actual_solar_mw", "price_eur_mwh", "Midday solar-price association"),
        contrast(clean, "actual_load_mw", "spike", "Demand and high-price incidence")])
    findings.to_csv("reports/quantified_market_findings.csv", index=False)
    numeric = clean[core + ["actual_gas_mw", "actual_hard_coal_mw", "actual_lignite_mw", "de_fr_spread", "de_nl_spread"]]
    corr = pd.concat({"pearson": numeric.corr(), "spearman": numeric.corr(method="spearman")})
    corr.to_csv("reports/fundamental_correlations.csv")
    conditions = clean.assign(event=np.where(clean.negative, "negative", np.where(clean.spike, "positive_spike", "ordinary")))
    conditions.groupby("event")[core + ["actual_gas_mw", "actual_hard_coal_mw", "actual_lignite_mw", "de_fr_spread"]].agg(["count", "mean", "median"]).to_csv("reports/extreme_price_fundamentals.csv")
    conditional = []
    for x, y in [("wind_mw", "negative"), ("actual_load_mw", "spike"), ("actual_solar_mw", "price_eur_mwh"),
                 ("actual_residual_load_mw", "price_eur_mwh"), ("renewable_share", "price_eur_mwh")]:
        table = bins(midday if x == "actual_solar_mw" else clean, x, y)
        conditional.append(table.assign(variable=x, outcome=y).reset_index().astype({"bin": "str"}))
    pd.concat(conditional).to_csv("reports/conditional_price_distributions.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.hexbin(clean.actual_residual_load_mw / 1000, clean.price_eur_mwh, gridsize=55, mincnt=1, bins="log", cmap="viridis")
    ax.set(xlabel="German actual residual load (GW)", ylabel="DE-LU day-ahead price (EUR/MWh)", title="Residual load and price | observed association")
    fig.colorbar(im, ax=ax, label="Hourly observations (log scale)")
    save_figure(fig, "residual_load_price_relationship.png")
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, (x, y, label) in zip(axes.flat[:4], [
        ("wind_mw", "negative", "Negative-price share"), ("actual_solar_mw", "price_eur_mwh", "Midday mean price (EUR/MWh)"),
        ("actual_load_mw", "spike", "Price >=200 EUR/MWh share"), ("renewable_share", "price_eur_mwh", "Price std (EUR/MWh)")]):
        b = bins(midday if x == "actual_solar_mw" else clean, x, y)
        ax.plot(b.x / (1000 if x.endswith("_mw") else 1), b["std" if x == "renewable_share" else "mean"], marker="o", color="#087e8b")
        ax.set(xlabel=x.replace("_mw", " (GW)").replace("_", " "), ylabel=label)
    means = conditions.groupby("event")[["actual_load_mw", "actual_residual_load_mw", "wind_mw", "actual_solar_mw"]].mean() / 1000
    means.plot.bar(ax=axes[1, 1], rot=0, legend=False)
    axes[1, 1].set(ylabel="Mean physical conditions (GW)", xlabel="Price event")
    axes[1, 1].legend(["load", "residual", "wind", "solar"], fontsize=7)
    clean.groupby("season")[["de_fr_spread", "de_nl_spread"]].mean().plot.bar(ax=axes[1, 2], rot=0)
    axes[1, 2].set(ylabel="Mean DE minus neighbor price (EUR/MWh)", xlabel="Season")
    save_figure(fig, "renewable_price_analysis.png")
    # Calendar-controlled explanatory models; actual physical variables are expressly retrospective.
    predictors = ["actual_residual_load_mw", "wind_mw", "actual_solar_mw", "actual_gas_mw", "actual_hard_coal_mw", "actual_lignite_mw"]
    model_frame = clean.dropna(subset=predictors)
    calendar_x = pd.get_dummies(model_frame[["hour", "weekday", "month"]].astype(str), dtype=float)
    x = pd.concat([model_frame[predictors], calendar_x], axis=1)
    y = model_frame.price_eur_mwh
    train = x.index < pd.Timestamp("2025-01-01", tz="Europe/Berlin")
    scores, importances = [], []
    for name, model in [("calendar_controlled_ridge", make_pipeline(StandardScaler(), Ridge(alpha=10))),
                         ("calendar_controlled_boosting", HistGradientBoostingRegressor(max_iter=80, max_leaf_nodes=15,
                            min_samples_leaf=48, early_stopping=False, random_state=42))]:
        model.fit(x.loc[train], y.loc[train])
        scores.append({"model": name, "holdout_mae": mean_absolute_error(y.loc[~train], model.predict(x.loc[~train])),
                       "train_rows": int(train.sum()), "holdout_rows": int((~train).sum())})
        imp = permutation_importance(model, x.loc[~train], y.loc[~train], scoring="neg_mean_absolute_error", n_repeats=3, random_state=42)
        importances.extend({"model": name, "feature": feature, "mae_increase": mean, "repeat_std": std}
                           for feature, mean, std in zip(x.columns, imp.importances_mean, imp.importances_std))
    pd.DataFrame(importances).to_csv("reports/feature_importance.csv", index=False)
    pd.DataFrame(scores).to_csv("reports/fundamental_explanatory_models.csv", index=False)
    seasonal = clean.groupby("season")[core].agg(["count", "mean", "std"])
    seasonal.to_csv("reports/seasonal_fundamentals.csv")
    borders = ["physical_fr_net_import_mw", "commercial_fr_net_import_mw", "de_fr_spread"]
    border_tables = {}
    if all(c in f for c in borders):
        border_sample = f[["price_eur_mwh"] + borders]
        border_tables["French border: complete aligned descriptive associations"] = border_sample.corr(method="spearman")
        border_sample.corr(method="spearman").to_csv("reports/cross_border_associations.csv")
        border_sample.count().to_csv("reports/cross_border_coverage.csv", header=["observed_hours"])
    daily = clean.groupby("market_date").agg(price_min=("price_eur_mwh", "min"), price_max=("price_eur_mwh", "max"),
        renewable_share=("renewable_share", "mean"), residual_load=("actual_residual_load_mw", "mean"), n=("price_eur_mwh", "count"))
    expected = [((pd.Timestamp(d, tz="Europe/Berlin") + pd.DateOffset(days=1)) - pd.Timestamp(d, tz="Europe/Berlin")).total_seconds()/3600 for d in daily.index]
    daily = daily.loc[daily.n.to_numpy() == expected]
    daily["spread"] = daily.price_max - daily.price_min
    daily.to_csv("reports/daily_fundamental_volatility.csv")
    html_report("reports/volatility_fundamental_relationships.html", "Volatility conditional on physical conditions",
        "Retrospective hourly-equivalent prices. Full-sample bins are descriptive. Daily spreads require complete local days including DST. "
        "Wind/solar share is generation divided by grid load, not an installed-capacity factor; it can exceed one.",
        {"Renewable share and price dispersion": bins(clean, "renewable_share", "price_eur_mwh"),
         "Residual load and price dispersion": bins(clean, "actual_residual_load_mw", "price_eur_mwh"),
         "Daily renewable share and spread": daily[["renewable_share", "spread"]].corr(method="spearman")})
    description = (f"Actual SMARD data; {len(clean)} complete hourly rows out of {len(f)}. Source: Bundesnetzagentur | SMARD.de. "
        "Germany physical variables explain DE-LU prices retrospectively; Luxembourg is not included in these load/generation totals. "
        "High/low comparisons use full-sample top/bottom quartiles and moving seven-day block confidence intervals. "
        "Hour, weekday and month are controlled in separate explanatory models trained before 2025, held out afterward. "
        "Seasonal/fuel-price, outage, dispatch and cross-border confounding remain; simultaneous conventional output is endogenous. "
        "Permutation importance is descriptive and unstable under correlated predictors; not a causal effect or ex-ante forecast. "
        "Nuclear is excluded from models because its series has extensive missing observations; none are filled with zero.")
    html_report("reports/fundamental_driver_analysis.html", "German electricity price formation: observed evidence", description,
        {"Quantified comparisons": findings, "Explanatory holdout": pd.DataFrame(scores), "Seasonal physical conditions": seasonal, **border_tables})
    path = Path("reports/fundamental_driver_analysis.html")
    path.write_text(path.read_text(encoding="utf-8").replace("</html>",
        '<h2>Observed relationships</h2><img style="width:100%" src="residual_load_price_relationship.png">'
        '<img style="width:100%" src="renewable_price_analysis.png"></html>'), encoding="utf-8")
    Path("reports/fundamental_research_summary.json").write_text(json.dumps({"rows": len(clean), "start": str(clean.index.min()),
        "end": str(clean.index.max()), "forecast_vintages_verified": False}, indent=2))
    print(findings.to_string(index=False))
    return findings
