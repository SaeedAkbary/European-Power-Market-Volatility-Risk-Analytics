"""Local five-page research dashboard. Run from repository root."""
from pathlib import Path

import pandas as pd
import streamlit as st

from power_risk.portfolio.risk import daily_scenarios, risk_summary, scenario_pnl

st.set_page_config(page_title="German Power Market Risk", layout="wide")
st.title("European Power Market Volatility & Risk Analytics")
st.caption("DE-LU • €0 public-data workflow • Source: Bundesnetzagentur | SMARD.de")
page = st.sidebar.radio("Research page", ["Market Overview", "Volatility Monitor", "Fundamental Drivers",
                                         "Probabilistic Forecasting", "Portfolio Risk"])
st.sidebar.caption("Historical analysis, exploratory forecasts and hypothetical scenarios are labelled separately.")


@st.cache_data
def parquet(path, modified):
    return pd.read_parquet(path)


def load(path):
    if not Path(path).exists():
        st.info(f"Output not generated yet: {path}. Run the documented pipeline commands.")
        st.stop()
    return parquet(path, Path(path).stat().st_mtime_ns)


if page == "Market Overview":
    st.subheader("Actual market observations — historical")
    frame = load("reports/volatility_metrics.parquet")
    st.metric("Hourly-equivalent average price", f"€{frame.price_eur_mwh.mean():.2f}/MWh")
    st.line_chart(frame.price_eur_mwh.resample("D").mean(), y_label="EUR/MWh (UTC daily mean)")
    st.dataframe(frame.groupby("season").price_eur_mwh.agg(["count", "mean", "std"]))
    st.image("reports/price_distribution.png")
    st.caption("Post-transition prices are complete hourly averages. Native negative durations appear in the event report.")
elif page == "Volatility Monitor":
    st.subheader("Historical volatility and extreme events")
    frame = load("reports/volatility_metrics.parquet")
    st.line_chart(frame[["rolling_std_7d", "bollinger_upper", "bollinger_lower"]].resample("D").last())
    st.image("reports/volatility_heatmap.png")
    if Path("reports/negative_price_events.csv").exists():
        st.dataframe(pd.read_csv("reports/negative_price_events.csv"))
    if Path("reports/regime_transitions.csv").exists():
        st.caption("Lagged volatility states; cutpoints fixed using 2023 calibration.")
        st.dataframe(pd.read_csv("reports/regime_transitions.csv", index_col=0))
    if Path("reports/intrahour_metrics.csv").exists():
        st.subheader("Observed native quarter-hour risk")
        native = pd.read_csv("reports/intrahour_metrics.csv", index_col=0, parse_dates=True)
        st.line_chart(native[["min", "mean", "max"]].tail(24 * 14))
        st.caption("Min/max are genuine quarter-hour prices within each hour; mean is the hourly-equivalent price. Averaging conceals intrahour events.")
elif page == "Fundamental Drivers":
    st.subheader("Observed German physical fundamentals")
    if not Path("data/processed/fundamentals_hourly.parquet").exists():
        st.info("Run power-risk fundamentals to retrieve free SMARD inputs.")
        st.stop()
    fundamentals = load("data/processed/fundamentals_hourly.parquet")
    columns = ["actual_load_mw", "actual_residual_load_mw", "actual_wind_onshore_mw", "actual_wind_offshore_mw", "actual_solar_mw"]
    st.line_chart(fundamentals[columns].tail(24 * 14) / 1000, y_label="GW")
    st.caption("DE physical area; DE-LU price area. Actual and forecast series remain separate. Provider estimates and revised snapshots may be included.")
    if Path("reports/quantified_market_findings.csv").exists():
        st.dataframe(pd.read_csv("reports/quantified_market_findings.csv"))
        st.image("reports/residual_load_price_relationship.png")
        st.image("reports/renewable_price_analysis.png")
    st.dataframe(pd.read_csv("reports/fundamental_data_quality.csv"))
    st.warning("These are retrospective associations, not causal estimates or forecasts available before clearing.")
elif page == "Probabilistic Forecasting":
    st.subheader("Exploratory historical forecasts")
    st.warning("Source publication/revision history is unverified. This backtest is not an executable trading strategy.")
    enhanced = Path("reports/price_risk_forecasts_enhanced.parquet").exists()
    frame = load("reports/price_risk_forecasts_enhanced.parquet" if enhanced else "reports/price_risk_forecasts.parquet")
    model = st.selectbox("Model", sorted(frame.model.unique()))
    selection = frame.loc[frame.model.eq(model)].tail(24 * 14)
    st.line_chart(selection[["actual", "q10", "q50", "q90"]])
    st.line_chart(selection[["p_negative", "p_spike"]])
    st.dataframe(pd.read_csv("reports/model_comparison_enhanced.csv" if enhanced else "reports/model_comparison.csv"))
    st.dataframe(pd.read_csv("reports/probability_calibration_enhanced.csv" if enhanced else "reports/probability_calibration.csv"))
    if enhanced:
        st.caption("2025 onward common test sample; each calibration window uses only earlier out-of-sample errors. Wider intervals improve coverage but probability calibration is not uniformly better.")
        st.dataframe(pd.read_csv("reports/price_only_vs_fundamental.csv"))
else:
    st.subheader("Hypothetical portfolio scenarios")
    side = st.selectbox("Position", ["purchase", "generation"])
    exposure = st.number_input("Flat exposure (MW)", min_value=0., value=1.)
    reference = st.number_input("Contract/reference price (EUR/MWh)", value=100.)
    confidence = st.slider("VaR / ES confidence", .90, .99, .95)
    if Path("reports/portfolio_scenario_comparison.csv").exists():
        st.subheader("Purchaser versus renewable-shaped portfolios")
        case = st.selectbox("Commercial case", ["purchaser", "solar", "wind"])
        observations = pd.read_csv("reports/portfolio_scenario_comparison.csv")
        observations = observations.loc[observations.case.eq(case)].copy()
        sign = -1 if case == "purchaser" else 1
        observations["pnl_eur"] = sign * (observations.spot_cash_eur - reference * observations.energy_mwh) * exposure
        st.dataframe(pd.DataFrame([risk_summary(observations.pnl_eur, confidence)]))
        capture = pd.read_csv("reports/renewable_capture_price_analysis.csv")
        st.dataframe(capture.loc[capture.case.eq(case)])
        st.caption("Renewable profiles follow observed German aggregate production, scaled to a 1 MW observed peak before applying the exposure multiplier. They are hypothetical, not plant returns. Enhanced cases use complete local days including DST; the legacy illustration below uses fixed UTC-day blocks.")
        st.dataframe(pd.read_csv("reports/portfolio_risk_enhanced.csv").query("case == @case"))
    st.caption("Historical sampler: complete, nonoverlapping 24-hour UTC blocks; daily exposure shape is flat.")
    hourly = load("data/processed/prices_hourly.parquet")
    scenarios = daily_scenarios(hourly, exposure, reference, side)
    st.dataframe(pd.DataFrame([risk_summary(scenarios.pnl_eur, confidence)]))
    st.bar_chart(scenarios.set_index("scenario_start").pnl_eur)
    st.markdown("Custom interval scenario: CSV columns `price_eur_mwh`, `exposure_mw`, `duration_hours`. Supports hourly or quarter-hourly exposure and an arbitrary horizon.")
    uploaded = st.file_uploader("Upload hypothetical exposure/price scenario", type="csv")
    if uploaded is not None:
        try:
            custom = pd.read_csv(uploaded)
            custom["pnl_eur"] = scenario_pnl(custom.price_eur_mwh, custom.exposure_mw, custom.duration_hours, reference, side)
            st.metric("Scenario P&L", f"€{custom.pnl_eur.sum():,.2f}")
            st.dataframe(custom)
        except (ValueError, AttributeError, KeyError) as exc:
            st.error(f"Invalid input: {exc}")
    st.caption("Purchase P&L=(reference−spot)×MW×hours; generation reverses the sign. Loss=−P&L. Historical representativeness is an assumption; no optimal hedge is implied.")
