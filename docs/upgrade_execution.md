# Upgrade execution record — 19 November 2026

This supersedes the baseline scope in `phase_status.md`. Existing valid price statistics
and original forecasts are preserved. The existing repository is upgraded in place.

## Phase 0: repository audit

Reviewed all source modules, reports, README, notebooks, dashboard, tests and CI at
b5b3bf6. Created `reports/repository_improvement_audit.md` before changing implementation.
Baseline pytest: 12 passed. SHA256 check: 245 raw response metadata files, zero mismatches
at audit time. Highest-priority gap: unauthenticated SMARD fundamentals had not been tried.

## Phase 1: real free fundamentals

Created `ingestion/fundamentals.py`, field/provenance catalogues and acquisition scripts;
extended HTTP caching with checksum checks and a shared four-request/second limiter.
Command: `power-risk fundamentals --start 2023-01-01 --end 2026-11-19`.

Official provider configuration identifies 22 series: actual/forecast load and onshore
wind/offshore wind/solar; eight other generation categories; French/Dutch prices; four
French commercial/physical directional exchange series. The first 18 were fully downloaded,
then four officially mapped flow series were added. Each core series has 136,128/136,128
observed quarter-hours. Nuclear has 37,874 observations; each French physical-flow series
has 136,095 observations (33 missing). These are not silently repaired.

Deliverables: `fundamentals_native.parquet`, `fundamentals_hourly.parquet` in ignored local
processed data; `fundamental_data_quality.csv`, `fundamental_coverage.html`, updated
availability CSV and raw URL/retrieval provenance. MWh per quarter-hour converts to MW.
Raw imports are negative; normalized directional import magnitudes are positive into DE.
Actual and forecast residual load are separate, require all four inputs, and preserve gaps.

Limitations: Germany physical area versus DE-LU prices; source estimates/revisions;
unverified forecast publication/issue times; French-border coverage is not all German borders.
Commercial exchanges are not certified pre-clearing information. ENTSO-E token still absent;
Open-Meteo remains a tested sample, not a full-period mandatory feature.

## Phase 2: fundamental research

Created `fundamentals/research.py`; ran `power-risk drivers`. 34,032 complete hourly rows.
Real residual-load, wind, solar, demand, conventional-output and neighboring-price analysis
now replaces the previously unavailable fundamental report. Added correlations, conditional
distributions, 2025+ explanatory holdout, permutation importance, seasonal tables, French
border associations and requested figures. Fixed-seed seven-day block bootstrap supports
the descriptive high/low comparisons; calendar controls supplement but do not establish causality.

Three prominent measured results: residual-load price difference EUR 113.22/MWh; midday
solar-group difference EUR -88.05/MWh; high/low demand spike incidence 7.48%/0.42%.
Full thresholds, counts, dates and intervals are in `quantified_market_findings.csv`.
Conventional output is endogenous; nuclear is excluded due to coverage; no causal claims.

## Phase 3: native interval and volatility analysis

Created `volatility/native.py`; ran `power-risk native`. Outputs include native metrics,
positive-spike runs, intrahour report, clustering diagnostics and fundamental-conditioned
volatility. 9,937 complete quarter-hour-market hours: mean within-hour spread EUR 23.90/MWh;
101 hidden negative hours and 357 hidden positive-spike hours. Ljung-Box results are
asymptotic diagnostics subject to seasonality and nonstationarity, not definitive structural tests.

## Phase 4: calibration and forecasting validation

Created `forecasting/enhanced.py` and `backtesting/uncertainty.py`; ran `power-risk calibrate`.
Original models are preserved. Common evaluation: 16,488 hours/model from 2025 onward;
2024 initializes a rolling past-only 90-day error archive. Each monthly cutoff is D-1
11:00 Europe/Berlin. No current-month labels calibrate the current month.

Boosting interval coverage: 68.60% original versus 78.21% calibrated. Width: EUR 76.26
versus 92.89/MWh. Negative-price Brier worsens after isotonic calibration; positive-spike
Brier improves. MAE stays unchanged because the median is unchanged. Full scores, windows,
reliability bins and hour/season evaluations are saved. Coverage uncertainty uses 500
moving seven-day block resamples, not an IID hourly confidence interval.

**Blocked:** a genuine point-in-time fundamental-enhanced comparison. Latest SMARD forecasts
do not prove publication before cutoff; official documentation allows later generation
forecast publication. `price_only_vs_fundamental.csv` marks this explicitly without metrics.
This does not block retrospective fundamental research. No actuals are disguised as forecasts.

## Phase 5: commercial cases

Created `portfolio/enhanced.py`; ran `power-risk portfolio-enhanced`. Purchaser, solar and
wind cases each have 1,418 complete local delivery-day scenarios. Capture prices:
solar EUR 56.60/MWh, wind EUR 82.34/MWh, baseload EUR 95.24/MWh. VaR/ES, seasonal and regime
comparisons, delivery exposure, negative-energy share and spot cash flow are generated.
Profiles are national shapes normalized to 1 MW observed peak, not actual plant capacity.
Reference is EUR 100/MWh; all cases are hypothetical and exclude fees, support and imbalance.

## Phases 6–8: dashboard, notebooks and hiring-manager communication

Upgraded five existing dashboard pages with actual fundamentals, native interval risk,
calibration comparisons and three commercial cases. Seven notebooks now contain research
questions, data/methods, equations, module calls, genuine charts, findings and limitations.
All seven were executed successfully using the project's Python kernel. Five dashboard
branches passed Streamlit AppTest with real local outputs.

Created `executive_market_analysis.pdf` (exactly two pages, three charts), CV summary and
16-question interview guide. PDF rendered with Poppler; both pages visually inspected
for layout and readable charts. README now leads with verified results and commercial meaning.

## Phase 9: engineering and reproducibility

Expanded tests cover cache corruption, API failures, physical units, missing/duplicate
quarters, forecast/actual separation, DST, border direction, capture weighting, contract-end
price eligibility and calibration/test separation. Existing original tests remain intact.
CI adds a dashboard smoke step (missing local data states are handled explicitly).

Commands: `pytest -q`, `ruff check .`, `python scripts/dashboard_smoke.py`,
`python scripts/execute_notebooks.py`, `python scripts/check_reproducibility.py`.
Final observed results are recorded in `reports/upgrade_verification.txt`.

Remaining material limits: authentic original forecast vintages, causal identification,
full-period weather, all-border coverage and plant-specific operational economics. They
are disclosed rather than replaced with unsupported numbers. Total data spend remains EUR 0.
