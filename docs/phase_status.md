# Execution record

**Historical baseline record.** The subsequent upgrade integrated real SMARD fundamentals,
calibration, renewable portfolios and executed research notebooks. See
`upgrade_execution.md` for current status. Statements below describe the original build,
not the upgraded project's current limitations or publication state.

Build date: 19 November 2026. Data budget used: €0. Repository prepared locally; no
remote repository was created and no files were published. Actual report values are
stored in machine-readable files; there are no synthetic findings.

## Phase 0 — completed price audit; other datasets qualified

Created: `ingestion/{http,smard,audit,entsoe}.py`, `validation/quality.py`, project
configuration, source documentation, schema contracts and data directories.

Command: `power-risk audit --start 2023-01-01 --end 2026-11-19`.

Coverage: 63,843/63,843 expected native price intervals, no duplicates or missing values.
Open-Meteo reanalysis and stitched forecasts: three German locations, 1–7 January 2023,
all three requested fields present with no nulls in that sample. Results:
`data_availability_report.csv`, `data_quality.json`, cached JSON and `prices.parquet`.

Limitations: ENTSO-E has no supplied token, so live retrieval is NOT_TESTED. Weather
individual runs are NOT_TESTED, full-period weather coverage remains unaudited.
Raw API responses have no verified historical issue/publication timestamps for the
required ex-ante use. Optional exchange/carbon/gas inputs remain excluded.

## Phase 1 — completed

Created: calendar features, volatility metrics, event detection, reports, charts and
market summary. Commands: `power-risk analyze`; `pytest -q`.

Coverage: 34,032 complete hourly-equivalent prices across the audited native period.
Outputs: `volatility_metrics.parquet`, `volatility_report.html`, `price_distribution.png`,
`volatility_heatmap.png`, `extreme_price_events.csv`, `negative_price_events.csv`,
`daily_price_metrics.csv`, `price_spike_analysis.html` and `market_summary.json`.

Tests cover both DST transitions, the MTU change, incomplete hours, duplicates, negative
prices, event continuity and future-invariant thresholds. ATR and Bollinger bands are
descriptive; no log returns or automated extreme-price removal. Remaining extension:
formal volatility-clustering significance tests with robust seasonality control.

## Phase 2 — implemented interface, live integration incomplete

Created: raw ENTSO-E connector, residual-load calculation, point-in-time eligibility
filter and retrospective driver analysis. Command:
`python -c "from power_risk.fundamentals.analysis import run; run()"`.

Output: `fundamental_driver_analysis.html` explicitly reports unavailable inputs.
No feature-importance CSV or residual-load scatter is fabricated. Tests verify that
missing generation components do not become zeros and future/unknown vintages fail closed.

Remaining: obtain free token, retrieve real XML, implement and validate category-specific
normalization (including units/revisions/fuels/borders), integrate full-period weather,
then execute regression/nonlinear driver analysis. This is a substantive incomplete phase.

## Phase 3 — price-only exploratory implementation and execution complete

Created: interpretable regime classifier, temporal design matrix, seasonal benchmark,
linear quantile model, boosted quantile/classification models, validation/calibration
and reports. Commands:

```powershell
python -c "from power_risk.regimes.model import run; run()"
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
power-risk forecast --advanced
```

Regime calibration: 2023; fixed thresholds evaluated from 2024. Forecast evaluation:
1 January 2024–18 November 2026, 35 monthly folds, 25,272 hours per model. Each fit uses
only targets before the first day's D−1 11:00 Berlin cutoff; predictive price lags are
at least 48h. Linear quantile fits use the last 90 days for bounded solver cost; the
seasonal and boosted models use expanding history. `power-risk forecast` alone is the
lightweight seasonal benchmark; `--advanced` regenerates all three comparisons.

Outputs: market regimes, transition matrix, regime HTML, price-risk forecasts, model
comparison, probability calibration, validation by hour/season, daily dispersion and
forecast-validation HTML. The boosted model's 69.5% coverage of nominal 80% intervals
is explicitly reported. No calibration superiority or executable trading claim is made.

Remaining: real vintage-verified forecasts, fundamental forecast features, predictive
distribution calibration on separate training/calibration windows, uncertainty intervals,
regime-aware/latent-state comparison and a proper next-day dispersion distribution.
Daily dispersion of predicted medians is only a point proxy, not total predictive variance.

## Phase 4 — portfolio and dashboard implemented

Created: portfolio P&L/VaR/ES, historical complete-day scenarios, hypothetical stress
scenarios, five-page Streamlit dashboard, six presentation notebooks, CI and documentation.
Commands: `power-risk portfolio`, `streamlit run dashboards/app.py`,
`python scripts/dashboard_smoke.py`, `pytest -q`, `ruff check .`.

Historical sampler: 1,417 complete UTC-day blocks, flat 1 MW purchase, €100/MWh reference.
Custom interval CSV permits variable MW, duration and horizon for deterministic P&L.
Outputs: portfolio-risk CSV/HTML, stress-tests CSV, scenario CSV and executive report.
Portfolio results are hypothetical, not realized performance. Full horizon-dependent
conditional scenario generation and variable-profile historical resampling remain extensions.

## Environment and final checks

Python 3.12 local virtual environment; pinned installed versions in `requirements-lock.txt`.
Windows initially blocked a PyArrow Parquet DLL; Fastparquet successfully wrote/read the
actual outputs. A scikit-learn DLL also had an initial loading failure; a subsequent
execution completed all 35 folds with two numerical threads. No system security settings
were changed. Local tests use synthetic fixtures solely for mechanics.

See `reports/verification.txt` for the final executed test/lint/dashboard status. Notebooks
are lightweight presentation readers and were generated, not executed as independent research.
