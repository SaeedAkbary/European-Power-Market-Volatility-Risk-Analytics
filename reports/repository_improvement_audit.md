# Repository improvement audit — 19 November 2026

Baseline inspected: commit b5b3bf6. Existing Python modules, tests, dashboard, notebooks,
README, CI and actual generated CSV/Parquet reports reviewed before implementation changes.
Baseline execution: 12 pytest tests passed (three dependency deprecation warnings).

| Module | Status | Evidence and next action |
|---|---|---|
| Price ingestion / validation | COMPLETE | 63,843 native intervals, no missing data; immutable raw JSON + retrieval/hash metadata. Add cache-integrity and API-failure tests. |
| Fundamental ingestion | NOT IMPLEMENTED | ENTSO-E raw XML exists but no normalization; SMARD fundamentals were not investigated. Highest priority: retrieve native MWh and normalize to MW. |
| Weather | PARTIALLY COMPLETE | Three-location January 2023 samples only; keep retrospective and document non-commercial hosted tier. |
| Calendar | COMPLETE | UTC/local DST tests and German national holidays. |
| Residual load / drivers | PARTIALLY COMPLETE | Formula and guarded analysis exist; no real observations, correlations, findings or feature importance. Avoid treating absent ENTSO-E credentials as proof SMARD data are unavailable. |
| Volatility / events | PARTIALLY COMPLETE | Genuine hourly metrics and native negative runs; no native intrahour comparison, formal clustering tests or fundamental conditioning. |
| Regimes | COMPLETE | 2023 fixed thresholds, later evaluation; descriptive overlapping-window persistence, not a causal state model. |
| Forecasting | NEEDS VALIDATION | 35 monthly folds, 25,272 hours/model; lags >=48h. No target leakage identified in price-only design. Timestamp eligibility exists but source vintages unverified. 69.5% nominal 80% coverage requires separate past calibration. |
| Forecast evaluation | PARTIALLY COMPLETE | Pinball/Brier/AP, coverage and breakdowns implemented; add MAE, blocked confidence intervals and calibration protocol. Preserve old results as baseline. |
| Portfolio | PARTIALLY COMPLETE | Correct interval P&L and fractional-tail ES; flat purchaser only, renewable capture/profile cases absent. |
| Dashboard | PARTIALLY COMPLETE | Five functional branches, fundamental page unavailable; add actual evidence and calibrated results. |
| Notebooks / presentation | PARTIALLY COMPLETE | Six reader notebooks, no substantial narrative; no executive PDF, CV summary or interview guide. |
| Tests / CI | PARTIALLY COMPLETE | 12 offline tests pass; add ingestion errors, units, directions, calibration separation and capture-price tests. |
| Vintage-verified fundamental backtest | BLOCKED BY FREE DATA ACCESS | No original issue/publication evidence in chart responses. Documented generation forecasts may arrive after the 11:00 cutoff. Never silently use actuals or assume latest forecasts are original vintages. |

Priorities: (1) real SMARD fundamentals and quantified residual-load research, (2) honest
calibration with a separate historical window, (3) native quarter-hour risk and renewable
capture economics, (4) concise recruiter-facing evidence. Existing genuine price statistics
and original model outputs remain preserved; enhanced experiments use separate filenames.

Provenance caveats: SMARD generation includes provider estimates; German physical fundamentals
are DE, while the price bidding zone is DE-LU. Latest historical snapshots do not reproduce
what was known at auction time. Correlation and importance cannot establish causality.

Final phase outcomes and executed verification will be recorded in `docs/upgrade_execution.md`.
