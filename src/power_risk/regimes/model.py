import numpy as np
import pandas as pd

from power_risk.reporting.research import html_report

LABELS = ["Low", "Normal", "Elevated", "Extreme"]


def classify(volatility, training_end):
    train = volatility.loc[volatility.index < pd.Timestamp(training_end)].dropna()
    if len(train) < 168:
        raise ValueError("Insufficient regime calibration history")
    thresholds = train.quantile([.25, .75, .95]).to_numpy()
    result = pd.Series(pd.NA, index=volatility.index, dtype="string", name="regime")
    valid = volatility.notna()
    result.loc[valid] = np.asarray(LABELS)[np.searchsorted(thresholds, volatility.loc[valid], side="right")]
    return result, thresholds


def run():
    f = pd.read_parquet("reports/volatility_metrics.parquet")
    cutoff = pd.Timestamp("2024-01-01", tz="Europe/Berlin").tz_convert("UTC")
    # Lagged 7d volatility is a descriptive online state, not a next-day issuance feature.
    regime, thresholds = classify(f.rolling_std_7d.shift(), cutoff)
    frame = pd.DataFrame({"regime": regime, "volatility": f.rolling_std_7d.shift(), "season": f.season})
    frame["sample"] = np.where(frame.index < cutoff, "calibration", "evaluation")
    frame.to_parquet("reports/market_regimes.parquet")
    evaluation = frame.loc[frame.index >= cutoff]
    transition = pd.crosstab(evaluation.regime.shift(), evaluation.regime, normalize="index").reindex(index=LABELS, columns=LABELS)
    transition.to_csv("reports/regime_transitions.csv")
    html_report("reports/regime_analysis.html", "Interpretable volatility states",
        f"2023 calibration cutpoints (EUR/MWh): {thresholds.tolist()}. Fixed 25th/75th/95th percentiles of "
        "lagged 7-day price standard deviation. Evaluation begins 2024. Hourly self-transition probabilities "
        "reflect overlapping windows and should not be read as independent regime evidence. No future smoothing. "
        "Fundamental-state associations await ENTSO-E data; advanced latent-state models are not implemented.",
        {"Hourly transition probabilities": transition, "Evaluation frequency": evaluation.regime.value_counts(normalize=True).to_frame("share"),
         "Seasonal frequency": pd.crosstab(evaluation.season, evaluation.regime, normalize="index")})
