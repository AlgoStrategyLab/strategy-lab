"""Render this article's data tables as PNGs (Medium strips HTML tables)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sitebuild.render import make_renderer, C
render = make_renderer(Path(__file__).parent / "tables")
S = json.load(open(Path(__file__).parent / "output" / "donchian_summary.json"))
pc = lambda x: f"{x*100:.2f}%"
p1 = lambda x: f"{x*100:.1f}%"
d, m55, dv = S["donchian_20_10"], S["donchian_55_20"], S["donchian_vol_sized"]
sma, mom, bm, sf = S["sma"], S["momentum"], S["benchmark"], S["sixty_forty"]
e = S["donchian_extended"]; sg = S["signals"]

render("t_headline", ["Metric","Donchian 20/10","SMA (10 mo)","Momentum (12 mo)","S&P 500"],
 [["Growth of $1", f"${d['total_return']+1:.0f}", f"${sma['total_return']+1:.0f}", f"${mom['total_return']+1:.0f}", f"${bm['total_return']+1:.0f}"],
  ["CAGR", pc(d["cagr"]), pc(sma["cagr"]), pc(mom["cagr"]), pc(bm["cagr"])],
  ["Annualised volatility", p1(d["volatility"]), p1(sma["volatility"]), p1(mom["volatility"]), p1(bm["volatility"])],
  ["Sharpe (rf = 0)", f"{d['sharpe']:.2f}", f"{sma['sharpe']:.2f}", f"{mom['sharpe']:.2f}", f"{bm['sharpe']:.2f}"],
  ["Maximum drawdown", p1(d["max_drawdown"]), p1(sma["max_drawdown"]), p1(mom["max_drawdown"]), p1(bm["max_drawdown"])],
  ["Calmar", f"{d['calmar']:.2f}", f"{sma['calmar']:.2f}", f"{mom['calmar']:.2f}", f"{bm['calmar']:.2f}"],
  ["Worst year", p1(d["worst_year"]), p1(sma["worst_year"]), p1(mom["worst_year"]), p1(bm["worst_year"])],
  ["Beta to S&P 500", f"{d['beta']:.2f}", f"{sma['beta']:.2f}", f"{mom['beta']:.2f}", "1.00"],
  ["Up / down capture (monthly)", "42% / 38%", "72% / 64%", "77% / 66%", "100% / 100%"],
  ["Signal switches", str(sg["s1_switches"]), "48", "27", "0"],
  ["Annual turnover", f"{d['annual_turnover']*100:.0f}%", f"{sma['annual_turnover']*100:.0f}%", f"{mom['annual_turnover']*100:.0f}%", "3%"],
  ["Cost drag at 10 bps", f"{e['trading']['avg_cost_drag_annual']*100:.2f} pts/yr", "0.11 pts/yr", "0.06 pts/yr", "—"]],
 title="Donchian against the previous two filters, Jan 1987 - Oct 2026", col_w=[0.32,0.18,0.17,0.19,0.14], highlight_col=1)

render("t_trading", ["Measure","System 1 (20/10)","System 2 (55/20)"],
 [["Entries over 39.8 years", str(sg["s1_entries"]), str(sg["s2_entries"])],
  ["Signal switches", str(sg["s1_switches"]), str(sg["s2_switches"])],
  ["Switches per year", str(sg["s1_switches_per_year"]), str(sg["s2_switches_per_year"])],
  ["Average holding period", f"{sg['s1_avg_holding_days']} trading days", f"{sg['s2_avg_holding_days']} trading days"],
  ["Time invested in equities", p1(sg["s1_time_in_market"]), p1(sg["s2_time_in_market"])],
  ["Annual turnover", f"{d['annual_turnover']*100:.0f}%", f"{m55['annual_turnover']*100:.0f}%"],
  ["CAGR", pc(d["cagr"]), pc(m55["cagr"])],
  ["Maximum drawdown", p1(d["max_drawdown"]), p1(m55["max_drawdown"])]],
 title="How much this rule trades", col_w=[0.44,0.28,0.28], highlight_col=1)

render("t_edge", ["Measure","After a 20-day breakout","Any random day"],
 [["Chance the S&P is higher 20 days later", p1(sg["s1_pct_entries_up_20d"]), p1(sg["baseline_pct_up_20d"])],
  ["Average S&P return over the next 20 days", pc(sg["s1_avg_fwd20_after_entry"]), pc(sg["baseline_avg_fwd20"])],
  ["Sample size", f"{sg['s1_entries']} breakouts", f"{sg['days']:,} days"]],
 title="Does a breakout predict anything? (S&P 500, 1987-2026)", col_w=[0.48,0.26,0.26])

render("t_episodes", ["Episode","Donchian 20/10","SMA (10 mo)","Momentum (12 mo)","S&P 500"],
 [[x["episode"], p1(x["donchian"]), p1(x["sma"]), p1(x["momentum"]), p1(x["sp500"])] for x in S["episodes"]],
 title="Every major episode, 1987-2026", col_w=[0.34,0.18,0.16,0.18,0.14], highlight_col=1)

render("t_variants", ["Variant","CAGR","Sharpe","Max drawdown","Turnover"],
 [["Donchian 20/10 (Turtle System 1)", pc(d["cagr"]), f"{d['sharpe']:.2f}", p1(d["max_drawdown"]), f"{d['annual_turnover']*100:.0f}%"],
  ["Donchian 55/20 (Turtle System 2)", pc(m55["cagr"]), f"{m55['sharpe']:.2f}", p1(m55["max_drawdown"]), f"{m55['annual_turnover']*100:.0f}%"],
  ["Donchian 20/10, volatility-sized", pc(dv["cagr"]), f"{dv['sharpe']:.2f}", p1(dv["max_drawdown"]), f"{dv['annual_turnover']*100:.0f}%"],
  ["Best grid cell tested (55/50)", "8.52%", "0.76", "-29.9%", "570%"],
  ["10-month SMA filter (monthly)", pc(sma["cagr"]), f"{sma['sharpe']:.2f}", p1(sma["max_drawdown"]), f"{sma['annual_turnover']*100:.0f}%"],
  ["12-month absolute momentum (monthly)", pc(mom["cagr"]), f"{mom['sharpe']:.2f}", p1(mom["max_drawdown"]), f"{mom['annual_turnover']*100:.0f}%"],
  ["60/40", pc(sf["cagr"]), f"{sf['sharpe']:.2f}", p1(sf["max_drawdown"]), f"{sf['annual_turnover']*100:.0f}%"],
  ["S&P 500 buy & hold", pc(bm["cagr"]), f"{bm['sharpe']:.2f}", p1(bm["max_drawdown"]), "3%"]],
 title="Every variant tested", col_w=[0.42,0.14,0.13,0.17,0.14], highlight_col=1)

b = S["basket"]
render("t_basket", ["Variant (from Feb 2006)","CAGR","Sharpe","Max drawdown","Turnover"],
 [["Donchian 20/10 across 6 assets", pc(b["basket"]["cagr"]), f"{b['basket']['sharpe']:.2f}", p1(b["basket"]["max_drawdown"]), f"{b['basket']['annual_turnover']*100:.0f}%"],
  ["Donchian 20/10 on SPY alone", pc(b["single_spy"]["cagr"]), f"{b['single_spy']['sharpe']:.2f}", p1(b["single_spy"]["max_drawdown"]), f"{b['single_spy']['annual_turnover']*100:.0f}%"],
  ["SPY buy & hold", pc(b["spy_buy_hold"]["cagr"]), f"{b['spy_buy_hold']['sharpe']:.2f}", p1(b["spy_buy_hold"]["max_drawdown"]), "5%"]],
 title="Does diversifying rescue it? SPY, EFA, TLT, GLD, DBC, VNQ", col_w=[0.42,0.14,0.13,0.17,0.14])

io = S["in_out_sample"]
render("t_inout", ["Metric","1987-2002 (before the rules went public)","2003-2026 (after)"],
 [["Donchian CAGR", pc(io["in_sample"]["cagr"]), pc(io["out_of_sample"]["cagr"])],
  ["Donchian Sharpe", f"{io['in_sample']['sharpe']:.2f}", f"{io['out_of_sample']['sharpe']:.2f}"],
  ["Donchian max drawdown", p1(io["in_sample"]["max_drawdown"]), p1(io["out_of_sample"]["max_drawdown"])],
  ["S&P 500 CAGR", pc(io["benchmark_in_sample"]["cagr"]), pc(io["benchmark_out_of_sample"]["cagr"])],
  ["Donchian minus S&P 500", f"{(io['in_sample']['cagr']-io['benchmark_in_sample']['cagr'])*100:+.1f} pts", f"{(io['out_of_sample']['cagr']-io['benchmark_out_of_sample']['cagr'])*100:+.1f} pts"]],
 title="Before and after the Turtle rules were published free in 2003", col_w=[0.34,0.36,0.30])

render("t_setup", ["Setting","Value"],
 [["Data","Yahoo Finance daily closes, dividend-adjusted"],
  ["Period","2 Jan 1987 - 28 Oct 2026  (39.8 years)"],
  ["Risky asset","VFINX (Vanguard 500 Index)"],
  ["Safe asset","VBMFX (Vanguard Total Bond Market)"],
  ["Entry","Close above the highest close of the prior 20 trading days"],
  ["Exit","Close below the lowest close of the prior 10 trading days"],
  ["Evaluation","Every trading day (this is a daily system, unlike articles 1 and 2)"],
  ["Execution","Fill at the NEXT day's close - one-day lag, no look-ahead"],
  ["Costs","10 bps per unit of turnover; 0-50 bps tested"],
  ["Not modelled","Shorting, leverage, pyramiding, futures markets - see the caveats section"]],
 title="Backtest setup", col_w=[0.22,0.78])
