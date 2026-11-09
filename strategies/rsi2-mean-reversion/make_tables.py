"""Render this article's data tables as PNGs (Medium strips HTML tables)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sitebuild.render import make_renderer  # noqa: E402

render = make_renderer(Path(__file__).parent / "tables")

S = json.load(open(Path(__file__).parent / "output" / "rsi2_summary.json"))

pc = lambda x: f"{x*100:.2f}%".replace("-", "−")
pc1 = lambda x: f"{x*100:.1f}%".replace("-", "−")
n2 = lambda x: f"{x:.2f}"
cfg, main, bench = S["config"], S["main"], S["benchmark"]
tr, ex, edge = S["trades"], S["exposure"], S["signal_edge"]

render("rsi_t_setup", ["Setting", "Value"], [
    ["Rule", "RSI(2) below 5, price above its 200-day SMA; exit on a close above SMA(5)"],
    ["Published in", "Connors & Alvarez, Short Term Trading Strategies That Work (2008)"],
    ["Universe", "VFINX (S&P 500 index fund), T-bills via ^IRX while flat"],
    ["Period", f"2 January 1987 to 6 November 2026 ({ex['total_days']:,} trading days, 39.8 years)"],
    ["Evaluation", "Daily bars, signal at the close, fill at the next close"],
    ["Costs", f"{cfg['cost_bps']} bps per unit of turnover"],
    ["Data", "Yahoo Finance adjusted closes (dividends reinvested)"],
], title="Backtest setup", col_w=[0.22, 0.78])

render("rsi_t_headline", ["Metric", "RSI(2)", "10-mo SMA filter", "60/40", "S&P 500"], [
    ["CAGR", pc(main["cagr"]), pc(S["sma_filter_monthly"]["cagr"]), pc(S["sixty_forty"]["cagr"]), pc(bench["cagr"])],
    ["Annualised volatility", pc1(main["volatility"]), pc1(S["sma_filter_monthly"]["volatility"]),
     pc1(S["sixty_forty"]["volatility"]), pc1(bench["volatility"])],
    ["Sharpe (rf = 0)", n2(main["sharpe"]), n2(S["sma_filter_monthly"]["sharpe"]),
     n2(S["sixty_forty"]["sharpe"]), n2(bench["sharpe"])],
    ["Max drawdown", pc1(main["max_drawdown"]), pc1(S["sma_filter_monthly"]["max_drawdown"]),
     pc1(S["sixty_forty"]["max_drawdown"]), pc1(bench["max_drawdown"])],
    ["Annual turnover", pc0 := f"{main['annual_turnover']*100:.0f}%",
     f"{S['sma_filter_monthly']['annual_turnover']*100:.0f}%",
     f"{S['sixty_forty']['annual_turnover']*100:.0f}%", f"{bench.get('annual_turnover', 0)*100:.0f}%"],
    ["Time invested", pc1(ex["exposure"]), "77%", "100%", "100%"],
], title="Headline results, January 1987 – November 2026", highlight_col=1)

render("rsi_t_trades", ["Trade statistic", "Value"], [
    ["Trades", f"{tr['trades']}"],
    ["Trades per year", f"{tr['trades_per_year']}"],
    ["Average holding period", f"{tr['avg_holding_days']} trading days"],
    ["Longest holding period", f"{tr['max_holding_days']} trading days"],
    ["Win rate", pc1(tr["win_rate"])],
    ["Average trade", pc(tr["avg_trade"])],
    ["Average winner", pc(tr["avg_win"])],
    ["Average loser", pc(tr["avg_loss"])],
    ["Payoff ratio (avg win / avg loss)", n2(tr["payoff_ratio"])],
    ["Best trade", pc1(tr["best_trade"])],
    ["Worst trade", pc1(tr["worst_trade"])],
], title="It wins most of the time, and wins slightly less than it loses", col_w=[0.56, 0.44])

render("rsi_t_exposure", ["", "Value"], [
    ["Days invested", f"{ex['days_in_market']:,} of {ex['total_days']:,}"],
    ["Share of trading days invested", pc(ex["exposure"])],
    ["Growth while invested", f"{ex['growth_while_invested']:.2f}×"],
    ["Annualised return while invested", pc1(ex["annualised_while_invested"])],
    ["Average daily return, invested", pc(ex["avg_daily_return_in_market"])],
    ["Average daily return, in cash", pc(ex["avg_daily_return_out"])],
    ["S&P 500 annualised, whole period", pc(bench["cagr"])],
], title="The signal is good. It is almost never available.", col_w=[0.58, 0.42])

render("rsi_t_edge", ["Condition", "Occurrences", "Avg 5-day forward return", "Share positive"], [
    ["Any day (baseline)", f"{ex['total_days']:,}", pc(edge["baseline_avg_fwd5"]), pc1(edge["baseline_pct_up_5d"])],
    ["RSI(2) below 5", f"{edge['n_rsi_below_5']}", pc(edge["after_rsi_below_5_avg_fwd5"]), pc1(edge["after_rsi_below_5_pct_up"])],
    ["…and above the 200-day SMA", f"{edge['n_above200_and_oversold']}", pc(edge["above200_and_oversold_avg_fwd5"]),
     pc1(edge["above200_and_oversold_pct_up"])],
    ["…and below the 200-day SMA", f"{edge['n_below200_and_oversold']}", pc(edge["below200_and_oversold_avg_fwd5"]),
     pc1(edge["below200_and_oversold_pct_up"])],
], title="The oversold signal works. The trend filter removes the best half of it.",
   col_w=[0.40, 0.17, 0.26, 0.17])

render("rsi_t_components", ["Variant", "CAGR", "Sharpe", "Max DD", "Turnover", "Time invested"], [
    ["RSI(2) < 5, 200-day filter (published)", pc(main["cagr"]), n2(main["sharpe"]), pc1(main["max_drawdown"]),
     f"{main['annual_turnover']*100:.0f}%", pc1(ex["exposure"])],
    ["RSI(2) < 5, no trend filter", pc(S["no_trend_filter"]["cagr"]), n2(S["no_trend_filter"]["sharpe"]),
     pc1(S["no_trend_filter"]["max_drawdown"]), f"{S['no_trend_filter']['annual_turnover']*100:.0f}%", "12.4%"],
    ["200-day filter only, no RSI", pc(S["trend_filter_only"]["cagr"]), n2(S["trend_filter_only"]["sharpe"]),
     pc1(S["trend_filter_only"]["max_drawdown"]), f"{S['trend_filter_only']['annual_turnover']*100:.0f}%", "76%"],
    ["Exit on RSI(2) > 65 instead of SMA(5)", pc(S["exit_on_rsi"]["cagr"]), n2(S["exit_on_rsi"]["sharpe"]),
     pc1(S["exit_on_rsi"]["max_drawdown"]), f"{S['exit_on_rsi']['annual_turnover']*100:.0f}%", "—"],
    ["Fixed 5-day hold", pc(S["fixed_5day_hold"]["cagr"]), n2(S["fixed_5day_hold"]["sharpe"]),
     pc1(S["fixed_5day_hold"]["max_drawdown"]), f"{S['fixed_5day_hold']['annual_turnover']*100:.0f}%", "—"],
    ["Parked in bonds while flat", pc(S["parked_in_bonds"]["cagr"]), n2(S["parked_in_bonds"]["sharpe"]),
     pc1(S["parked_in_bonds"]["max_drawdown"]), f"{S['parked_in_bonds']['annual_turnover']*100:.0f}%", "—"],
], title="Switching each component off", col_w=[0.34, 0.13, 0.12, 0.13, 0.13, 0.15], highlight_col=0)

render("rsi_t_costs", ["Round-trip cost", "CAGR", "Sharpe", "Max drawdown"],
       [[f"{r['cost_bps']} bps", pc(r["cagr"]), n2(r["sharpe"]), pc1(r["max_drawdown"])]
        for r in S["cost_sensitivity"]],
       title=f"Cost sensitivity at {main['annual_turnover']*100:.0f}% annual turnover",
       col_w=[0.28, 0.24, 0.24, 0.24])

io = S["in_out_sample"]
render("rsi_t_inout", ["", "RSI(2) CAGR", "RSI(2) Sharpe", "RSI(2) max DD", "S&P 500 CAGR"], [
    ["1987–2008, before publication", pc(io["in_sample"]["cagr"]), n2(io["in_sample"]["sharpe"]),
     pc1(io["in_sample"]["max_drawdown"]), pc(io["benchmark_in_sample"]["cagr"])],
    ["2009–2026, after publication", pc(io["out_of_sample"]["cagr"]), n2(io["out_of_sample"]["sharpe"]),
     pc1(io["out_of_sample"]["max_drawdown"]), pc(io["benchmark_out_of_sample"]["cagr"])],
], title="Before and after the book", col_w=[0.34, 0.17, 0.17, 0.16, 0.16])

render("rsi_t_regimes", ["Episode", "RSI(2)", "10-mo SMA filter", "S&P 500"],
       [[r["regime"], pc1(r["rsi2"]), pc1(r["sma_filter"]), pc1(r["sp500"])] for r in S["regimes"]],
       title="Total return through each episode", col_w=[0.46, 0.18, 0.2, 0.16])

print("tables written")
