"""Charts for article #5 from output/pairs_*.json/csv. Shared light-mode palette."""
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

S = json.load(open(OUT / "pairs_summary.json"))
s = pd.read_csv(OUT / "pairs_series.csv", index_col=0, parse_dates=True)
sel = pd.read_csv(OUT / "selection_curves.csv", index_col=0, parse_dates=True)
trades = pd.read_csv(OUT / "trades.csv")

# 1. The flat line -------------------------------------------------------------
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 6.4), dpi=160, sharex=True,
                              gridspec_kw={"height_ratios": [2.2, 1]})
ax.plot(s.index, s["SP500"], color=C["orange"], lw=2.0, label="S&P 500")
ax.plot(s.index, s["Pairs"], color=C["blue"], lw=2.2, label="Pairs trading")
ax.set_yscale("log"); ax.set_yticks([0.5, 1, 2, 4, 8]); ax.set_yticklabels(["$0.5", "$1", "$2", "$4", "$8"])
ax.text(s.index[-1], s["Pairs"].iloc[-1], f"  ${s['Pairs'].iloc[-1]:.2f}", color=C["blue"],
        va="center", fontweight="semibold", fontsize=9.5)
ax.text(s.index[-1], s["SP500"].iloc[-1], f"  ${s['SP500'].iloc[-1]:.1f}", color=C["orange"],
        va="center", fontweight="semibold", fontsize=9.5)
ax.set_title("Growth of $1, January 2000 – November 2026 (log scale)")
ax.legend(loc="upper left")
ax2.fill_between(s.index, s["SP_dd"] * 100, 0, color=C["orange"], alpha=0.30, lw=0, label="S&P 500")
ax2.fill_between(s.index, s["Pairs_dd"] * 100, 0, color=C["blue"], alpha=0.65, lw=0, label="Pairs trading")
ax2.set_ylabel("Drawdown (%)"); ax2.legend(loc="lower left", ncol=2)
ax2.xaxis.set_major_locator(mdates.YearLocator(3))
ax.set_xlim(s.index[0], s.index[-1] + pd.Timedelta(days=900))
fig.tight_layout(); fig.savefig(OUT / "pt_c1_equity.png"); plt.close(fig)

# 2. Gross vs net of costs -----------------------------------------------------
cs = pd.DataFrame(S["cost_sensitivity"])
fig, ax = plt.subplots(figsize=(10, 4.4), dpi=160)
colors = [C["aqua"] if v > 0 else C["red"] for v in cs["cagr"]]
ax.bar(cs["cost_bps"].astype(str), cs["cagr"] * 100, color=colors, width=0.6)
ax.axhline(0, color=C["ink2"], lw=0.9)
for i, v in enumerate(cs["cagr"] * 100):
    ax.text(i, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}%", ha="center",
            va="bottom" if v >= 0 else "top", fontsize=9.5, color=C["ink2"])
ax.set_xlabel("Round-trip cost (basis points)"); ax.set_ylabel("CAGR (%)")
ax.set_title(f"The whole result is the cost line, at {S['main']['annual_turnover']*100:.0f}% annual turnover")
fig.tight_layout(); fig.savefig(OUT / "pt_c2_costs.png"); plt.close(fig)

# 3. Chosen pairs against random pairs ----------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.0), dpi=160)
rcols = [c for c in sel.columns if c.startswith("random")]
for i, c in enumerate(rcols):
    ax.plot(sel.index, sel[c], color=C["ink2"], lw=1.1, alpha=0.5,
            label="Random pairs (5 draws)" if i == 0 else None)
ax.plot(sel.index, sel["chosen"], color=C["blue"], lw=2.4, label="Closest-tracking pairs")
ax.axhline(1.0, color=C["ink2"], lw=1.0, ls="--")
ax.set_ylabel("Growth of $1")
ax.set_title("The chosen pairs are steadier than random ones. They are not more profitable.")
ax.legend(loc="upper left")
ax.xaxis.set_major_locator(mdates.YearLocator(3))
fig.tight_layout(); fig.savefig(OUT / "pt_c3_selection.png"); plt.close(fig)

# 4. It really is market neutral ----------------------------------------------
pr = s["Pairs"].pct_change().dropna()
br = s["SP500"].pct_change().reindex(pr.index).fillna(0)
fig, (axa, axb) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=160)
axa.scatter(br * 100, pr * 100, s=6, color=C["blue"], alpha=0.28, edgecolor="none")
lim = float(np.nanpercentile(np.abs(br * 100), 99.7))
xs = np.linspace(-lim, lim, 10)
axa.plot(xs, xs, color=C["orange"], lw=1.6, ls="--", label="beta = 1 (the index itself)")
beta = S["main"]["beta"]
axa.plot(xs, beta * xs, color=C["aqua"], lw=2.0, label=f"fitted beta = {beta:.3f}")
axa.set_xlim(-lim, lim); axa.set_ylim(-lim / 2, lim / 2)
axa.set_xlabel("S&P 500 daily return (%)"); axa.set_ylabel("Pairs daily return (%)")
axa.set_title("Daily returns against the index"); axa.legend(loc="upper left", fontsize=9)

roll = pr.rolling(252).cov(br) / br.rolling(252).var()
axb.axhline(0, color=C["ink2"], lw=0.9)
axb.axhline(1, color=C["orange"], lw=1.2, ls="--")
axb.text(roll.index[5], 1.02, "the index", color=C["orange"], fontsize=9, va="bottom")
axb.plot(roll.index, roll, color=C["aqua"], lw=1.6)
axb.set_ylim(-0.5, 1.2); axb.set_ylabel("Rolling 1-year beta")
axb.set_title("Beta never leaves zero")
axb.xaxis.set_major_locator(mdates.YearLocator(5))
fig.tight_layout(); fig.savefig(OUT / "pt_c4_neutrality.png"); plt.close(fig)

# 5. Does the premise hold? ----------------------------------------------------
fig, (axa, axb) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=160)
conv = trades["reason"].value_counts()
labels = {"converged": "Converged\n(the premise)", "period end": "Never converged\n(closed at window end)",
          "stop": "Stopped out"}
order = [k for k in ["converged", "period end", "stop"] if k in conv.index]
cols = {"converged": C["aqua"], "period end": C["red"], "stop": C["yellow"]}
axa.bar([labels[k] for k in order], [conv[k] for k in order], color=[cols[k] for k in order], width=0.55)
for i, k in enumerate(order):
    axa.text(i, conv[k] + 4, f"{conv[k]}  ({conv[k]/len(trades)*100:.0f}%)",
             ha="center", fontsize=10, color=C["ink2"])
axa.set_ylabel("Positions"); axa.set_title(f"Only {S['trades']['convergence_rate']*100:.0f}% of positions ever converged")
axa.set_ylim(0, conv.max() * 1.22)

axb.hist(trades["days"], bins=26, color=C["blue"], alpha=0.85)
axb.axvline(trades["days"].median(), color=C["orange"], lw=1.8)
axb.text(trades["days"].median() + 4, axb.get_ylim()[1] * 0.9,
         f"median {trades['days'].median():.0f} days", color=C["orange"], fontsize=9.5)
axb.set_xlabel("Calendar days held"); axb.set_ylabel("Positions")
axb.set_title("How long a position lasts")
fig.tight_layout(); fig.savefig(OUT / "pt_c5_convergence.png"); plt.close(fig)

# 6. Uncorrelated, through everything -----------------------------------------
ep = pd.DataFrame(S["episodes"])
fig, ax = plt.subplots(figsize=(11, 4.6), dpi=160)
x = np.arange(len(ep)); w = 0.38
ax.bar(x - w / 2, ep["pairs"] * 100, w, color=C["blue"], label="Pairs trading")
ax.bar(x + w / 2, ep["sp500"] * 100, w, color=C["orange"], label="S&P 500")
ax.axhline(0, color=C["ink2"], lw=0.9)
ax.set_xticks(x); ax.set_xticklabels([e.replace(" (", "\n(") for e in ep["episode"]], fontsize=8.5)
ax.set_ylabel("Total return through the episode (%)")
ax.set_title("It is genuinely uncorrelated. It is also genuinely flat.")
ax.legend(loc="upper left", ncol=2)
fig.tight_layout(); fig.savefig(OUT / "pt_c6_episodes.png"); plt.close(fig)

print("charts written to", OUT)
