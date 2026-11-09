"""Charts for Article #1 from output/dual_momentum_*.json/csv. Light-mode palette from the dataviz reference."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "output"
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "violet": "#6250d6",
     "red": "#e34948", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e6e5e2", "surface": "#fcfcfb"}
plt.rcParams.update({
    "figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "axes.edgecolor": C["grid"],
    "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 13, "axes.titlecolor": C["ink"],
    "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "font.size": 10.5,
    "font.family": "DejaVu Sans", "legend.frameon": False, "legend.fontsize": 10,
})

s = pd.read_csv(OUT / "dual_momentum_series.csv", index_col=0, parse_dates=True)
summ = json.load(open(OUT / "dual_momentum_summary.json"))
HOLD_COL = {"VFINX": C["blue"], "VGTSX": C["violet"], "VBMFX": C["yellow"], "CASH": C["ink2"]}
HOLD_LBL = {"VFINX": "US equities", "VGTSX": "Intl equities", "VBMFX": "US bonds", "CASH": "T-bills"}


def shade_holdings(ax, alpha=0.10):
    h = s["holding"]
    start = h.index[0]; cur = h.iloc[0]
    for d, v in h.items():
        if v != cur:
            ax.axvspan(start, d, color=HOLD_COL[cur], alpha=alpha, lw=0)
            start, cur = d, v
    ax.axvspan(start, h.index[-1], color=HOLD_COL[cur], alpha=alpha, lw=0)


# 1. Growth of $1 (log) with holdings shading
fig, ax = plt.subplots(figsize=(11, 5.4), dpi=160)
shade_holdings(ax)
ax.plot(s.index, s["GEM"], color=C["blue"], lw=2.2, label="Dual Momentum (GEM)")
ax.plot(s.index, s["SP500"], color=C["orange"], lw=1.8, label="S&P 500 (VFINX)")
ax.plot(s.index, s["60/40"], color=C["aqua"], lw=1.6, label="60/40")
ax.plot(s.index, s["Intl"], color=C["violet"], lw=1.2, label="Intl equities (VGTSX)", alpha=0.9)
ax.set_yscale("log")
ax.set_yticks([0.5, 1, 2, 4, 8, 16]); ax.set_yticklabels(["$0.5", "$1", "$2", "$4", "$8", "$16"])
ax.set_title("Growth of $1, May 1997 – Oct 2026 (log scale) — background = GEM's holding")
for k, v in s[["GEM", "SP500", "60/40", "Intl"]].iloc[-1].items():
    pass
ax.text(s.index[-1], s["GEM"].iloc[-1], f"  ${s['GEM'].iloc[-1]:.1f}", color=C["blue"], va="center", fontweight="semibold")
ax.text(s.index[-1], s["SP500"].iloc[-1], f"  ${s['SP500'].iloc[-1]:.1f}", color=C["orange"], va="center", fontweight="semibold")
ax.text(s.index[-1], s["60/40"].iloc[-1] * 0.93, f"  ${s['60/40'].iloc[-1]:.1f}", color=C["aqua"], va="center", fontweight="semibold")
ax.text(s.index[-1], s["Intl"].iloc[-1], f"  ${s['Intl'].iloc[-1]:.1f}", color=C["violet"], va="center", fontweight="semibold")
from matplotlib.patches import Patch
h1, l1 = ax.get_legend_handles_labels()
h2 = [Patch(color=HOLD_COL[k], alpha=0.25, label=f"holding: {HOLD_LBL[k]}") for k in ["VFINX", "VGTSX", "VBMFX"]]
ax.legend(h1 + h2, l1 + [p.get_label() for p in h2], loc="upper left", ncol=2)
ax.set_xlim(s.index[0], s.index[-1] + pd.Timedelta(days=700))
ax.xaxis.set_major_locator(mdates.YearLocator(3))
fig.tight_layout(); fig.savefig(OUT / "chart1_equity.png"); plt.close(fig)

# 2. Drawdowns
fig, ax = plt.subplots(figsize=(11, 3.8), dpi=160)
ax.fill_between(s.index, s["SP500_dd"] * 100, 0, color=C["orange"], alpha=0.35, lw=0, label="S&P 500")
ax.fill_between(s.index, s["GEM_dd"] * 100, 0, color=C["blue"], alpha=0.55, lw=0, label="Dual Momentum (GEM)")
ax.set_ylim(-60, 2); ax.set_ylabel("Drawdown from peak (%)")
ax.set_title("Drawdowns: GEM sidestepped 2000–02 and 2008, but not the 2020 crash")
ax.annotate("2008: -55% vs -12%", xy=(pd.Timestamp("2009-03-09"), -55), xytext=(pd.Timestamp("2004-06-01"), -48),
            arrowprops=dict(arrowstyle="-", color=C["ink2"]), color=C["ink2"])
ax.annotate("COVID: both -34%\n(too fast for a 12-month filter)", xy=(pd.Timestamp("2020-03-23"), -34),
            xytext=(pd.Timestamp("2013-06-01"), -40), arrowprops=dict(arrowstyle="-", color=C["ink2"]), color=C["ink2"])
ax.legend(loc="lower left"); ax.xaxis.set_major_locator(mdates.YearLocator(3))
fig.tight_layout(); fig.savefig(OUT / "chart2_drawdown.png"); plt.close(fig)

# 3. Yearly returns grouped bars
y = pd.DataFrame(summ["yearly"]).set_index("year")
y = y[y.index >= 1998]
fig, ax = plt.subplots(figsize=(11, 4.4), dpi=160)
x = np.arange(len(y)); w = 0.4
ax.bar(x - w / 2, y["strategy"] * 100, w, color=C["blue"], label="Dual Momentum (GEM)")
ax.bar(x + w / 2, y["benchmark"] * 100, w, color=C["orange"], label="S&P 500")
ax.axhline(0, color=C["ink2"], lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([str(i) if i % 2 == 0 else "" for i in y.index])
ax.set_ylabel("Calendar-year return (%)"); ax.set_title("Calendar-year returns (2026 year-to-date)")
ax.legend(loc="lower left", ncol=2)
fig.tight_layout(); fig.savefig(OUT / "chart3_yearly.png"); plt.close(fig)

# 4. Lookback sensitivity
sw = pd.DataFrame(summ["lookback_sweep"])
fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), dpi=160)
for ax, col, ttl, fmt in zip(axes, ["cagr", "sharpe", "max_drawdown"], ["CAGR (%)", "Sharpe", "Max drawdown (%)"], [100, 1, 100]):
    vals = sw[col] * fmt
    cols = [C["blue"] if lb == 12 else "#9bbde8" for lb in sw["lookback"]]
    ax.bar(sw["lookback"].astype(str), vals, color=cols)
    ax.set_title(ttl); ax.set_xlabel("Lookback (months)")
    for i, v in enumerate(vals):
        ax.text(i, v + (0.2 if v >= 0 else -0.2), f"{v:.1f}" if fmt == 100 else f"{v:.2f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8.5, color=C["ink2"])
axes[0].axhline(summ["benchmark"]["cagr"] * 100, color=C["orange"], ls="--", lw=1.2)
axes[0].text(6.4, summ["benchmark"]["cagr"] * 100 + 0.2, "S&P 500", color=C["orange"], ha="right", fontsize=9)
axes[2].axhline(summ["benchmark"]["max_drawdown"] * 100, color=C["orange"], ls="--", lw=1.2)
axes[2].text(6.4, summ["benchmark"]["max_drawdown"] * 100 + 1, "S&P 500", color=C["orange"], ha="right", fontsize=9)
fig.suptitle("Lookback sensitivity, 1997–2026, 10 bps costs (12 months = the published rule)", fontweight="semibold")
fig.tight_layout(); fig.savefig(OUT / "chart4_lookback.png"); plt.close(fig)

# 5. Rolling 3-year CAGR difference GEM - S&P
r = s[["GEM", "SP500"]]
roll = (r / r.shift(756)) ** (252 / 756) - 1
diff = (roll["GEM"] - roll["SP500"]).dropna() * 100
fig, ax = plt.subplots(figsize=(11, 3.6), dpi=160)
ax.fill_between(diff.index, diff, 0, where=diff >= 0, color=C["blue"], alpha=0.6, lw=0, label="GEM ahead")
ax.fill_between(diff.index, diff, 0, where=diff < 0, color=C["orange"], alpha=0.6, lw=0, label="S&P 500 ahead")
ax.axhline(0, color=C["ink2"], lw=0.8); ax.set_ylabel("Rolling 3-yr CAGR gap (pp)")
ax.set_title("Rolling 3-year CAGR: GEM minus S&P 500 — the edge shows up in bear markets, then gives back")
ax.legend(loc="upper right", ncol=2); ax.xaxis.set_major_locator(mdates.YearLocator(3))
fig.tight_layout(); fig.savefig(OUT / "chart5_rolling.png"); plt.close(fig)

# 6. In-sample vs out-of-sample
io = summ["in_out_sample"]
fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), dpi=160)
labels = ["1997–2013\n(pre-publication)", "2014–2026\n(post-publication)"]
for ax, col, ttl, fmt in zip(axes, ["cagr", "sharpe", "max_drawdown"], ["CAGR (%)", "Sharpe", "Max drawdown (%)"], [100, 1, 100]):
    g = np.array([io["in_sample"][col], io["out_of_sample"][col]]) * fmt
    b = np.array([io["benchmark_in_sample"][col], io["benchmark_out_of_sample"][col]]) * fmt
    x = np.arange(2); w = 0.36
    ax.bar(x - w / 2, g, w, color=C["blue"], label="GEM"); ax.bar(x + w / 2, b, w, color=C["orange"], label="S&P 500")
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_title(ttl)
    for i, v in enumerate(g): ax.text(i - w / 2, v, f"{v:.1f}" if fmt == 100 else f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, color=C["ink2"])
    for i, v in enumerate(b): ax.text(i + w / 2, v, f"{v:.1f}" if fmt == 100 else f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, color=C["ink2"])
axes[0].legend(loc="upper right")
fig.suptitle("Before vs after the strategy was published (2014)", fontweight="semibold")
fig.tight_layout(); fig.savefig(OUT / "chart6_inout.png"); plt.close(fig)
print("charts written")

# 7. Monthly returns heatmap
main = json.load(open(OUT / "dual_momentum_main.json"))
mr = pd.DataFrame(main["monthly_returns"]).T
mr.index = mr.index.astype(int)
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
grid = mr[months].astype(float) * 100
yr = mr["Year"].astype(float) * 100
fig, ax = plt.subplots(figsize=(11, 9.5), dpi=160)
from matplotlib.colors import TwoSlopeNorm
norm = TwoSlopeNorm(vmin=-12, vcenter=0, vmax=12)
im = ax.imshow(grid.values, cmap="RdBu", norm=norm, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(months)
ax.set_yticks(range(len(grid))); ax.set_yticklabels(grid.index)
ax.grid(False)
for i in range(len(grid)):
    for j in range(12):
        v = grid.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color="white" if abs(v) > 6 else C["ink"])
# year column
for i, (y, v) in enumerate(yr.items()):
    ax.text(12.3, i, f"{v:+.1f}%", ha="left", va="center", fontsize=8.5, fontweight="bold",
            color=C["blue"] if v >= 0 else C["red"])
ax.text(12.3, -0.9, "Year", ha="left", va="center", fontsize=9, color=C["ink2"])
ax.set_xlim(-0.5, 13.5)
ax.set_title("Dual Momentum: monthly returns (%), May 1997 – Oct 2026")
fig.tight_layout(); fig.savefig(OUT / "chart7_monthly_heatmap.png"); plt.close(fig)

# 8. Underwater plot with top-5 drawdowns labelled
dds = main["drawdowns"][:5]
fig, ax = plt.subplots(figsize=(11, 3.6), dpi=160)
ax.fill_between(s.index, s["GEM_dd"] * 100, 0, color=C["blue"], alpha=0.55, lw=0)
for k, d in enumerate(dds, 1):
    t = pd.Timestamp(d["trough"])
    ax.annotate(f"#{k} {d['depth']*100:.0f}%", xy=(t, d["depth"] * 100), xytext=(0, -14), textcoords="offset points",
                ha="center", fontsize=8.5, color=C["ink"])
ax.set_ylim(-42, 2); ax.set_ylabel("Drawdown (%)"); ax.set_title("Underwater plot: the five deepest drawdowns")
ax.xaxis.set_major_locator(mdates.YearLocator(3))
fig.tight_layout(); fig.savefig(OUT / "chart8_underwater.png"); plt.close(fig)
print("extra charts written")
