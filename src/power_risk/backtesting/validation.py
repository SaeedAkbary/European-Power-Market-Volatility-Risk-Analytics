import numpy as np
import pandas as pd


def mean_pinball_loss(y, prediction, alpha):
    error = np.asarray(y) - np.asarray(prediction)
    return float(np.maximum(alpha * error, (alpha - 1) * error).mean())


def brier_score_loss(y, probability):
    return float(np.mean((np.asarray(y, dtype=float) - np.asarray(probability)) ** 2))


def average_precision_score(y, probability):
    # Group ties before integrating the stepwise precision-recall curve.
    grouped = pd.DataFrame({"y": np.asarray(y, dtype=int), "p": np.asarray(probability)})
    grouped = grouped.groupby("p").y.agg(["sum", "count"]).sort_index(ascending=False)
    positives = grouped["sum"].sum()
    if not positives:
        return np.nan
    precision = grouped["sum"].cumsum() / grouped["count"].cumsum()
    return float((precision * grouped["sum"] / positives).sum())


def summarize(predictions):
    rows = []
    for name, f in predictions.groupby("model"):
        row = {"model": name, "observations": len(f),
               "coverage_80": ((f.actual >= f.q10) & (f.actual <= f.q90)).mean(),
               "mean_width": (f.q90 - f.q10).mean()}
        for quantile, col in [(.1, "q10"), (.5, "q50"), (.9, "q90")]:
            row[f"pinball_{col}"] = mean_pinball_loss(f.actual, f[col], alpha=quantile)
        for event, probability in [(f.actual < 0, "p_negative"), (f.actual >= 200, "p_spike")]:
            row[f"brier_{probability}"] = brier_score_loss(event, f[probability])
            row[f"average_precision_{probability}"] = average_precision_score(event, f[probability]) if event.any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def calibration(predictions):
    rows = []
    for name, f in predictions.groupby("model"):
        for event, column in [(f.actual < 0, "p_negative"), (f.actual >= 200, "p_spike")]:
            temp = pd.DataFrame({"probability": f[column], "event": event.astype(float)})
            temp["bin"] = pd.cut(temp.probability, np.linspace(0, 1, 11), include_lowest=True)
            for label, group in temp.groupby("bin", observed=True):
                rows.append({"model": name, "event": column, "bin": str(label), "count": len(group),
                             "mean_probability": group.probability.mean(), "event_frequency": group.event.mean()})
    return pd.DataFrame(rows)
