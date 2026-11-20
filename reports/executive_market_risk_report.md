# German electricity market: executive risk assessment

**Preserved baseline assessment.** The upgraded research now includes real SMARD physical
fundamentals, improved calibration and renewable portfolios. Use
`executive_market_analysis.pdf` for the current two-page report. Baseline price statistics
below remain valid; the former fundamental-data gap has been addressed.

**Scope:** genuine SMARD DE-LU day-ahead prices, 1 January 2023–18 November 2026.
Source: Bundesnetzagentur | SMARD.de. €0 data expenditure. All 63,843 expected native
intervals were retrieved with no missing prices or duplicates.

**What happened.** The hourly-equivalent average was €95.24/MWh, while native prices
ranged from −€500 to €936.28/MWh. Negative prices occupied 1,797.75 hours (5.28% of
delivery time) in 376 episodes. The mean complete-day hourly price spread was €121.68/MWh.
These are full-period descriptive statistics, not current forward-price expectations.

**Why it happened.** The hourly/weekday heatmap documents strong differences across
delivery periods, but the current dataset cannot identify the fundamental causes.
Validated residual-load, generation and border data are unavailable without ENTSO-E
integration. Renewable oversupply, demand and constraints are hypotheses to investigate,
not findings established by this price-only analysis.

**What risk it represents.** Average-price budgeting conceals substantial delivery-period
tail exposure. Negative prices reverse the usual commercial effect: they benefit an
unhedged purchaser and reduce a generator's spot revenue. Hourly aggregation can conceal
quarter-hour extremes after the October 2025 market-time-unit change. Exposure must be
measured as MW × actual interval hours, including DST and missing-period checks.

**What can be predicted in this experiment.** Monthly chronological evaluation covers
25,272 hours from 2024 onward. The seasonal benchmark's median pinball loss is 18.30
EUR/MWh; gradient boosting's is 14.64 EUR/MWh. Its negative-price Brier score is 0.0413
versus 0.0509 for the benchmark. However, nominal 80% interval coverage falls to **69.5%**
for boosting versus **77.1%** for the benchmark: narrower model intervals underestimate
realized uncertainty. These results support further calibration research, not deployment.
Historical publication/revision evidence is unavailable; no executable ex-ante strategy
or statistically significant superiority is claimed.

**Commercial illustration.** For a hypothetical flat 1 MW purchase over 24 UTC hours,
against €100/MWh, the 1,417 complete historical day scenarios yield 95% loss VaR of
€1,559.95 and Expected Shortfall of €2,698.89. Positive P&L means favorable procurement
relative to the reference; loss is its negative. Historical scenarios preserve within-day
dependence but assume past days represent future risk. These values are neither actual
trading P&L nor a hedge recommendation, and do not include fees, imbalance costs or
counterparty constraints.

**Next decision gate.** Obtain the free ENTSO-E token, validate forecast vintages and
fundamental coverage, and recalibrate predictive intervals on a separate historical
calibration set before considering operational risk use. The present deliverable is
a reproducible historical/price-only research project with explicit incomplete inputs.
