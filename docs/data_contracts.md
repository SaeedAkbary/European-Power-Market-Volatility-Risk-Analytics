# Input and output contracts

All ranges are start-inclusive, end-exclusive. CLI dates without offsets mean midnight
Europe/Berlin. Persisted delivery timestamps are timezone-aware UTC; local calendar
fields are derived without discarding offsets. DST days contain 23 or 25 hours.

| Field | Type | Meaning |
|---|---|---|
| delivery_start, delivery_end | UTC timestamp | Physical delivery interval [start, end) |
| interval_minutes | integer | 60 before 2025-10-01 local; 15 thereafter |
| price_eur_mwh | nullable float | Day-ahead DE-LU price; negative values valid |
| bidding_zone | string | DE-LU (not historical DE-AT-LU) |
| local_delivery_hour, market_date | integer, ISO date string | Europe/Berlin delivery calendar |
| provider, source_url | string | Attribution and exact source query |
| retrieved_at | UTC ISO timestamp | Cache acquisition time |
| publication_time | nullable timestamp | Original publication, unknown for SMARD |
| forecast_issue_time | nullable timestamp | Original forecast vintage, unknown for SMARD |

Raw layer: original JSON/XML plus URL/query, retrieval time and SHA256 sidecar. Tokens
are excluded from metadata. Cached records are immutable until explicitly refreshed.
Processed layer: validated native `prices.parquet` and complete duration-weighted
`prices_hourly.parquet`. Features layer: hourly calendar and analytical metrics.
Hourly price = sum(price × minutes)/60, only when all 60 minutes have observed prices.
Missing intervals and nulls are retained as missing; no fabricated interpolation.
Native-quarter-hour extremes are not equivalent to hourly-average extremes.

The upgrade's validated fundamental layer is a wide UTC-indexed table with distinct
`actual_*` and `forecast_*` MW fields, neighboring EUR/MWh prices and separately named
directional commercial/physical MW fields. Native rows span 15 minutes and include
delivery end, interval minutes, local market date and null original publication/issue
timestamps. Hourly rows require four observed quarters per variable. Variable-level
provenance is in `reports/fundamental_provenance.json`; original units/observations remain
in raw JSON. Derived actual and forecast residual loads require all four components.
No original vintage is certified. The ENTSO-E adapter's future normalized input remains:
UTC delivery start/end, variable, value, unit, area/border, fuel_type, process_type,
issue_time, publication_time, retrieval_time, revision_id and source_url.
Power is MW; interval energy is MWh; convert energy to MW by dividing by interval hours.
Do not treat generation consumption columns as production. Keep onshore/offshore wind,
physical flows and commercial schedules distinct. Residual load = load − onshore wind
− offshore wind − solar, requiring every component. Missing fuel categories are unknown,
not zero. Compare actual/forecast errors only over matching areas, units and intervals.

Outputs: Parquet retains datetime types; CSV uses ISO timestamps; HTML reports identify
actual data, exploratory historical models and hypothetical portfolio scenarios.
`data_availability_report.csv` includes all requested columns plus verification_status,
token_required, tested_start and tested_end. `data_quality.json` includes absent grid
positions, null observations and missing rate over the entire requested period.

## Prospective information contract

Research cutoff: D−1 at 11:00 Europe/Berlin for delivery date D. An admissible feature
requires publication_time <= cutoff and, for forecasts, issue_time <= cutoff. Unknown
times fail closed. Select the latest *available* vintage per delivery interval. Document
creation or retrieval timestamps alone cannot prove the earliest publication time.
Actual D load, generation, flows and reanalysis are retrospective explanations only.
Use forecast residual load for prospective work after validating its vintage.

For enhanced calibration, `calibration_windows.csv` records each training-error archive,
issuance cutoff and evaluation window. 2024 initializes the archive; evaluation begins
in 2025. Every archive is strictly earlier than the monthly cutoff. Forecast-group
availability status is distinct from metric validity; blocked fundamental models have
no fabricated score columns. Enhanced portfolio cases use complete local days, while
the preserved baseline portfolio used fixed UTC-day blocks; their VaR samples differ.

Price-only exploratory backtests may use calendar and prices at least 48 hours old;
these lags avoid same-day/next-day target contamination but cannot reconstruct source
revisions. Such results are explicitly not executable trading backtests. Test-day labels
must never enter model fitting, scaling, quantile thresholds or hyperparameter selection.
