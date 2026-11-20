# Interview preparation: defensible project answers

1. **How are day-ahead electricity prices formed?**
   The market clears supply and demand subject to network and market rules. The marginal
   accepted supply/demand conditions help explain the price, but cross-border coupling,
   intertemporal plant constraints and bidding behavior complicate a simple supply stack.
   This project studies observed DE-LU prices; it does not reconstruct the auction book.

2. **How does merit-order reasoning relate to your findings?**
   Low-marginal-cost wind/solar can reduce the demand left for other plants. Mean prices
   were EUR 147.32/MWh in the upper residual-load quartile versus EUR 34.10/MWh in the
   lower quartile. That association is consistent with merit-order reasoning, not proof
   that changing residual load alone causes a EUR 113.22 price effect.

3. **How did you define residual load?**
   German grid load minus onshore wind, offshore wind and solar generation, all in MW.
   Quarter-hour MWh are divided by 0.25. All components must be observed; missing wind
   never becomes zero. Actual and forecast residual load remain distinct columns.

4. **Why can electricity prices be negative?**
   Inflexible operations, startup costs, support arrangements and limited flexibility
   can make negative offers rational when supply is abundant relative to demand.
   The project observed 1,797.75 negative-price hours, but does not identify individual
   bidders' incentives. High-wind hourly groups had more negative prices, with material
   seasonal and demand confounding.

5. **What does renewable cannibalization mean here?**
   Similar generation patterns can concentrate output in lower-priced periods. The
   aggregate solar-shaped capture price was EUR 56.60/MWh versus the EUR 95.24/MWh
   baseload mean; wind-shaped capture was EUR 82.34/MWh. This is a price/output coincidence
   measure, not a causal estimate of cannibalization or a specific plant's profitability.

6. **Why not use logarithmic price returns?**
   Prices can be zero or negative. I use level dispersion, differences, daily spreads,
   events and native-interval extremes. ATR and Bollinger bands are descriptive comparisons,
   not automatic hedging signals or conventional traded-asset OHLC measures.

7. **What did the 15-minute analysis add?**
   From October 2025 onward, 101 hours contained a negative quarter despite a nonnegative
   hourly mean; 357 hours contained a >=EUR 200/MWh quarter hidden by a lower hourly mean.
   Native quarter-hour exposure therefore matters even when a long-run chart is hourly.

8. **How is forecast leakage prevented?**
   The experimental cutoff is D-1 11:00 Europe/Berlin. Price features are at least 48h old;
   monthly fits use only earlier targets. Vintage eligibility rejects unknown or late
   publication/issue timestamps. Actual delivery-day load/generation never enter prospective
   forecasts. Latest historical snapshots still cannot establish executable availability.

9. **Did fundamentals improve your forecasts?**
   I cannot defensibly answer that yet. SMARD's latest forecast series lack original
   publication/vintage evidence, and generation forecasts may be published after the
   cutoff. I integrated them for retrospective forecast-error/residual-load inspection
   but mark the ex-ante fundamental comparison blocked. Actual-fundamental models are
   explanatory diagnostics, clearly separate from forecasting performance.

10. **How did you improve interval calibration?**
    Each evaluation month uses the prior 90 days of out-of-sample errors before cutoff.
    I widen intervals using the finite-sample 80th percentile of max(lower-y,y-upper,0).
    Boosting coverage rises from 68.6% to 78.2% on 16,488 common test hours, with mean
    width increasing from EUR 76.26 to EUR 92.89/MWh. This is not a guaranteed 80% coverage
    result under nonstationary dependent data. The median forecast is unchanged.

11. **Does probability calibration always help?**
    No. Past-window isotonic calibration improved the positive-spike Brier score in this
    experiment but worsened the negative-price Brier score. I report both, rather than
    selecting whichever looks better on the final sample. Reliability bins and event
    frequencies supplement scalar scores; rare-event precision-recall is also reported.

12. **How did you handle dependence in uncertainty estimates?**
    Seven-day moving block bootstrap, with 500 fixed-seed resamples of daily data, preserves
    some short-range dependence. It does not resolve structural breaks or long memory.
    Confidence intervals are descriptive uncertainty assessments, not causal identification.

13. **What are the market regimes?**
    Low/Normal/Elevated/Extreme use fixed 2023 quantile cutpoints for lagged seven-day
    price standard deviation. Subsequent frequencies/transitions are out of calibration.
    Overlapping windows mechanically create persistence; I do not interpret the labels
    as hidden causal market states or claim they select an optimal trading strategy.

14. **How do VaR and Expected Shortfall differ?**
    Loss is minus hypothetical P&L. VaR is an empirical loss quantile; ES averages the
    worst tail using fractional probability mass. ES captures severity beyond VaR but
    is sensitive to sample size. Daily scenarios assume historical representativeness;
    renewable and purchaser cases have different energy exposures, even at equal peak MW.

15. **What matters commercially during spikes?**
    Spot-exposed buyers incur higher costs while generators may receive higher prices,
    subject to their production and contractual position. Negative prices reverse those
    effects. I keep EUR/MWh, MW and MWh distinct and show hypothetical reference-relative
    P&L, not actual trades, fees, imbalance costs or hedge optimization.

16. **Why distinguish physical flows from commercial exchanges?**
    Physical power follows the network, while commercial exchanges represent transactions.
    French-border imports have negative SMARD chart signs; I explicitly convert them to
    positive import magnitudes, preserve exports separately and define net import as
    import minus export. Physical-flow gaps are retained. Neither series is assumed to
    have been known before clearing, and France is not a proxy for every German border.

Evidence: `reports/quantified_market_findings.csv`, `model_comparison_enhanced.csv`,
`intrahour_summary.json`, `renewable_capture_price_analysis.csv` and source documentation.
