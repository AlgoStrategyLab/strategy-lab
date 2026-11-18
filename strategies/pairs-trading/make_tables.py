"""Render this article's data tables as PNGs (Medium strips HTML tables)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sitebuild.render import make_renderer  # noqa: E402

render = make_renderer(Path(__file__).parent / "tables")
S = json.load(open(Path(__file__).parent / "output" / "pairs_summary.json"))

pc = lambda x: f"{x*100:.2f}%".replace("-", "−")
pc1 = lambda x: f"{x*100:.1f}%".replace("-", "−")
n2 = lambda x: f"{x:.2f}".replace("-", "−")
n3 = lambda x: f"{x:.3f}".replace("-", "−")
cfg, main, bench, tr = S["config"], S["main"], S["benchmark"], S["trades"]

render("pt_t_setup", ["Setting", "Value"], [
    ["Rule", "12-month formation, 5 closest pairs by sum of squared deviation, enter at 2 sigma, "
             "exit on convergence or at the end of a 6-month window"],
    ["Published in", "Gatev, Goetzmann & Rouwenhorst (2006), Review of Financial Studies"],
    ["Universe", "22 liquid US-listed ETFs: 5 broad indices, 9 sector SPDRs, 8 country funds"],
    ["Period", "January 2000 to November 2026"],
    ["Execution", "Daily bars, signal at the close, fill at the next close"],
    ["Costs", f"{cfg['cost_bps']} bps per unit of turnover, plus {cfg['borrow_bps']} bps a year to borrow the short leg"],
    ["Data", "Yahoo Finance adjusted closes (dividends reinvested)"],
], title="Backtest setup", col_w=[0.19, 0.81])

render("pt_t_headline", ["Metric", "Pairs trading", "S&P 500", "60/40 proxy"], [
    ["CAGR", pc(main["cagr"]), pc(bench["cagr"]), pc(S["sixty_forty"]["cagr"])],
    ["Annualised volatility", pc1(main["volatility"]), pc1(bench["volatility"]), pc1(S["sixty_forty"]["volatility"])],
    ["Sharpe (rf = 0)", n2(main["sharpe"]), n2(bench["sharpe"]), n2(S["sixty_forty"]["sharpe"])],
    ["Max drawdown", pc1(main["max_drawdown"]), pc1(bench["max_drawdown"]), pc1(S["sixty_forty"]["max_drawdown"])],
    ["Beta to the S&P 500", n3(main["beta"]), "1.000", n2(S["sixty_forty"]["beta"])],
    ["Annual turnover", f"{main['annual_turnover']*100:.0f}%", "0%", f"{S['sixty_forty']['annual_turnover']*100:.0f}%"],
    ["Average gross exposure", pc1(main["avg_gross_exposure"]), "100%", "100%"],
    ["Average net exposure", pc1(main["avg_net_exposure"]), "100%", "100%"],
], title="Headline results, January 2000 – November 2026", highlight_col=1)

render("pt_t_selection", ["", "CAGR", "Sharpe", "Volatility", "Max drawdown"], [
    ["Closest-tracking pairs (the method)", pc(main["cagr"]), n2(main["sharpe"]),
     pc1(main["volatility"]), pc1(main["max_drawdown"])],
    ["Pairs drawn at random, average of 5", pc(S["random_pairs_mean"]["cagr"]), n2(S["random_pairs_mean"]["sharpe"]),
     pc1(S["random_pairs_mean"]["volatility"]), pc1(S["random_pairs_mean"]["max_drawdown"])],
], title="The selection step, against a coin flip", col_w=[0.40, 0.15, 0.15, 0.15, 0.15], highlight_col=0)

render("pt_t_costs", ["Round-trip cost", "CAGR", "Sharpe", "Max drawdown"],
       [[f"{r['cost_bps']} bps", pc(r["cagr"]), n2(r["sharpe"]), pc1(r["max_drawdown"])]
        for r in S["cost_sensitivity"]],
       title=f"Cost sensitivity at {main['annual_turnover']*100:.0f}% annual turnover",
       col_w=[0.28, 0.24, 0.24, 0.24])

render("pt_t_borrow", ["Borrow cost", "CAGR", "Sharpe", "Annual drag"],
       [[f"{r['borrow_bps']} bps/yr", pc(r["cagr"]), n2(r["sharpe"]), pc(r["annual_borrow_cost"])]
        for r in S["borrow_sensitivity"]],
       title="What the short leg costs to carry", col_w=[0.28, 0.24, 0.24, 0.24])

render("pt_t_pairs", ["Pairs carried", "CAGR", "Sharpe", "Volatility", "Max DD", "Gross exposure"],
       [[str(r["n_pairs"]), pc(r["cagr"]), n2(r["sharpe"]), pc1(r["volatility"]),
         pc1(r["max_drawdown"]), pc1(r["avg_gross_exposure"])] for r in S["pair_sweep"]],
       title="More pairs means steadier, not better", col_w=[0.19, 0.17, 0.15, 0.17, 0.16, 0.16])

render("pt_t_sigma", ["Entry threshold", "CAGR", "Sharpe", "Max DD", "Turnover", "Gross exposure"],
       [[f"{r['entry_sigma']:.1f} sigma", pc(r["cagr"]), n2(r["sharpe"]), pc1(r["max_drawdown"]),
         f"{r['annual_turnover']*100:.0f}%", pc1(r["avg_gross_exposure"])] for r in S["sigma_sweep"]],
       title="Trading less is the only thing that helps", col_w=[0.21, 0.16, 0.14, 0.15, 0.17, 0.17])

io = S["in_out_sample"]
render("pt_t_inout", ["", "CAGR", "Sharpe", "Volatility", "Beta", "S&P 500 CAGR"], [
    ["2000–2006, before the paper", pc(io["in_sample"]["cagr"]), n2(io["in_sample"]["sharpe"]),
     pc1(io["in_sample"]["volatility"]), n3(io["in_sample"]["beta"]), pc(io["benchmark_in_sample"]["cagr"])],
    ["2007–2026, after the paper", pc(io["out_of_sample"]["cagr"]), n2(io["out_of_sample"]["sharpe"]),
     pc1(io["out_of_sample"]["volatility"]), n3(io["out_of_sample"]["beta"]), pc(io["benchmark_out_of_sample"]["cagr"])],
], title="Before and after publication", col_w=[0.30, 0.14, 0.13, 0.15, 0.13, 0.15])

render("pt_t_trades", ["Trade statistic", "Value"], [
    ["Positions opened", f"{tr['trades']}"],
    ["Converged, as the premise requires", f"{tr['converged']} ({tr['convergence_rate']*100:.0f}%)"],
    ["Closed at the window end, never converged", f"{tr['closed_at_period_end']}"],
    ["Average holding period", f"{tr['avg_holding_days']} calendar days"],
    ["Median holding period", f"{tr['median_holding_days']:.0f} calendar days"],
    ["Distinct pairs ever traded", f"{tr['distinct_pairs']} of 231 possible"],
    ["Most-selected pair", f"{tr['top_pairs'][0]['pair']} ({tr['top_pairs'][0]['times_selected']} windows)"],
], title="The premise fails more often than it holds", col_w=[0.60, 0.40])

render("pt_t_episodes", ["Episode", "Pairs trading", "S&P 500"],
       [[r["episode"], pc1(r["pairs"]), pc1(r["sp500"])] for r in S["episodes"]],
       title="Total return through each episode", col_w=[0.50, 0.25, 0.25])

print("tables written")
