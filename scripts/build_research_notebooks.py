"""Generate seven research narratives and module-based analyses with genuine charts."""
from pathlib import Path

import nbformat as nbf

SETUP = """from pathlib import Path
import os
import json
import pandas as pd
from IPython.display import Image, display
root = Path.cwd() if Path('reports').exists() else Path.cwd().parent
os.chdir(root)
"""

# name, question, method/equation, calculation, chart, interpretation, limitation
TOPICS = [
    ("01_market_overview", "How do German price levels and tails differ from average-price budgeting?",
     "Hourly price = sum(price x minutes)/60, only with complete coverage. Retain zero/negative prices and native market intervals.",
     "from power_risk.validation.quality import hourly_prices\nnative = pd.read_parquet('data/processed/prices.parquet')\nhourly = hourly_prices(native)\ndisplay(hourly.price_eur_mwh.describe())\ndisplay(json.loads(Path('reports/market_summary.json').read_text()))",
     "price_distribution.png",
     "The EUR 95.24/MWh average coexists with native prices from -500 to 936.28 EUR/MWh and 5.28% negative delivery time. Purchasers and generators face opposing price-tail exposures; merit-order reasoning alone does not identify causality.",
     "Post-transition hourly averaging hides quarter-hour extremes. Historical price levels are not forward expectations or traded returns."),
    ("02_volatility_diagnostics", "What volatility is concealed by hourly aggregation, and does volatility cluster?",
     "Compute 168-hour rolling standard deviation, prior-same-hour median anomalies and max-minus-min intrahour spreads. Ljung-Box tests use absolute changes and squared hour-adjusted anomalies, not log returns.",
     "from power_risk.volatility.metrics import calculate\nf,daily = calculate(pd.read_parquet('data/processed/prices_hourly.parquet'))\ndisplay(f[['price_eur_mwh','rolling_std_7d','anomaly']].tail())\ndisplay(pd.read_csv('reports/volatility_clustering_tests.csv'))\ndisplay(json.loads(Path('reports/intrahour_summary.json').read_text()))",
     "volatility_heatmap.png",
     "101 hours hide a negative quarter and 357 hide a >=200 EUR/MWh quarter behind an hourly mean outside that event. Mean intrahour spread is EUR 23.90/MWh. Delivery granularity matters for exposure.",
     "Asymptotic clustering tests are affected by nonstationarity/seasonality. Overlapping benchmarks induce dependence. ATR/Bollinger bands are descriptive, not optimal trading rules."),
    ("03_price_spikes", "Which physical conditions accompany positive and negative price extremes?",
     "Events are P<0 and P>=200 EUR/MWh. Consecutive periods must be physically contiguous. Trailing event quantiles use past observations; full-sample physical bins are descriptive rather than prospective thresholds.",
     "from power_risk.spikes.events import negative_runs\nfrom power_risk.fundamentals.research import dataset, bins\ndisplay(negative_runs(pd.read_parquet('data/processed/prices.parquet')).sort_values('duration_hours',ascending=False).head(8))\ndisplay(bins(dataset(), 'actual_load_mw', 'spike'))\ndisplay(pd.read_csv('reports/consecutive_positive_spikes.csv').head())",
     "renewable_price_analysis.png",
     "High-demand quartile spike incidence is 7.48%, versus 0.42% for low demand. High-wind negative-price incidence is 7.20% versus 4.67%. Low residual demand and inflexibility are plausible mechanisms, not identified causal explanations.",
     "Thresholds are fixed research choices. Weather, demand, fuels, outages and cross-border conditions confound comparisons. No paid fuel proxy is silently substituted."),
    ("04_fundamental_drivers", "How are residual load and renewables associated with prices?",
     "RL=load-onshore wind-offshore wind-solar, with all components observed in MW. Descriptive quartiles and Pearson/Spearman correlations are supplemented by calendar-controlled Ridge/boosting with a chronological 2025+ holdout. Moving seven-day bootstrap gives descriptive confidence intervals.",
     "from power_risk.fundamentals.research import dataset,bins\ndisplay(bins(dataset(),'actual_residual_load_mw','price_eur_mwh'))\ndisplay(pd.read_csv('reports/quantified_market_findings.csv'))\ndisplay(pd.read_csv('reports/fundamental_explanatory_models.csv'))\ndisplay(pd.read_csv('reports/feature_importance.csv').sort_values('mae_increase',ascending=False).head(12))",
     "residual_load_price_relationship.png",
     "Upper versus lower residual-load quartiles differ by EUR 113.22/MWh (block CI 106.59-122.54). High-solar midday prices are EUR 88.05/MWh lower. These are consistent with merit-order pressure and renewable price coincidence.",
     "Actual dispatch is endogenous; correlated predictors complicate importance. DE physical quantities differ from DE-LU price-zone totals. Nuclear gaps remain missing. Forecast vintages are unverified."),
    ("05_volatility_regimes", "How persistent are interpretable market volatility states?",
     "Low/Normal/Elevated/Extreme use 2023 25th/75th/95th quantiles of lagged seven-day standard deviation. Estimate Pr(Rt=j | Rt-1=i) on subsequent hourly states without future smoothing.",
     "from power_risk.regimes.model import classify\nf=pd.read_parquet('reports/volatility_metrics.parquet')\nlabels,cuts=classify(f.rolling_std_7d.shift(),pd.Timestamp('2024-01-01',tz='Europe/Berlin'))\ndisplay(pd.Series(cuts,index=['q25','q75','q95']))\ndisplay(pd.read_csv('reports/regime_transitions.csv',index_col=0))\nrisk=pd.read_csv('reports/portfolio_risk_enhanced.csv')\ndisplay(risk.loc[risk.grouping.eq('regime')])",
     "volatility_heatmap.png",
     "The displayed transition probabilities quantify persistence; conditional portfolio losses differ across states. Scenario counts are essential because small extreme-state samples produce unstable tails.",
     "Overlapping windows mechanically increase persistence. Labels are descriptive rather than causal latent states or hedge recommendations. 2023 portfolio state labels are in-calibration descriptions."),
    ("06_forecast_validation", "Can past-only calibration improve uncertainty without evaluation-label leakage?",
     "Each month uses prior 90-day out-of-sample scores s=max(q10-y,y-q90,0) before D-1 11:00 Berlin. Widen intervals by the finite-sample 80th percentile; evaluate coverage, width, pinball/MAE, Brier/AP and seven-day block confidence intervals.",
     "from power_risk.backtesting.validation import summarize\nf=pd.read_parquet('reports/price_risk_forecasts_enhanced.parquet')\ndisplay(summarize(f))\ndisplay(pd.read_csv('reports/calibration_results.csv'))\ndisplay(pd.read_csv('reports/calibration_windows.csv').head())\ndisplay(pd.read_csv('reports/price_only_vs_fundamental.csv')[['model','feature_group','status']])",
     "calibration_comparison.png",
     "Boosting coverage rises from 68.6% to 78.2%, with width 76.26 to 92.89 EUR/MWh over 16,488 common 2025+ hours. Negative-price Brier worsens after isotonic calibration; benefits are not uniform.",
     "2024 initializes calibration; earlier test months become past history in later folds. No original source vintage proof or distribution-free time-series coverage guarantee. Fundamental-enhanced pre-clearing comparison is blocked; actual fundamentals never enter these forecasts."),
    ("07_portfolio_exposure", "How does production-price coincidence change commercial exposure?",
     "Energy=MW x hours; generator P&L=(spot-reference)xMWh; purchaser reverses sign. Capture price=sum(price x MWh)/sum(MWh). Loss VaR is an empirical quantile; ES averages the fractional worst tail. Complete local delivery days respect DST.",
     "from power_risk.portfolio.risk import risk_summary\ns=pd.read_csv('reports/portfolio_scenario_comparison.csv')\ndisplay(pd.DataFrame([dict(case=name,**risk_summary(g.pnl_eur)) for name,g in s.groupby('case')]))\ncapture=pd.read_csv('reports/renewable_capture_price_analysis.csv')\ndisplay(capture.loc[capture.period.eq('all')])",
     "capture_price_comparison.png",
     "Solar-shaped capture is EUR 56.60/MWh and wind-shaped capture EUR 82.34/MWh, versus baseload EUR 95.24/MWh. National generation coincidence highlights the limitations of flat-price revenue assumptions.",
     "Profiles are hypothetical national shapes normalized to 1 MW observed peak, not installed capacity or actual plant profits. No fees, subsidies, imbalance or curtailment optimization. Equal peak MW does not equalize energy exposure."),
]
for name, question, method, code, chart, findings, limits in TOPICS:
    notebook = nbf.v4.new_notebook()
    notebook.metadata.kernelspec = {"name":"python3", "display_name":"Python 3", "language":"python"}
    data = ("Source: Bundesnetzagentur | SMARD.de. Observed period: January 2023-18 November 2026; "
            "63,843 native price intervals and 136,128 quarter-hours per core load/wind/solar series. "
            "Physical quantities are German net grid/load generation; prices cover DE-LU. "
            "Actuals and forecasts remain separate; no missing physical value is replaced by zero.")
    notebook.cells = [nbf.v4.new_markdown_cell(f"# {name[3:].replace('_',' ').title()}\n\n## Research question\n{question}\n\n## Data\n{data}\n\n## Methodology and equations\n{method}"),
        nbf.v4.new_code_cell(SETUP if "json." in code else SETUP.replace("import json\n", "")), nbf.v4.new_code_cell(code),
        nbf.v4.new_code_cell(f"display(Image(filename='reports/{chart}'))"),
        nbf.v4.new_markdown_cell(f"## Quantitative findings and commercial interpretation\n{findings}\n\n## Limitations\n{limits}\n\nCalculations call reusable modules; regenerate underlying outputs using the README workflow.")]
    nbf.write(notebook, Path('notebooks') / (name+'.ipynb'))
print('Seven research notebooks generated')
