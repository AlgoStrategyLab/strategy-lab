"""Tables for article #6, rendered as PNGs (Medium strips HTML tables)."""
from __future__ import annotations

import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from sitebuild.render import make_renderer

OUT = Path(__file__).parent / "output"
render = make_renderer(Path(__file__).parent.parent.parent / "sitebuild" / "assets" / "tables")
S = json.load(open(OUT / "voltarget_summary.json"))

pct = lambda x, d=2: ("−" if x < 0 else "") + f"{abs(x)*100:.{d}f}%"
num = lambda x, d=2: ("−" if x < 0 else "") + f"{abs(x):.{d}f}"
by = lambda rows, k, v: next(r for r in rows if r[k] == v)

layer = S["layer"]
base_of = {r["name"]: r for r in layer if r["variant"] == "base"}
vt_of = {r["name"]: r for r in layer if r["variant"] == "vol target"}
names = list(base_of)

# 1 setup
render("vt_t_setup",
       ["Setting", "Value"],
       [["Data", "Yahoo Finance daily adjusted closes (VFINX, VGTSX, VBMFX, ^IRX)"],
        ["Window", "November 1981 – November 2026 for the equity books; 1997 for dual momentum"],
        ["Rule", "scale = target volatility ÷ trailing 60-day volatility of the strategy itself"],
        ["Target", f"{S['config']['target_vol']:.0%} annualised"],
        ["Cap", "1.0× the base position unless stated; the leverage section lifts it"],
        ["Execution", "measured at the rebalance close, filled at the next close"],
        ["Costs", f"{S['config']['cost_bps']:.0f} bps per unit of turnover; "
                  f"{S['config']['margin_bps']:.0f} bps over cash on any borrowed capital"],
        ["Cash", "uninvested weight earns nothing, which is the harshest reading"]],
       title="How the layer was tested", col_w=[0.17, 0.83])

# 2 headline
m, b, bm = S["main"], S["base"], S["benchmark"]
render("vt_t_headline",
       ["", "Buy & hold", "Volatility targeted", "Change"],
       [["CAGR", pct(b["cagr"]), pct(m["cagr"]), pct(m["cagr"] - b["cagr"])],
        ["Volatility", pct(b["volatility"]), pct(m["volatility"]), pct(m["volatility"] - b["volatility"])],
        ["Sharpe", num(b["sharpe"], 3), num(m["sharpe"], 3), "+" + num(m["sharpe"] - b["sharpe"], 3)],
        ["Sortino", num(b["sortino"], 3), num(m["sortino"], 3), "+" + num(m["sortino"] - b["sortino"], 3)],
        ["Worst drawdown", pct(b["max_drawdown"], 1), pct(m["max_drawdown"], 1),
         "+" + pct(m["max_drawdown"] - b["max_drawdown"], 1)],
        ["Calmar", num(b["calmar"], 3), num(m["calmar"], 3), "+" + num(m["calmar"] - b["calmar"], 3)],
        ["Beta to the index", num(b["beta"]), num(m["beta"]), num(m["beta"] - b["beta"])],
        ["Annual turnover", pct(b["annual_turnover"], 0), pct(m["annual_turnover"], 0),
         "+" + pct(m["annual_turnover"] - b["annual_turnover"], 0)],
        ["Average exposure", "100%", f"{S['scale_stats']['mean']:.0%}", ""]],
       title="The layer on S&P 500 buy & hold, November 1981 – November 2026",
       col_w=[0.34, 0.22, 0.24, 0.20], highlight_col=2)

# 3 every strategy
render("vt_t_layer",
       ["Strategy", "CAGR", "Vol", "Sharpe", "Worst DD", "Δ Sharpe", "Δ Worst DD", "Avg held"],
       [[n, f"{pct(base_of[n]['cagr'])} → {pct(vt_of[n]['cagr'])}",
         f"{pct(base_of[n]['volatility'])} → {pct(vt_of[n]['volatility'])}",
         f"{num(base_of[n]['sharpe'], 3)} → {num(vt_of[n]['sharpe'], 3)}",
         f"{pct(base_of[n]['max_drawdown'], 1)} → {pct(vt_of[n]['max_drawdown'], 1)}",
         "+" + num(vt_of[n]["d_sharpe"], 3), "+" + pct(vt_of[n]["d_maxdd"], 1),
         f"{vt_of[n]['avg_scale']:.0%}"] for n in names],
       title="Every rule in the series, before and after the layer (de-risking only)",
       col_w=[0.195, 0.140, 0.122, 0.132, 0.142, 0.093, 0.093, 0.083], highlight_col=5, fontsize=9.8)

# 4 the two controls
ctrl = {r["name"]: r for r in S["controls"]}
sm = S["shuffled_mean"]
render("vt_t_controls",
       ["", "CAGR", "Volatility", "Sharpe", "Worst drawdown"],
       [["No targeting at all", pct(b["cagr"]), pct(b["volatility"]), num(b["sharpe"], 3),
         pct(b["max_drawdown"], 1)],
        [f"Held flat at {ctrl['S&P 500 buy & hold']['scale']:.0%} throughout",
         pct(ctrl["S&P 500 buy & hold"]["cagr"]), pct(ctrl["S&P 500 buy & hold"]["volatility"]),
         num(ctrl["S&P 500 buy & hold"]["sharpe"], 3), pct(ctrl["S&P 500 buy & hold"]["max_drawdown"], 1)],
        ["Same sizes, shuffled dates (5 draws)", pct(sm["cagr"]), pct(sm["volatility"]),
         num(sm["sharpe"], 3), pct(sm["max_drawdown"], 1)],
        ["Volatility targeted", pct(m["cagr"]), pct(m["volatility"]), num(m["sharpe"], 3),
         pct(m["max_drawdown"], 1)]],
       title="Two controls: the same average exposure, and the same sizes on the wrong days",
       col_w=[0.40, 0.15, 0.15, 0.15, 0.15], highlight_col=3)

# 5 why
vp = S["vol_persistence"]
render("vt_t_persistence",
       ["Measured over 60-day windows, 1981–2026", "Correlation"],
       [["This window's volatility against the next window's volatility", num(vp["corr_next_60d"])],
        ["The same, by rank rather than level", num(vp["rank_corr"])],
        ["This window's volatility against the next window's return", num(vp["corr_return_next_60d"])],
        ["Overlapping windows in the sample", f"{vp['n']:,}"]],
       title="Why it works: one of these is forecastable and the other is not",
       col_w=[0.72, 0.28], highlight_col=1)

# 6 leverage
lev = {r["name"]: r for r in S["levered"]}
render("vt_t_leverage",
       ["Strategy", "Sharpe, no leverage", "Sharpe, 2× cap", "Time levered", "Avg borrowed"],
       [[n, num(vt_of[n]["sharpe"], 3), num(lev[n]["sharpe"], 3),
         f"{lev[n]['time_levered']:.0%}", f"{lev[n]['avg_borrowed']:.0%}"] for n in names],
       title="Letting the rule borrow: helpful on the trend rules, ruinous on RSI(2)",
       col_w=[0.32, 0.19, 0.17, 0.16, 0.16], highlight_col=2)

# 7 cap sweep
render("vt_t_cap",
       ["Leverage cap", "CAGR", "Sharpe", "Worst drawdown", "Time levered", "Margin cost/yr"],
       [[f"{r['max_scale']:.2f}×", pct(r["cagr"]), num(r["sharpe"], 3),
         pct(r["max_drawdown"], 1), f"{r['time_levered']:.0%}", pct(r["annual_margin_cost"], 2)]
        for r in S["cap_sweep"]],
       title="How far to let it borrow, on S&P 500 buy & hold",
       col_w=[0.16, 0.17, 0.17, 0.18, 0.16, 0.16], highlight_col=2)

# 8 target sweep
render("vt_t_target",
       ["Volatility target", "CAGR", "Realised vol", "Sharpe", "Worst drawdown", "Turnover"],
       [[f"{r['target_vol']:.0%}", pct(r["cagr"]), pct(r["volatility"]), num(r["sharpe"], 3),
         pct(r["max_drawdown"], 1), pct(r["annual_turnover"], 0)] for r in S["target_sweep"]],
       title="The target sets the risk, not the Sharpe",
       col_w=[0.19, 0.16, 0.17, 0.16, 0.18, 0.14], highlight_col=3)

# 9 lookback sweep
render("vt_t_lookback",
       ["Lookback", "CAGR", "Sharpe", "Worst drawdown", "Turnover"],
       [[f"{r['lookback']} days", pct(r["cagr"]), num(r["sharpe"], 3), pct(r["max_drawdown"], 1),
         pct(r["annual_turnover"], 0)] for r in S["lookback_sweep"]] +
       [[f"EWMA, {S['config']['lookback']}-day", pct(S["method_sweep"][1]["cagr"]),
         num(S["method_sweep"][1]["sharpe"], 3), pct(S["method_sweep"][1]["max_drawdown"], 1),
         pct(S["method_sweep"][1]["annual_turnover"], 0)]],
       title="How long to look back, and whether to weight recent days more",
       col_w=[0.24, 0.19, 0.19, 0.21, 0.17], highlight_col=2)

# 10 costs
render("vt_t_costs",
       ["Round-trip cost", "CAGR", "Sharpe", "Worst drawdown", "Buy & hold CAGR"],
       [[f"{r['cost_bps']:.0f} bps", pct(r["cagr"]), num(r["sharpe"], 3), pct(r["max_drawdown"], 1),
         pct(r["base_cagr"])] for r in S["cost_sweep"]],
       title="What the extra trading costs",
       col_w=[0.22, 0.19, 0.19, 0.21, 0.19], highlight_col=1)

# 11 in/out
io = S["in_out_sample"]
render("vt_t_inout",
       ["Period", "Buy & hold CAGR", "Targeted CAGR", "Buy & hold Sharpe", "Targeted Sharpe", "Δ"],
       [[f"Before 2017 ({io['in_sample']['start'][:4]}–2016)", pct(io["in_sample"]["base_cagr"]),
         pct(io["in_sample"]["vt_cagr"]), num(io["in_sample"]["base_sharpe"], 3),
         num(io["in_sample"]["vt_sharpe"], 3), "+" + num(io["in_sample"]["d_sharpe"], 3)],
        ["2017 onwards", pct(io["out_of_sample"]["base_cagr"]), pct(io["out_of_sample"]["vt_cagr"]),
         num(io["out_of_sample"]["base_sharpe"], 3), num(io["out_of_sample"]["vt_sharpe"], 3),
         num(io["out_of_sample"]["d_sharpe"], 3)]],
       title="Before and after Moreira & Muir published",
       col_w=[0.24, 0.17, 0.16, 0.18, 0.16, 0.09], highlight_col=5)

# 12 episodes
render("vt_t_episodes",
       ["Episode", "S&P 500", "Volatility targeted", "Average exposure held"],
       [[r["name"], pct(r["sp500"], 1), pct(r["vt"], 1), f"{r['avg_scale']:.0%}"]
        for r in S["episodes"]],
       title="Total return through each episode, and how much was held through it",
       col_w=[0.34, 0.22, 0.24, 0.20], highlight_col=3)
