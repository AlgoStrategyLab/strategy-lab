"""Render this article's data tables as PNGs (Medium strips HTML tables)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sitebuild.render import make_renderer, C
render = make_renderer(Path(__file__).parent / "tables")

W2 = [0.52, 0.24, 0.24]
render("t_headline", ["Metric","Dual Momentum (GEM)","S&P 500","60/40","Intl equities"],
 [["CAGR","10.25%","9.85%","7.63%","5.84%"],
  ["Annualised volatility","15.0%","19.2%","11.5%","18.2%"],
  ["Sharpe (rf = 0)","0.73","0.59","0.71","0.40"],
  ["Sortino","1.02","0.83","—","—"],
  ["Max drawdown","–33.8%","–55.3%","–35.5%","–61.5%"],
  ["Recovery from max DD","14 months","58 months","—","—"],
  ["Longest underwater","3.1 years","6.1 years","—","—"],
  ["Calmar","0.30","0.18","—","—"],
  ["Worst year","–17.3% (2022)","–37.0% (2008)","—","—"],
  ["Positive months","64%","65%","—","—"],
  ["Beta to S&P 500","0.52","1.00","—","—"],
  ["Annual turnover","214%","0%","—","—"],
  ["Growth of $1","$17.65","$15.89","$8.68","$5.33"]],
 title="Headline results, May 1997 – Oct 2026", col_w=[0.36,0.18,0.16,0.15,0.15], highlight_col=1)

render("t_returns", ["Metric","Dual Momentum","S&P 500"],
 [["Total return","+1,665%","+1,489%"],["Growth of $1","$17.65","$15.89"],["CAGR","10.25%","9.85%"],
  ["Arithmetic mean annual return","10.9%","11.3%"],["Average month","+0.88%","+0.88%"],
  ["Median month","+0.91%","+1.36%"],["Average positive month","+2.95%","+3.42%"],
  ["Average negative month","–2.79%","–3.77%"],["Best / worst day","+9.5% / –12.0%","+11.6% / –12.0%"],
  ["Best / worst month","+10.9% / –14.5%","+12.8% / –16.8%"],
  ["Best / worst quarter","+21.4% / –19.7%","+21.4% / –21.9%"],
  ["Best / worst year","+29.8% / –17.3%","+32.2% / –37.0%"],
  ["Positive days / months","53% / 64%","54% / 65%"],
  ["Positive quarters / years","70% / 77%","72% / 80%"],
  ["Longest win streak (days / months)","10 / 15","9 / 15"],
  ["Longest loss streak (days / months)","11 / 7","9 / 5"],
  ["Rolling 1y: min / median / max","–19.0% / +11.2% / +46.7%","–47.5% / +13.6% / +77.6%"],
  ["Rolling 1y windows positive","77%","79%"],
  ["Trailing 1y / 3y (ann.)","16.8% / 20.7%","16.3% / 22.5%"],
  ["Trailing 5y / 10y (ann.)","9.8% / 9.4%","13.6% / 15.5%"],
  ["2026 year-to-date","+12.2%","+14.2%"]], title="Returns", col_w=W2, highlight_col=1)

render("t_risk", ["Metric","Dual Momentum","S&P 500"],
 [["Annualised volatility","15.0%","19.2%"],["Downside deviation","10.7%","13.5%"],
  ["Upside volatility","10.5%","13.7%"],["Monthly volatility","3.7%","4.4%"],
  ["Maximum drawdown","–33.8%","–55.3%"],
  ["Max DD peak","19 Feb 2020","9 Oct 2007"],["Max DD trough","23 Mar 2020","9 Mar 2009"],
  ["Max DD recovery","9 Apr 2021","16 Aug 2012"],
  ["Days to trough / to recover","33 / 382","517 / 1,256"],
  ["Longest time underwater","3.1 years","6.1 years"],
  ["Average drawdown","–5.9% over 90 days","–6.0% over 89 days"],
  ["Drawdowns deeper than 10% / 20%","16 / 5","12 / 4"],
  ["Time below prior peak","90%","90%"],["Time more than 10% below peak","27%","36%"],
  ["Ulcer index","8.7%","15.3%"],["Pain index (mean drawdown)","6.4%","10.0%"],
  ["Daily VaR 95% / 99%","–1.46% / –2.77%","–1.82% / –3.36%"],
  ["Daily CVaR 95% / 99%","–2.32% / –3.88%","–2.87% / –4.83%"],
  ["Worst 5-day / 20-day","–18.0% / –30.9%","–18.3% / –30.9%"],
  ["Worst 63-day","–29.9%","–41.4%"],
  ["Skewness / excess kurtosis (daily)","–0.43 / 13.8","–0.14 / 9.9"],
  ["Tail ratio","0.95","0.96"]], title="Risk", col_w=W2, highlight_col=1)

render("t_drawdowns", ["#","Peak","Trough","Recovered","Depth","Days down","To recover"],
 [["1","19 Feb 2020","23 Mar 2020","9 Apr 2021","–33.8%","33","382"],
  ["2","3 Jan 2022","27 Oct 2023","15 May 2024","–22.4%","662","201"],
  ["3","20 Jul 2015","11 Feb 2016","21 Feb 2017","–21.0%","206","376"],
  ["4","29 Apr 2011","3 Oct 2011","13 Mar 2012","–21.0%","157","162"],
  ["5","26 Jan 2018","24 Dec 2018","26 Dec 2019","–20.0%","332","367"]],
 title="The five deepest drawdowns", col_w=[0.06,0.19,0.19,0.19,0.13,0.12,0.12])

render("t_riskadj", ["Metric","Dual Momentum","S&P 500"],
 [["Sharpe (rf = 0)","0.73","0.59"],["Sharpe standard error","±0.21","±0.20"],
  ["Sortino","1.02","0.83"],["Calmar (CAGR / max DD)","0.30","0.18"],
  ["Omega (threshold 0)","1.15","1.12"],["Martin ratio (CAGR / ulcer)","1.17","0.64"],
  ["Sterling ratio","0.65","0.62"],["Burke ratio","0.12","0.10"],
  ["Gain-to-pain (monthly)","0.88","0.66"],["Profit factor (monthly)","1.88","1.66"],
  ["Payoff ratio (monthly)","1.06","0.91"],["Return / volatility","0.68","0.51"],
  ["Months worse than –10%","0.8% (3 of 354)","1.4% (5 of 354)"]],
 title="Risk-adjusted", col_w=W2, highlight_col=1)

render("t_relative", ["Metric","Value"],
 [["Excess CAGR","+0.39 pts"],["Beta (full period)","0.52"],
  ["Beta in up / down markets","0.40 / 0.48"],["Jensen's alpha (annual)","+5.1%"],
  ["Correlation / R²","0.66 / 0.44"],["Tracking error","14.6%"],
  ["Information ratio","–0.03"],["Treynor ratio","0.20"],
  ["M² (Modigliani)","13.9%  (+4.1 pts at equal risk)"],
  ["Up capture / down capture (monthly)","77% / 62%"],["Capture ratio","1.24"],
  ["Months beating the index","25%  (90 of 354)"],
  ["Months matching the index","45%  (159 of 354)"],
  ["Years beating the index","30%"],
  ["Avg excess in index down months","+1.4%"],
  ["Avg excess in index up months","–0.8%"],
  ["Maximum relative drawdown","–73%"]],
 title="Relative to the S&P 500", col_w=[0.62,0.38])

render("t_trading", ["Metric","Value"],
 [["Rebalance checks","354 (monthly)"],["Rebalances that changed the position","32  (9%)"],
  ["Individual trades","63"],["Average holding period","232 trading days  (~11 months)"],
  ["Annual turnover","214%"],["Time allocated: US equities","49%"],
  ["Time allocated: Intl equities","29%"],["Time allocated: bonds","22%"],
  ["Time in risk assets","99.7%"],["Cost drag at 10 bps","0.21 pts of CAGR per year"]],
 title="Trading", col_w=[0.62,0.38])

render("t_rules", ["Role","Instrument used (1997–2026)","ETF equivalent"],
 [["US equities","VFINX — Vanguard 500 Index","SPY / VOO"],
  ["International equities","VGTSX — Vanguard Total International","VXUS / ACWX"],
  ["US bonds (safe asset)","VBMFX — Vanguard Total Bond Market","AGG / BND"],
  ["T-bill hurdle","Daily accrual from 13-week bill yield (^IRX)","BIL / SGOV"]],
 title="Instruments", col_w=[0.26,0.46,0.28])

render("t_setup", ["Setting","Value"],
 [["Data","Yahoo Finance daily closes, dividend-adjusted"],
  ["Period","1 May 1997 – 21 Oct 2026  (29.4 years)"],
  ["Rebalance","Monthly, signal on the last trading day's close"],
  ["Execution","Fill at the NEXT day's close — one-day lag, no look-ahead"],
  ["Costs","10 bps per unit of turnover, charged on fill"],
  ["Cash","T-bill accrual index from the 13-week bill yield"],
  ["Benchmark","VFINX buy-and-hold; 60/40 as a second reference"],
  ["Parameters fitted","None — 12-month lookback is the published rule"]],
 title="Backtest setup", col_w=[0.26,0.74])

render("t_episodes", ["Episode","GEM","S&P 500","What GEM held"],
 [["Dot-com bust, Mar 2000 – Oct 2002","–2.7%","–47.4%","Bonds 73%, Intl 18%, US 10%"],
  ["GFC, Oct 2007 – Mar 2009","–8.2%","–54.9%","Bonds 78%, Intl 22%"],
  ["Euro crisis, May – Oct 2011","–21.0%","–18.7%","Intl 60%, US 40%"],
  ["Correction, May 2015 – Feb 2016","–20.7%","–12.7%","US 77%, Bonds 23%"],
  ["Q4 2018","–18.8%","–18.8%","US 100%"],
  ["COVID crash, Feb – Mar 2020","–33.5%","–33.5%","US 100%"],
  ["COVID rebound, Mar – Dec 2020","+33.3%","+65.0%","US 68%, Bonds 32%"],
  ["2022 bear, Jan – Oct 2022","–19.2%","–24.1%","US 53%, Bonds 47%"],
  ["AI bull, 2023–2024","+36.0%","+57.5%","US 71%, Bonds 25%"],
  ["Tariff shock, Feb – Apr 2025","–18.6%","–18.6%","US 100%"]],
 title="Every major episode, 1997–2026", col_w=[0.40,0.13,0.14,0.33])

render("t_ablation", ["Variant","CAGR","Sharpe","Max drawdown"],
 [["Full Dual Momentum","10.3%","0.73","–33.8%"],
  ["Absolute momentum only (US vs T-bills)","9.9%","0.71","–33.8%"],
  ["Relative momentum only (US vs Intl)","9.0%","0.55","–61.1%"],
  ["S&P 500 buy-and-hold","9.9%","0.59","–55.3%"]],
 title="Which half does the work?", col_w=[0.46,0.18,0.18,0.18], highlight_col=1)

render("t_inout", ["Metric","1997–2013  (pre-publication)","2014–2026  (post-publication)"],
 [["GEM CAGR","12.1%","8.3%"],["GEM Sharpe","0.86","0.59"],["GEM max drawdown","–21.0%","–33.8%"],
  ["S&P 500 CAGR","7.0%","13.7%"],["S&P 500 Sharpe","0.43","0.83"],
  ["S&P 500 max drawdown","–55.3%","–33.8%"],
  ["GEM minus S&P 500, CAGR","+5.1 pts","–5.4 pts"]],
 title="Before and after the book was published", col_w=[0.34,0.33,0.33])

render("t_walkforward", ["2003–2025, 23 annual test windows","Annualised return"],
 [["Walk-forward optimised lookback","8.7%"],
  ["Fixed 12-month lookback","9.2%"],
  ["S&P 500","11.3%"]],
 title="Walk-forward: optimising made it worse", col_w=[0.62,0.38])