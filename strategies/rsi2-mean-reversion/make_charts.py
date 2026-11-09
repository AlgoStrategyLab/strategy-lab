"""Charts for article #4 from output/rsi2_*.json/csv. Light-mode palette, shared across the series."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "output"
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
     "violet": "#6250d6", "red": "#e34948", "ink": "#0b0b0b", "ink2": "#52514e",
     "grid": "#e6e5e2", "surface": "#fcfcfb"}
plt.rcParams.update({
    "figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "axes.edgecolor": C["grid"],
    "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 13,
    "axes.titlecolor": C["ink"], "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"],
    "ytick.color": C["ink2"], "font.size": 10.5, "font.family": "DejaVu Sans",
    "legend.frameon": False, "legend.fontsize": 10,
})

S = json.load(open(OUT / "rsi2_summary.json"))
s = pd.read_csv(OUT / "rsi2_series.csv", index_col=0, parse_dates=True)
sig = pd.read_csv(OUT / "signals.csv", index_col=0, parse_dates=True)

# 1. Growth of $1 -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.2), dpi=160)
ax.plot(s.index, s["SP500"], color=C["orange"], lw=1.8, label="S&P 500")
ax.plot(s.index, s["SMA"], color=C["aqua"], lw=1.5, label="10-month SMA filter (article #2)")
ax.plot(s.index, s["SixtyForty"], color=C["yellow"], lw=1.3, label="60/40")
ax.plot(s.index, s["RSI2"], color=C["blue"], lw=2.3, label="RSI(2) mean reversion")
ax.set_yscale("log")
ax.set_yticks([1, 2, 4, 8, 16, 32, 64]); ax.set_yticklabels([f"${v}" for v in [1, 2, 4, 8, 16, 32, 64]])
for col, colr in [("RSI2", C["blue"]), ("SP500", C["orange"]), ("SMA", C["aqua"]), ("SixtyForty", C["yellow"])]:
    ax.text(s.index[-1], s[col].iloc[-1], f"  ${s[col].iloc[-1]:.1f}", color=colr, va="center", fontweight="semibold")
ax.set_xlim(s.index[0], s.index[-1] + pd.Timedelta(days=1400))
ax.set_title("Growth of $1, January 1987 – November 2026 (log scale)")
ax.legend(loc="upper left")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
fig.tight_layout(); fig.savefig(OUT / "rsi_c1_equity.png"); plt.close(fig)

# 2. Where the return actually comes from -------------------------------------
exp = S["exposure"]
cash_growth = (1 + exp["avg_daily_return_out"]) ** (exp["total_days"] - exp["days_in_market"])
trade_growth = exp["growth_while_invested"]
yrs = exp["total_days"] / 252
fig, ax = plt.subplots(figsize=(9.5, 4.0), dpi=160)
parts = [("T-bill interest\nwhile flat", cash_growth ** (1 / yrs) - 1, C["ink2"]),
         ("The trades\nthemselves", trade_growth ** (1 / yrs) - 1, C["blue"]),
         ("Total\n(strategy CAGR)", S["main"]["cagr"], C["violet"]),
         ("S&P 500\nbuy & hold", S["benchmark"]["cagr"], C["orange"])]
xs = np.arange(len(parts))
ax.bar(xs, [p[1] * 100 for p in parts], color=[p[2] for p in parts], width=0.6)
for i, p in enumerate(parts):
    ax.text(i, p[1] * 100 + 0.12, f"{p[1]*100:.2f}%", ha="center", color=C["ink2"], fontsize=10)
ax.set_xticks(xs); ax.set_xticklabels([p[0] for p in parts])
ax.set_ylabel("Annualised contribution (%)")
ax.set_title("More than half the strategy's return is interest on cash it isn't investing")
fig.tight_layout(); fig.savefig(OUT / "rsi_c2_decomposition.png"); plt.close(fig)

# 3. Before and after publication ---------------------------------------------
io = S["in_out_sample"]
fig, axes = plt.subplots(1, 3, figsize=(11, 3.5), dpi=160)
labels = ["1987–2008\n(before the book)", "2009–2026\n(after)"]
for ax, key, ttl, mult in zip(axes, ["cagr", "sharpe", "max_drawdown"],
                              ["CAGR (%)", "Sharpe", "Max drawdown (%)"], [100, 1, 100]):
    g = np.array([io["in_sample"][key], io["out_of_sample"][key]]) * mult
    b = np.array([io["benchmark_in_sample"][key], io["benchmark_out_of_sample"][key]]) * mult
    x = np.arange(2); w = 0.36
    ax.bar(x - w / 2, g, w, color=C["blue"], label="RSI(2)")
    ax.bar(x + w / 2, b, w, color=C["orange"], label="S&P 500")
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_title(ttl)
    for i, v in enumerate(g):
        ax.text(i - w / 2, v, f"{v:.2f}" if mult == 1 else f"{v:.1f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8.5, color=C["ink2"])
    for i, v in enumerate(b):
        ax.text(i + w / 2, v, f"{v:.2f}" if mult == 1 else f"{v:.1f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8.5, color=C["ink2"])
axes[0].legend(loc="upper right")
fig.suptitle("Connors and Alvarez published the rule in 2008", fontweight="semibold")
fig.tight_layout(); fig.savefig(OUT / "rsi_c3_inout.png"); plt.close(fig)

# 4. The cost cliff ------------------------------------------------------------
cs = pd.DataFrame(S["cost_sensitivity"])
fig, ax = plt.subplots(figsize=(10, 4.2), dpi=160)
colors = [C["aqua"] if v > 0 else C["red"] for v in cs["cagr"]]
ax.bar(cs["cost_bps"].astype(str), cs["cagr"] * 100, color=colors, width=0.6)
ax.axhline(0, color=C["ink2"], lw=0.9)
ax.axhline(S["benchmark"]["cagr"] * 100, color=C["orange"], ls="--", lw=1.2)
ax.text(0.02, S["benchmark"]["cagr"] * 100 + 0.4, "S&P 500 buy & hold", color=C["orange"],
        transform=ax.get_yaxis_transform(), fontsize=9)
for i, v in enumerate(cs["cagr"] * 100):
    ax.text(i, v + (0.35 if v >= 0 else -0.35), f"{v:.2f}%", ha="center",
            va="bottom" if v >= 0 else "top", fontsize=9.5, color=C["ink2"])
ax.set_xlabel("Round-trip cost (basis points)"); ax.set_ylabel("CAGR (%)")
ax.set_title(f"At {S['main']['annual_turnover']*100:.0f}% annual turnover, the broker decides the outcome")
fig.tight_layout(); fig.savefig(OUT / "rsi_c4_costs.png"); plt.close(fig)

# 5. The Sharpe trap: high ratios bought with almost no exposure ---------------
g = pd.DataFrame(S["grid"])
fig, ax = plt.subplots(figsize=(10, 4.6), dpi=160)
sc = ax.scatter(g["time_in_market"] * 100, g["sharpe"], s=90,
                c=g["rsi_period"], cmap="viridis", edgecolor="white", linewidth=0.8, zorder=3)
pub = g[(g["rsi_period"] == 2) & (g["entry"] == 5)].iloc[0]
ax.annotate("the published rule\nRSI(2) < 5", xy=(pub["time_in_market"] * 100, pub["sharpe"]),
            xytext=(14, 1.9), arrowprops=dict(arrowstyle="->", color=C["ink2"]), color=C["ink2"], fontsize=9.5)
worst = g.loc[g["sharpe"].idxmax()]
ax.annotate(f"Sharpe {worst['sharpe']:.1f} — invested {worst['time_in_market']*100:.2f}% of days\n"
            f"(that is {int(round(worst['time_in_market']*S['exposure']['total_days']))} days in 40 years)",
            xy=(worst["time_in_market"] * 100, worst["sharpe"]),
            xytext=(6, 5.2), arrowprops=dict(arrowstyle="->", color=C["red"]), color=C["red"], fontsize=9.5)
ax.set_xlabel("Time invested (% of trading days)"); ax.set_ylabel("Sharpe ratio")
ax.set_title("Every high Sharpe in the parameter grid is bought by barely trading")
plt.colorbar(sc, ax=ax, label="RSI period")
fig.tight_layout(); fig.savefig(OUT / "rsi_c5_sharpe_trap.png"); plt.close(fig)

# 6. The regime thesis, tested -------------------------------------------------
reg = pd.DataFrame(S["regimes"])
fig, ax = plt.subplots(figsize=(11, 4.6), dpi=160)
x = np.arange(len(reg)); w = 0.27
ax.bar(x - w, reg["rsi2"] * 100, w, color=C["blue"], label="RSI(2)")
ax.bar(x, reg["sma_filter"] * 100, w, color=C["aqua"], label="10-month SMA filter")
ax.bar(x + w, reg["sp500"] * 100, w, color=C["orange"], label="S&P 500")
ax.axhline(0, color=C["ink2"], lw=0.9)
ax.set_xticks(x)
ax.set_xticklabels([r.replace(" (chop)", "\n(chop)").replace(" ", "\n", 1) for r in reg["regime"]],
                   fontsize=8.5)
ax.set_ylabel("Total return through the episode (%)")
ax.set_title("The thesis was that mean reversion thrives where trend following bleeds. It doesn't.")
ax.legend(loc="upper right", ncol=3)
fig.tight_layout(); fig.savefig(OUT / "rsi_c6_regimes.png"); plt.close(fig)

print("charts written to", OUT)
