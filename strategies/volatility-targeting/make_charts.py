"""Charts for article #6 from output/voltarget_*.json/csv. Shared light-mode palette."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "output"
DEST = Path(__file__).parent.parent.parent / "sitebuild" / "assets" / "charts"
DEST.mkdir(parents=True, exist_ok=True)
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

S = json.load(open(OUT / "voltarget_summary.json"))
s = pd.read_csv(OUT / "voltarget_series.csv", index_col=0, parse_dates=True)
sc = pd.read_csv(OUT / "scales.csv", index_col=0, parse_dates=True)
shuf = pd.read_csv(OUT / "shuffled_curves.csv", index_col=0, parse_dates=True)

BEARS = [("2000-03-24", "2002-10-09"), ("2007-10-10", "2009-03-09"),
         ("2020-02-20", "2020-03-23"), ("2022-01-04", "2022-10-12")]


def save(fig, name):
    fig.savefig(DEST / f"{name}.png", bbox_inches="tight", facecolor=C["surface"])
    plt.close(fig)
    print("wrote", name)


# 1. What the layer actually does ---------------------------------------------
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 6.6), dpi=160, sharex=True,
                              gridspec_kw={"height_ratios": [2.2, 1]})
ax.plot(s.index, s["Base"], color=C["orange"], lw=2.0, label="S&P 500 buy & hold")
ax.plot(s.index, s["VT"], color=C["blue"], lw=2.2, label="Volatility targeted (10%)")
ax.set_yscale("log"); ax.set_yticks([1, 5, 20, 80, 320])
ax.set_yticklabels(["$1", "$5", "$20", "$80", "$320"])
for a, b in BEARS:
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=C["ink"], alpha=0.05, lw=0)
for col, colr in (("Base", C["orange"]), ("VT", C["blue"])):
    ax.text(s.index[-1], s[col].iloc[-1], f"  ${s[col].iloc[-1]:,.0f}", color=colr,
            va="center", fontweight="semibold", fontsize=9.5)
ax.set_title("Growth of $1, November 1981 – November 2026 (log scale). Shaded: bear markets.")
ax.legend(loc="upper left")
ax2.fill_between(s.index, s["Base_dd"] * 100, 0, color=C["orange"], alpha=0.30, lw=0,
                 label="Buy & hold")
ax2.fill_between(s.index, s["VT_dd"] * 100, 0, color=C["blue"], alpha=0.60, lw=0,
                 label="Volatility targeted")
ax2.set_ylabel("Drawdown (%)"); ax2.legend(loc="lower left")
ax2.set_title("Less money, and less than half the worst loss", fontsize=11)
save(fig, "vt_c1_equity")

# 2. The dial itself -----------------------------------------------------------
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 6.2), dpi=160, sharex=True,
                              gridspec_kw={"height_ratios": [1, 1]})
ax.plot(sc.index, sc["realised_vol"] * 100, color=C["ink2"], lw=1.0)
ax.axhline(10, color=C["blue"], lw=1.6, ls="--")
ax.text(sc.index[int(len(sc) * 0.015)], 15.5, "10% target", color=C["blue"], fontsize=9.5,
        fontweight="semibold", bbox=dict(fc=C["surface"], ec="none", pad=1.5))
ax.set_ylabel("Realised vol (%)"); ax.set_ylim(0, 65)
ax.set_title("Trailing 60-day volatility of the position, and the exposure it implies")
for a, b in BEARS:
    for axx in (ax, ax2):
        axx.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=C["ink"], alpha=0.05, lw=0)
ax2.fill_between(sc.index, sc["scale"] * 100, 0, color=C["blue"], alpha=0.45, lw=0)
ax2.plot(sc.index, sc["scale"] * 100, color=C["blue"], lw=1.0)
ax2.axhline(S["scale_stats"]["mean"] * 100, color=C["orange"], lw=1.4, ls="--")
ax2.text(sc.index[int(len(sc) * 0.015)], S["scale_stats"]["mean"] * 100 + 11,
         f"average {S['scale_stats']['mean']:.0%} invested", color=C["orange"], fontsize=9.5,
         fontweight="semibold", bbox=dict(fc=C["surface"], ec="none", pad=1.5))
ax2.set_ylabel("Exposure (%)"); ax2.set_ylim(0, 108)
save(fig, "vt_c2_scale")

# 3. The control that matters --------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=160)
for c in [c for c in shuf.columns if c.startswith("Shuffled")]:
    ax.plot(shuf.index, shuf[c], color=C["ink2"], lw=1.0, alpha=0.45)
ax.plot([], [], color=C["ink2"], lw=1.0, alpha=0.6, label="Same sizes, shuffled dates (5 draws)")
ax.plot(shuf.index, shuf["Base"], color=C["orange"], lw=2.0, label="No targeting at all")
ax.plot(shuf.index, shuf["Timed"], color=C["blue"], lw=2.4, label="Volatility targeted")
ax.set_yscale("log"); ax.set_yticks([1, 5, 20, 80, 320])
ax.set_yticklabels(["$1", "$5", "$20", "$80", "$320"])
ax.set_title("The same position sizes on the wrong dates: the advantage disappears")
ax.legend(loc="upper left")
sm = S["shuffled_mean"]
ax.text(0.985, 0.10, f"Sharpe       targeted {S['main']['sharpe']:.2f}   ·   "
        f"shuffled {sm['sharpe']:.2f}   ·   untouched {S['base']['sharpe']:.2f}",
        transform=ax.transAxes, ha="right", fontsize=10, color=C["ink"], fontweight="semibold")
ax.text(0.985, 0.045, f"Worst loss   targeted {S['main']['max_drawdown']:.0%}   ·   "
        f"shuffled {sm['max_drawdown']:.0%}   ·   untouched {S['base']['max_drawdown']:.0%}",
        transform=ax.transAxes, ha="right", fontsize=10, color=C["ink"], fontweight="semibold")
save(fig, "vt_c3_shuffled")

# 4. Every strategy in the series ---------------------------------------------
lay = pd.DataFrame(S["layer"])
names = list(dict.fromkeys(lay["name"]))
fig, ax = plt.subplots(figsize=(11, 4.6), dpi=160)
y = np.arange(len(names))[::-1]
for i, nm in enumerate(names):
    b = lay[(lay["name"] == nm) & (lay["variant"] == "base")].iloc[0]
    v = lay[(lay["name"] == nm) & (lay["variant"] == "vol target")].iloc[0]
    ax.plot([b["sharpe"], v["sharpe"]], [y[i], y[i]], color=C["grid"], lw=6, solid_capstyle="round",
            zorder=1)
    ax.scatter([b["sharpe"]], [y[i]], s=90, color=C["orange"], zorder=3)
    ax.scatter([v["sharpe"]], [y[i]], s=90, color=C["blue"], zorder=3)
    ax.text(v["sharpe"] + 0.012, y[i], f"+{v['sharpe'] - b['sharpe']:.3f}", va="center",
            fontsize=9.5, color=C["blue"], fontweight="semibold")
ax.set_yticks(y); ax.set_yticklabels(names)
ax.set_xlabel("Sharpe ratio"); ax.set_xlim(0.38, 0.88)
ax.scatter([], [], s=90, color=C["orange"], label="Strategy as published")
ax.scatter([], [], s=90, color=C["blue"], label="With the volatility layer")
ax.legend(loc="lower right")
ax.set_title("The same small improvement, on every rule in the series")
ax.grid(axis="y", visible=False)
save(fig, "vt_c4_layer")

# 5. Why it works --------------------------------------------------------------
vp = S["vol_persistence"]
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=160)
base_r = s["Base"].pct_change().fillna(0.0)
vol = (base_r.rolling(60).std() * np.sqrt(252)).dropna()
nxt_vol = vol.shift(-60).dropna()
nxt_ret = (base_r.rolling(60).mean() * 252).shift(-60)
j = pd.concat([vol.rename("v"), nxt_vol.rename("nv"), nxt_ret.rename("nr")], axis=1).dropna()
j = j.iloc[::5]
ax.scatter(j["v"] * 100, j["nv"] * 100, s=5, color=C["blue"], alpha=0.22, lw=0)
ax.set_xlabel("Volatility, last 60 days (%)"); ax.set_ylabel("Volatility, next 60 days (%)")
ax.set_title(f"Volatility predicts volatility   r = {vp['corr_next_60d']:.2f}", fontsize=12)
lim = [0, 70]; ax.plot(lim, lim, color=C["ink2"], lw=1.0, ls="--"); ax.set_xlim(lim); ax.set_ylim(lim)
ax2.scatter(j["v"] * 100, j["nr"] * 100, s=5, color=C["orange"], alpha=0.22, lw=0)
ax2.axhline(0, color=C["ink2"], lw=1.0, ls="--")
ax2.set_xlabel("Volatility, last 60 days (%)"); ax2.set_ylabel("Return, next 60 days (% ann.)")
ax2.set_title(f"It does not predict return   r = {vp['corr_return_next_60d']:.2f}", fontsize=12)
ax2.set_xlim(lim)
fig.suptitle("The whole mechanism, in two scatters", fontsize=13, fontweight="semibold", y=1.02)
save(fig, "vt_c5_persistence")

# 6. What leverage buys, and what it breaks ------------------------------------
cap = pd.DataFrame(S["cap_sweep"])
lev = pd.DataFrame(S["levered"]).set_index("name")
basel = lay[lay["variant"] == "base"].set_index("name")
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=160)
ax.plot(cap["max_scale"], cap["sharpe"], color=C["blue"], lw=2.2, marker="o", ms=6)
ax.set_xlabel("Leverage cap (× the base position)"); ax.set_ylabel("Sharpe ratio")
ax.set_title("On buy & hold, each extra turn of leverage costs", fontsize=12)
ax.axhline(S["base"]["sharpe"], color=C["orange"], lw=1.4, ls="--")
ax.text(2.05, S["base"]["sharpe"] + 0.004, "untouched", color=C["orange"], fontsize=9.5,
        ha="right", fontweight="semibold")
xs = np.arange(len(names))
d_nolev = [lay[(lay["name"] == n) & (lay["variant"] == "vol target")].iloc[0]["sharpe"]
           - basel.loc[n, "sharpe"] for n in names]
d_lev = [lev.loc[n, "d_sharpe_vs_base"] for n in names]
ax2.bar(xs - 0.19, d_nolev, 0.36, color=C["blue"], label="De-risk only (1.0× cap)")
ax2.bar(xs + 0.19, d_lev, 0.36, color=C["violet"], label="Leverage allowed (2.0× cap)")
ax2.axhline(0, color=C["ink2"], lw=1.0)
ax2.set_xticks(xs)
ax2.set_xticklabels([n.replace(" buy & hold", "").replace(" filter", "").replace(" 20/10", "")
                     for n in names], rotation=18, ha="right", fontsize=9)
ax2.set_ylabel("Change in Sharpe")
ax2.set_title("And on RSI(2) it levers the cash", fontsize=12)
ax2.legend(loc="lower left")
save(fig, "vt_c6_leverage")

# 7. Episodes ------------------------------------------------------------------
ep = pd.DataFrame(S["episodes"])
fig, ax = plt.subplots(figsize=(11, 4.8), dpi=160)
y = np.arange(len(ep))[::-1]
ax.barh(y + 0.19, ep["base"] * 100, 0.36, color=C["orange"], label="S&P 500 buy & hold")
ax.barh(y - 0.19, ep["vt"] * 100, 0.36, color=C["blue"], label="Volatility targeted")
for i, r in ep.iterrows():
    ax.text(-2 if r["base"] < 0 else 2, y[i] + 0.19, f"{r['base']:+.0%}",
            va="center", ha="right" if r["base"] < 0 else "left", fontsize=9, color=C["ink2"])
    ax.text(-2 if r["vt"] < 0 else 2, y[i] - 0.19, f"{r['vt']:+.0%}  ({r['avg_scale']:.0%} held)",
            va="center", ha="right" if r["vt"] < 0 else "left", fontsize=9, color=C["ink2"])
ax.set_yticks(y); ax.set_yticklabels(ep["name"])
ax.axvline(0, color=C["ink2"], lw=1.0)
ax.set_xlabel("Total return through the episode (%)"); ax.set_xlim(-70, 560)
ax.set_title("Smaller losses, and smaller gains, in every episode since 2000")
ax.legend(loc="lower right"); ax.grid(axis="y", visible=False)
save(fig, "vt_c7_episodes")
