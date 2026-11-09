"""Render this article's data tables as PNGs (Medium strips HTML tables)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sitebuild.render import make_renderer, C
render = make_renderer(Path(__file__).parent / "tables")
S = json.load(open(Path(__file__).parent / "output" / "sma_trend_filter_summary.json"))
pc = lambda x: f"{x*100:.2f}%"
pc1 = lambda x: f"{x*100:.1f}%"

render("t_headline", ["Metric","SMA (10 mo)","Momentum (12 mo)","S&P 500","60/40"],
 [["CAGR", pc(S["sma"]["cagr"]), pc(S["momentum"]["cagr"]), pc(S["benchmark"]["cagr"]), pc(S["sixty_forty"]["cagr"])],
  ["Annualised volatility", pc1(S["sma"]["volatility"]), pc1(S["momentum"]["volatility"]), pc1(S["benchmark"]["volatility"]), pc1(S["sixty_forty"]["volatility"])],
  ["Sharpe (rf = 0)", f"{S['sma']['sharpe']:.2f}", f"{S['momentum']['sharpe']:.2f}", f"{S['benchmark']['sharpe']:.2f}", f"{S['sixty_forty']['sharpe']:.2f}"],
  ["Sortino", f"{S['sma_extended']['risk_adjusted']['sortino']:.2f}", f"{S['momentum_extended']['risk_adjusted']['sortino']:.2f}", "—", "—"],
  ["Maximum drawdown", pc1(S["sma"]["max_drawdown"]), pc1(S["momentum"]["max_drawdown"]), pc1(S["benchmark"]["max_drawdown"]), pc1(S["sixty_forty"]["max_drawdown"])],
  ["Calmar", f"{S['sma']['calmar']:.2f}", f"{S['momentum']['calmar']:.2f}", f"{S['benchmark']['calmar']:.2f}", f"{S['sixty_forty']['calmar']:.2f}"],
  ["Ulcer index", pc1(S["sma_extended"]["risk"]["ulcer_index"]), pc1(S["momentum_extended"]["risk"]["ulcer_index"]), "—", "—"],
  ["Worst year", pc1(S["sma"]["worst_year"]), pc1(S["momentum"]["worst_year"]), pc1(S["benchmark"]["worst_year"]), "—"],
  ["Up / down capture (monthly)", "72% / 64%", "77% / 66%", "100% / 100%", "—"],
  ["Beta to S&P 500", f"{S['sma']['beta']:.2f}", f"{S['momentum']['beta']:.2f}", "1.00", "—"],
  ["Signal switches in 40 years", "48", "27", "0", "0"],
  ["Annual turnover", f"{S['sma']['annual_turnover']*100:.0f}%", f"{S['momentum']['annual_turnover']*100:.0f}%", "3%", "22%"],
  ["Avg holding period", "209 days", "371 days", "—", "—"],
  ["Growth of $1", f"${S['sma']['total_return']+1:.0f}", f"${S['momentum']['total_return']+1:.0f}", f"${S['benchmark']['total_return']+1:.0f}", f"${S['sixty_forty']['total_return']+1:.0f}"]],
 title="Head to head, Jan 1987 - Oct 2026 (39.8 years)", col_w=[0.34,0.17,0.19,0.15,0.15], highlight_col=2)

c = S["comparison"]
render("t_agreement", ["Measure","Value"],
 [["Months compared", str(c["months"])],
  ["Months the two filters agreed", f"{c['agreement_rate']*100:.1f}%"],
  ["  both risk-on", f"{c['both_risk_on']*100:.1f}%"],
  ["  both risk-off", f"{c['both_risk_off']*100:.1f}%"],
  ["Months they disagreed", f"{(1-c['agreement_rate'])*100:.1f}%"],
  ["  SMA in, momentum out", f"{c['sma_on_mom_off']*100:.1f}%  ({c['n_sma_only_on']} months)"],
  ["  momentum in, SMA out", f"{c['mom_on_sma_off']*100:.1f}%  ({c['n_mom_only_on']} months)"],
  ["Time risk-on: SMA / momentum", f"{c['sma_risk_on_pct']*100:.1f}%  /  {c['mom_risk_on_pct']*100:.1f}%"],
  ["Switches: SMA / momentum", f"{c['sma_switches']}  /  {c['mom_switches']}"],
  ["Who was right when they disagreed", f"SMA {c['sma_right_when_disagree']*100:.0f}%   momentum {c['mom_right_when_disagree']*100:.0f}%"],
  ["Avg next-month equity return, SMA-only-in", pc(c["avg_fwd_equity_return_sma_only_on"])],
  ["Avg next-month equity return, momentum-only-in", pc(c["avg_fwd_equity_return_mom_only_on"])]],
 title="How often do the two filters actually differ?", col_w=[0.56,0.44])

render("t_episodes", ["Episode","SMA (10 mo)","Momentum (12 mo)","S&P 500"],
 [[e["episode"], pc1(e["sma"]), pc1(e["momentum"]), pc1(e["sp500"])] for e in S["episodes"]],
 title="Every major episode, 1987-2026", col_w=[0.46,0.18,0.20,0.16])

render("t_variants", ["Variant","CAGR","Sharpe","Max drawdown","Turnover"],
 [["10-month SMA filter", pc(S["sma"]["cagr"]), f"{S['sma']['sharpe']:.2f}", pc1(S["sma"]["max_drawdown"]), f"{S['sma']['annual_turnover']*100:.0f}%"],
  ["12-month absolute momentum", pc(S["momentum"]["cagr"]), f"{S['momentum']['sharpe']:.2f}", pc1(S["momentum"]["max_drawdown"]), f"{S['momentum']['annual_turnover']*100:.0f}%"],
  ["Both must agree (AND)", pc(S["combined_and"]["cagr"]), f"{S['combined_and']['sharpe']:.2f}", pc1(S["combined_and"]["max_drawdown"]), f"{S['combined_and']['annual_turnover']*100:.0f}%"],
  ["Either one is enough (OR)", pc(S["combined_or"]["cagr"]), f"{S['combined_or']['sharpe']:.2f}", pc1(S["combined_or"]["max_drawdown"]), f"{S['combined_or']['annual_turnover']*100:.0f}%"],
  ["SMA with T-bills instead of bonds", pc(S["sma_with_tbills"]["cagr"]), f"{S['sma_with_tbills']['sharpe']:.2f}", pc1(S["sma_with_tbills"]["max_drawdown"]), f"{S['sma_with_tbills']['annual_turnover']*100:.0f}%"],
  ["S&P 500 buy & hold", pc(S["benchmark"]["cagr"]), f"{S['benchmark']['sharpe']:.2f}", pc1(S["benchmark"]["max_drawdown"]), "3%"],
  ["60/40", pc(S["sixty_forty"]["cagr"]), f"{S['sixty_forty']['sharpe']:.2f}", pc1(S["sixty_forty"]["max_drawdown"]), "22%"]],
 title="Every variant tested", col_w=[0.40,0.15,0.13,0.17,0.15], highlight_col=1)

render("t_drawdowns", ["#","Peak","Trough","Recovered","Depth","Days down","To recover"],
 [[str(i+1), d["peak"], d["trough"], d["recovery"] or "not yet", pc1(d["depth"]),
   str(d["days_peak_to_trough"]), str(d["days_trough_to_recovery"] or "-")] for i, d in enumerate(S["drawdowns"][:5])],
 title="The five deepest drawdowns, 10-month SMA filter", col_w=[0.06,0.19,0.19,0.19,0.13,0.12,0.12])

dis = S["disagreement_episodes"][:6]
render("t_disagree", ["Period","Months","Who was in equities","Equities","Bonds","Right call?"],
 [[f"{d['from']} to {d['to']}", str(d["months"]), d["who_was_in"], pc1(d["equities"]), pc1(d["bonds"]),
   "yes" if d["right_call"] else "no"] for d in dis],
 title="The longest disagreements, and who was right", col_w=[0.28,0.10,0.22,0.13,0.13,0.14])

render("t_setup", ["Setting","Value"],
 [["Data","Yahoo Finance daily closes, dividend-adjusted"],
  ["Period","2 Jan 1987 - 22 Oct 2026  (39.8 years)"],
  ["Risky asset","VFINX (Vanguard 500 Index)"],
  ["Safe asset","VBMFX (Vanguard Total Bond Market); T-bills tested separately"],
  ["Signal","Month-end close vs 10-month SMA of month-end closes"],
  ["Warmup","VFINX history from 1980, so the average is defined from the first evaluated month"],
  ["Execution","Fill at the NEXT day's close - one-day lag, no look-ahead"],
  ["Costs","10 bps per unit of turnover, charged on fill"],
  ["Benchmark","VFINX buy-and-hold; 60/40 as a second reference"]],
 title="Backtest setup", col_w=[0.24,0.76])
