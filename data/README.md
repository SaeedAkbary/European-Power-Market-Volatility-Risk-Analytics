# Data layers

`raw/`: original provider responses and hashed retrieval metadata.
`processed/`: validated native intervals and complete hourly aggregation.
`features/`: calendar and derived research features.

The upgrade adds `fundamentals_native.parquet` and `fundamentals_hourly.parquet` with
separate actual/forecast physical series and French-border directional flows. Quarter-hour
MWh convert to MW; gaps stay missing. See `../reports/fundamental_provenance.json` for
the exact source queries and `../reports/fundamental_data_quality.csv` for coverage.

Raw and processed observations are excluded from Git. Regenerate with `power-risk audit`.
Source attribution: Bundesnetzagentur | SMARD.de. See `../docs/data_sources.md` for
licensing, free-access conditions and forecast-vintage limitations. No synthetic values
are inserted into these layers. Tests use explicitly labelled in-memory fixtures.
