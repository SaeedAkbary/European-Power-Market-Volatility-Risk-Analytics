"""Retrospective drivers only; no causal or ex-ante claims."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from power_risk.reporting.research import html_report

COMPONENTS = ["load_mw", "wind_onshore_mw", "wind_offshore_mw", "solar_mw"]


def residual_load(frame, prefix="actual_"):
    cols = [prefix + c for c in COMPONENTS]
    f = frame[cols]
    return (f.iloc[:, 0] - f.iloc[:, 1:].sum(axis=1, min_count=3)).where(f.notna().all(axis=1))


def run(path="data/processed/fundamentals_hourly.parquet"):
    if not Path(path).exists():
        html_report("reports/fundamental_driver_analysis.html", "Fundamental drivers — data pending",
            "No validated ENTSO-E load, renewable generation, fuel mix or border data are available. "
            "No fundamental findings or feature importance are reported. Configure the free token, retrieve XML, "
            "validate units/categories and produce the documented normalized input before running this module.", {})
        return False
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error
    frame = pd.read_parquet(path).sort_index()
    if frame.index.tz is None or frame.index.has_duplicates:
        raise ValueError("Unique timezone-aware delivery index required")
    frame["residual_load_mw"] = residual_load(frame)
    prices = pd.read_parquet("data/processed/prices_hourly.parquet")
    joined = prices[["price_eur_mwh"]].join(frame)
    features = [c for c in frame.select_dtypes("number").columns if c != "price_eur_mwh"]
    complete = joined.dropna(subset=features + ["price_eur_mwh"])
    if len(complete) < 1000:
        raise ValueError("At least 1000 complete aligned observations required")
    split = int(len(complete) * .8)
    train, test = complete.iloc[:split], complete.iloc[split:]
    results, importance = [], []
    for name, model in [("linear", LinearRegression()),
                        ("random_forest", RandomForestRegressor(n_estimators=100, min_samples_leaf=24, random_state=42))]:
        model.fit(train[features], train.price_eur_mwh)
        results.append({"model": name, "retrospective_holdout_mae": mean_absolute_error(test.price_eur_mwh, model.predict(test[features]))})
        imp = permutation_importance(model, test[features], test.price_eur_mwh,
                                     scoring="neg_mean_absolute_error", n_repeats=5, random_state=42)
        importance.extend({"model": name, "feature": c, "holdout_mae_increase": v}
                          for c, v in zip(features, imp.importances_mean))
    pd.DataFrame(importance).to_csv("reports/feature_importance.csv", index=False)
    fig, ax = plt.subplots()
    ax.hexbin(complete.residual_load_mw, complete.price_eur_mwh, gridsize=50, mincnt=1)
    ax.set(xlabel="Actual residual load (MW)", ylabel="Day-ahead price (EUR/MWh)")
    fig.tight_layout()
    fig.savefig("reports/residual_load_price_relationship.png", dpi=160)
    plt.close(fig)
    html_report("reports/fundamental_driver_analysis.html", "Retrospective fundamental associations",
        f"Complete-case rows: {len(complete)} of {len(joined)}. Chronological 80/20 descriptive holdout; "
        "actual fundamentals are unavailable before clearing. Correlation, regression and permutation importance "
        "do not establish causality; correlated predictors complicate importance interpretation.",
        {"Holdout": pd.DataFrame(results), "Spearman associations": complete.corr(method="spearman")})
    return True
