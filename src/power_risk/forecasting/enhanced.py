"""Rolling calibration on strictly earlier out-of-sample forecasts."""
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from power_risk.backtesting.uncertainty import daily_ratio_ci
from power_risk.backtesting.validation import calibration, summarize
from power_risk.features.calendar import calendar
from power_risk.reporting.research import html_report


def conformal_expansion(calibration_frame, alpha=.2):
    scores = np.maximum.reduce([calibration_frame.q10 - calibration_frame.actual,
                               calibration_frame.actual - calibration_frame.q90,
                               np.zeros(len(calibration_frame))])
    if len(scores) < 100 or not np.isfinite(scores).all():
        raise ValueError("At least 100 finite calibration errors required")
    rank = min(len(scores), int(np.ceil((len(scores) + 1) * (1 - alpha))))
    return float(np.sort(scores)[rank - 1])


def calibrate_month(history, test, cutoff):
    if history.index.max() >= cutoff or test.index.min() <= cutoff:
        raise ValueError("Calibration observations must precede issuance cutoff and test")
    out = test.copy()
    expansion = conformal_expansion(history)
    out["q10"] -= expansion
    out["q90"] += expansion
    for probability, event in [("p_negative", history.actual.lt(0)), ("p_spike", history.actual.ge(200))]:
        if event.nunique() == 2:
            fitted = IsotonicRegression(out_of_bounds="clip").fit(history[probability], event.astype(int))
            out[probability] = fitted.predict(test[probability])
    out["calibration_last_observation"] = history.index.max()
    out["interval_expansion"] = expansion
    return out


def run():
    original = pd.read_parquet("reports/price_risk_forecasts.parquet")
    cutoff_test = pd.Timestamp("2025-01-01", tz="Europe/Berlin")
    output, log = [], []
    for name, frame in original.groupby("model"):
        frame = frame.sort_index()
        months = sorted(set(frame.loc[frame.index >= cutoff_test].index.tz_convert("Europe/Berlin").strftime("%Y-%m")))
        for month in months:
            first = pd.Timestamp(month + "-01", tz="Europe/Berlin")
            cutoff = (first - pd.DateOffset(days=1) + pd.Timedelta(hours=11)).tz_convert("UTC")
            history = frame.loc[(frame.index < cutoff) & (frame.index >= cutoff - pd.Timedelta(days=90))]
            test = frame.loc[(frame.index >= first) & (frame.index < first + pd.offsets.MonthBegin(1))]
            calibrated = calibrate_month(history, test, cutoff)
            before = test.copy()
            before["model"] = name + " / original"
            calibrated["model"] = name + " / calibrated"
            output.extend([before, calibrated])
            log.append({"base_model": name, "month": month, "cutoff": cutoff, "calibration_rows": len(history),
                        "calibration_start": history.index.min(), "calibration_end": history.index.max(),
                        "test_start": test.index.min(), "test_end": test.index.max(),
                        "expansion_eur_mwh": calibrated.interval_expansion.iloc[0]})
    f = pd.concat(output).sort_index()
    f.to_parquet("reports/price_risk_forecasts_enhanced.parquet")
    pd.DataFrame(log).to_csv("reports/calibration_windows.csv", index=False)
    scores = summarize(f)
    scores["mae"] = scores.model.map(f.assign(error=(f.actual - f.q50).abs()).groupby("model").error.mean())
    intervals = []
    for model, part in f.groupby("model"):
        days = part.index.tz_convert("Europe/Berlin").strftime("%Y-%m-%d")
        covered = ((part.actual >= part.q10) & (part.actual <= part.q90)).astype(int)
        daily = pd.DataFrame({"covered": covered.to_numpy(), "count": 1}, index=days).groupby(level=0).sum()
        lo, hi = daily_ratio_ci(daily.covered, daily["count"])
        intervals.append({"model": model, "coverage_ci_low": lo, "coverage_ci_high": hi})
    scores = scores.merge(pd.DataFrame(intervals), on="model")
    scores.to_csv("reports/model_comparison_enhanced.csv", index=False)
    scores[["model", "observations", "coverage_80", "mean_width", "coverage_ci_low", "coverage_ci_high"]].to_csv("reports/calibration_results.csv", index=False)
    calibration(f).to_csv("reports/probability_calibration_enhanced.csv", index=False)
    cal = calendar(f.index)
    for key in ["hour", "season"]:
        temp = f.assign(**{key: cal[key].to_numpy()})
        pd.concat([summarize(g).assign(**{key: label}) for label, g in temp.groupby(key)]).to_csv(f"reports/enhanced_by_{key}.csv", index=False)
    comparison = scores.assign(feature_group="price_only", status="EXPLORATORY_LATEST_PRICE_SNAPSHOT")
    unavailable = pd.DataFrame([{"model": "fundamental_enhanced", "feature_group": "load/wind/solar forecasts",
        "status": "BLOCKED: original publication/vintage times unverified; generation may arrive after cutoff"}])
    pd.concat([comparison, unavailable], ignore_index=True).to_csv("reports/price_only_vs_fundamental.csv", index=False)
    html_report("reports/forecast_validation_enhanced.html", "Forecast calibration on past predictions",
        "Original models preserved. 2024 initializes calibration; evaluation starts 1 January 2025. Each month uses "
        "only the prior 90 days of out-of-sample errors before D-1 11:00 Berlin. Interval expansion uses the finite-sample "
        "80th percentile of max(q10-y,y-q90,0); probability calibration uses isotonic regression on the same past window. "
        "No current-month labels used. Earlier evaluation months become available history in later folds, a prequential "
        "protocol rather than a permanently locked holdout. Settings fixed before this experiment. Confidence intervals "
        "use 500 moving seven-day block resamples of daily coverage totals; serial dependence and regime drift prevent "
        "a distribution-free time-series coverage guarantee. No admissible fundamental model is claimed without vintages.",
        {"Common-sample comparison": scores, "Calibration windows": pd.DataFrame(log), "Fundamental comparison status": unavailable})
    return scores
