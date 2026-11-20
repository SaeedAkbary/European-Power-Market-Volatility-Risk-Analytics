"""Generate CV evidence, concise charts and a two-page executive PDF from actual reports."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ROOT = Path.cwd()
findings = pd.read_csv("reports/quantified_market_findings.csv").set_index("finding")
scores = pd.read_csv("reports/model_comparison_enhanced.csv").set_index("model")
captures = pd.read_csv("reports/renewable_capture_price_analysis.csv").query("period == 'all'").set_index("case")
risks = pd.read_csv("reports/portfolio_risk_enhanced.csv").query("grouping == 'all'").set_index("case")
intrahour = json.loads(Path("reports/intrahour_summary.json").read_text())
residual = findings.loc["Residual-load price gradient"]
solar = findings.loc["Midday solar-price association"]
demand = findings.loc["Demand and high-price incidence"]
before = scores.loc["gradient_boosting / original"]
after = scores.loc["gradient_boosting / calibrated"]

fig, ax = plt.subplots(figsize=(6, 3.2))
coverage = [before.coverage_80 * 100, after.coverage_80 * 100]
ax.bar(["Original", "Past-error calibrated"], coverage, color=["#9bacbb", "#087e8b"], width=.55)
ax.axhline(80, color="#bb6132", linestyle="--", label="80% target")
for i, value in enumerate(coverage):
    ax.text(i, value + 2, f"{value:.1f}%", ha="center", fontsize=12)
ax.set(ylim=(0, 100), ylabel="Observed interval coverage (%)", title="2025-2026 common evaluation sample")
ax.legend(loc="lower right", frameon=False)
fig.tight_layout()
fig.savefig("reports/calibration_comparison.png", dpi=180)
plt.close(fig)
fig, ax = plt.subplots(figsize=(6, 3.2))
values = captures.loc[["purchaser", "solar", "wind"], "capture_price_eur_mwh"]
ax.bar(["Baseload", "Solar shape", "Wind shape"], values, color=["#9bacbb", "#e5a73b", "#087e8b"])
for i, value in enumerate(values):
    ax.text(i, value + 2, f"{value:.2f}", ha="center", fontsize=11)
ax.set(ylim=(0, 120), ylabel="Energy-weighted price (EUR/MWh)", title="Observed price / generation coincidence")
fig.tight_layout()
fig.savefig("reports/capture_price_comparison.png", dpi=180)
plt.close(fig)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=colors.HexColor("#173447"), spaceAfter=10))
styles.add(ParagraphStyle(name="SubCustom", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#087e8b"), spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyCustom", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=6, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="SmallCustom", fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#526473"), spaceAfter=4))
def P(text, style="BodyCustom"):
    return Paragraph(text, styles[style])

def table(rows, widths):
    wrapped = [[P(str(cell), "SmallCustom") for cell in row] for row in rows]
    t = Table(wrapped, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f1f3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), .7, colors.HexColor("#087e8b")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5)]))
    return t

def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#cbd6db"))
    canvas.line(17*mm, 15*mm, 193*mm, 15*mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#526473"))
    canvas.drawString(17*mm, 11*mm, "Saeed Akbari | Germany case study | 19 November 2026 | Source: Bundesnetzagentur / SMARD.de")
    canvas.drawRightString(193*mm, 11*mm, str(doc.page))

story = [P("German electricity market<br/>Volatility, fundamentals and risk", "TitleCustom"),
    P("EXECUTIVE MARKET ANALYSIS | EUR 0 PUBLIC-DATA RESEARCH", "SubCustom"),
    P("Objective: explain observed price tails and translate them into defensible forecasting and commercial exposure examples. "
      "Coverage: 1 January 2023 to 18 November 2026; 63,843 native price intervals and 136,128 quarter-hours for each core load/wind/solar series. "
      "No missing core observations; 34,032 complete hourly comparisons. Physical area: Germany; price area: DE-LU."),
    P("Three measured physical-market relationships", "SubCustom"),
    table([["Comparison", "Observed result", "Interpretation / evidence"],
        ["Residual load: upper vs lower quartile", f"EUR {residual.high_mean:.2f} vs {residual.low_mean:.2f}/MWh",
         f"Difference EUR {residual.difference:.2f}; 95% block CI [{residual.ci_low:.2f}, {residual.ci_high:.2f}]. 8,508 hours per group."],
        ["Solar output: upper vs lower midday quartile", f"EUR {solar.high_mean:.2f} vs {solar.low_mean:.2f}/MWh",
         f"Difference EUR {solar.difference:.2f}; CI [{solar.ci_low:.2f}, {solar.ci_high:.2f}]. Local 10:00-15:59; 2,127 hours per group."],
        ["Demand: upper vs lower quartile", f"{demand.high_mean*100:.2f}% vs {demand.low_mean*100:.2f}% spike incidence",
         f"Price >= EUR 200/MWh. Difference {demand.difference*100:.2f} percentage points; CI [{demand.ci_low*100:.2f}, {demand.ci_high*100:.2f}]."]], [43*mm, 46*mm, 87*mm]),
    Spacer(1, 5*mm), Image("reports/residual_load_price_relationship.png", width=176*mm, height=88*mm),
    P("Market interpretation", "SubCustom"),
    P("Higher residual load coincides with higher marginal-system price pressure; solar output coincides with lower midday prices. "
      "These patterns are consistent with merit-order economics, but fuel costs, outages, demand seasonality and cross-border conditions also matter. "
      "Calendar-controlled explanatory models and a chronological holdout supplement the descriptive comparisons; they do not identify causal effects."),
    P("Evidence protocol: full-sample descriptive quartiles; 500 moving seven-day block resamples for 95% confidence intervals. "
      "SMARD data include provider estimates and revisions. Raw source observations are retained; no missing values are replaced with zero.", "SmallCustom"),
    PageBreak(), P("Forecast discipline and<br/>commercial exposure", "TitleCustom"),
    P("Uncertainty improves, at the cost of wider intervals", "SubCustom"),
    P(f"On the same {int(after.observations):,} delivery hours from January 2025 onward, past-error calibration raises boosting's "
      f"nominal 80% interval coverage from {before.coverage_80*100:.1f}% to {after.coverage_80*100:.1f}%. "
      f"Mean width rises from EUR {before.mean_width:.2f} to {after.mean_width:.2f}/MWh. Each month's calibrator uses only earlier out-of-sample errors. "
      "Negative-price Brier score worsens after isotonic calibration; probability gains are not uniform."),
    table([["Model / interval", "Coverage", "Width EUR/MWh", "MAE EUR/MWh"],
        ["Seasonal / original", f"{scores.loc['seasonal_history / original'].coverage_80:.1%}", f"{scores.loc['seasonal_history / original'].mean_width:.2f}", f"{scores.loc['seasonal_history / original'].mae:.2f}"],
        ["Boosting / original", f"{before.coverage_80:.1%}", f"{before.mean_width:.2f}", f"{before.mae:.2f}"],
        ["Boosting / calibrated", f"{after.coverage_80:.1%}", f"{after.mean_width:.2f}", f"{after.mae:.2f}"]], [65*mm, 31*mm, 40*mm, 40*mm]),
    Spacer(1, 4*mm),
    Table([[Image("reports/calibration_comparison.png", width=87*mm, height=46.4*mm),
            Image("reports/capture_price_comparison.png", width=87*mm, height=46.4*mm)]], colWidths=[88*mm, 88*mm]),
    P("Implications for purchasers and generators", "SubCustom"),
    P(f"Native quarter-hour prices reveal {intrahour['hidden_negative_hours']} hours with a negative quarter hidden by a nonnegative hourly mean, "
      f"and {intrahour['hidden_positive_spike_hours']} hours with a >=EUR 200/MWh quarter hidden by a lower hourly mean. "
      f"Solar-shaped capture price is EUR {captures.loc['solar'].capture_price_eur_mwh:.2f}/MWh and wind-shaped capture price "
      f"EUR {captures.loc['wind'].capture_price_eur_mwh:.2f}/MWh, versus baseload EUR {captures.loc['purchaser'].capture_price_eur_mwh:.2f}/MWh. "
      "Generation-price coincidence matters as much as the average market price."),
    table([["Hypothetical daily exposure", "95% loss VaR (EUR)", "Expected Shortfall (EUR)"],
        *[[case.title(), f"{risks.loc[case].var_loss_eur:,.2f}", f"{risks.loc[case].expected_shortfall_loss_eur:,.2f}"] for case in ["purchaser", "solar", "wind"]]], [76*mm, 50*mm, 50*mm]),
    P("Assumptions: purchaser 1 MW flat; solar/wind national shapes normalized to a 1 MW observed peak, not plant capacity. "
      "Reference EUR 100/MWh; complete local days including DST. Generation P&amp;L=(spot-reference)xMWh; purchaser reverses sign. "
      "Historical scenarios are hypothetical and do not establish financial returns or optimal hedges.", "SmallCustom"),
    P("Key limitations and operational gate", "SubCustom"),
    P("Historical source vintages are unverified. Fundamental-enhanced pre-clearing comparison is blocked: latest forecasts cannot prove availability by D-1 11:00 Berlin. "
      "Generation forecasts may arrive later. No paid fuels, forward curves or private positions are used. No causal claims, guaranteed time-series coverage, "
      "plant-specific capture or trading profitability are implied. Validate vintages and stability before operational use.", "SmallCustom"),
    P('Reproducible code and detailed results: <link href="https://github.com/SaeedAkbare/European-Power-Market-Volatility-Risk-Analytics">github.com/SaeedAkbare/European-Power-Market-Volatility-Risk-Analytics</link>', "SmallCustom")]

doc = SimpleDocTemplate("reports/executive_market_analysis.pdf", pagesize=(210*mm, 297*mm),
    rightMargin=17*mm, leftMargin=17*mm, topMargin=15*mm, bottomMargin=20*mm,
    title="German Electricity Market - Executive Market Analysis", author="Saeed Akbari")
doc.build(story, onFirstPage=footer, onLaterPages=footer)

cv = f"""# CV project summary

**European Power Market Volatility & Risk Analytics - Germany Case Study**

Reproducible Python research linking German electricity-market fundamentals, price extremes,
probabilistic forecasts and hypothetical purchaser/renewable exposure, using free SMARD data.

- Integrated and validated 136,128 quarter-hour observations per core demand/wind/solar series;
  linked actual residual load to a EUR {residual.difference:.2f}/MWh upper-versus-lower-quartile price difference
  using 34,032 hourly comparisons and seven-day block-bootstrap uncertainty.
- Evaluated price-risk models chronologically and calibrated intervals using past out-of-sample
  errors; improved boosting's nominal 80% coverage from {before.coverage_80:.1%} to {after.coverage_80:.1%}
  on {int(after.observations):,} common evaluation hours, explicitly reporting wider intervals and calibration trade-offs.
- Built hypothetical purchaser, solar and wind risk cases with duration-correct P&L, VaR/ES
  and capture-price analysis; identified solar-shaped capture of EUR {captures.loc['solar'].capture_price_eur_mwh:.2f}/MWh
  versus a EUR {captures.loc['purchaser'].capture_price_eur_mwh:.2f}/MWh baseload average.

**Skills demonstrated:** Python, pandas, NumPy, scikit-learn, SMARD data engineering,
electricity-market fundamentals, residual-load analysis, native interval volatility,
probabilistic forecasting, chronological validation, block bootstrap, risk modelling,
Streamlit, pytest, GitHub Actions, scientific communication.

**Scope:** 1 January 2023-18 November 2026; calibrated evaluation from January 2025.
Retrospective associations are not causal estimates. Forecast vintage timing is unverified;
fundamental-enhanced pre-auction modelling remains blocked. Portfolios are hypothetical;
no actual trading profits, financial savings or professional trading experience are implied.
ENTSO-E is an optional connector, not a source claimed as used in these results.
"""
Path("docs/cv_project_summary.md").write_text(cv, encoding="utf-8")
print("Executive PDF, comparison figures and evidence-based CV summary generated")
