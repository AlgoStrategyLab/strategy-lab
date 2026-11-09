"""Charts for article #2. Palette matches the Strategy Lab house style."""
import json
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np, pandas as pd

OUT = Path(__file__).parent / "output"
C = {"blue":"#2a78d6","orange":"#eb6834","aqua":"#1baf7a","yellow":"#eda100","violet":"#6250d6",
     "red":"#e34948","ink":"#0b0b0b","ink2":"#52514e","grid":"#e6e5e2","surface":"#fcfcfb"}
plt.rcParams.update({
    "figure.facecolor":C["surface"],"axes.facecolor":C["surface"],"axes.edgecolor":C["grid"],
    "axes.grid":True,"grid.color":C["grid"],"grid.linewidth":0.8,"axes.spines.top":False,
    "axes.spines.right":False,"axes.titlesize":13,"axes.titlecolor":C["ink"],
    "axes.labelcolor":C["ink2"],"xtick.color":C["ink2"],"ytick.color":C["ink2"],"font.size":10.5,
    "font.family":"DejaVu Sans","legend.frameon":False,"legend.fontsize":10})

s = pd.read_csv(OUT/"sma_trend_filter_series.csv", index_col=0, parse_dates=True)
sig = pd.read_csv(OUT/"signals.csv", index_col=0, parse_dates=True)
summ = json.load(open(OUT/"sma_trend_filter_summary.json"))

# 1 — growth of $1
fig, ax = plt.subplots(figsize=(11,5.2), dpi=160)
for col, colr, lab, lw in [("SP500",C["orange"],"S&P 500 buy & hold",1.8),
                           ("SMA",C["blue"],"10-month SMA filter",2.2),
                           ("Momentum",C["aqua"],"12-month absolute momentum",2.0),
                           ("SixtyForty",C["violet"],"60/40",1.3)]:
    ax.plot(s.index, s[col], color=colr, lw=lw, label=lab)
ax.set_yscale("log"); ax.set_yticks([1,2,5,10,20,50]); ax.set_yticklabels(["$1","$2","$5","$10","$20","$50"])
for col,colr in [("SMA",C["blue"]),("SP500",C["orange"]),("Momentum",C["aqua"]),("SixtyForty",C["violet"])]:
    ax.text(s.index[-1], s[col].iloc[-1], f"  ${s[col].iloc[-1]:.0f}", color=colr, va="center", fontweight="bold", fontsize=10)
ax.set_title("Growth of $1, Jan 1987 – Oct 2026 (log scale)", fontweight="bold")
ax.legend(loc="upper left"); ax.set_xlim(s.index[0], s.index[-1]+pd.Timedelta(days=900))
ax.xaxis.set_major_locator(mdates.YearLocator(4))
fig.tight_layout(); fig.savefig(OUT/"c1_equity.png"); plt.close(fig)

# 2 — THE signal chart: two filter states over time + disagreement
fig, (ax0, ax1) = plt.subplots(2,1, figsize=(11,5.4), dpi=160, sharex=True,
                               gridspec_kw={"height_ratios":[1.05,1.6]})
idx = sig.index
def band(ax, series, y, label, colr):
    runs=[]; start=idx[0]; cur=bool(series.iloc[0])
    for d,v in series.items():
        if bool(v)!=cur: runs.append((start,d,cur)); start=d; cur=bool(v)
    runs.append((start, idx[-1], cur))
    for a,b,on in runs:
        ax.axvspan(a,b, ymin=y, ymax=y+0.38, color=colr if on else "#d9d8d4", lw=0)
    ax.text(idx[0]-pd.Timedelta(days=430), (y+0.19), label, ha="right", va="center",
            fontsize=10, color=C["ink"], fontweight="bold")
ax0.set_ylim(0,1); ax0.axis("off")
band(ax0, sig["sma_on"], 0.55, "10-mo SMA", C["blue"])
band(ax0, sig["mom_on"], 0.08, "12-mo momentum", C["aqua"])
dis = sig["sma_on"] != sig["mom_on"]
for d, v in dis.items():
    if v: ax0.axvspan(d, d+pd.Timedelta(days=31), ymin=0.0, ymax=1.0, color=C["red"], alpha=0.16, lw=0)
ax0.set_title("When each filter was risk-on (colour) vs risk-off (grey) — red = they disagreed", fontweight="bold")
ax1.fill_between(s.index, s["SP500_dd"]*100, 0, color=C["orange"], alpha=0.30, lw=0, label="S&P 500")
ax1.plot(s.index, s["SMA_dd"]*100, color=C["blue"], lw=1.3, label="10-month SMA filter")
ax1.plot(s.index, s["Mom_dd"]*100, color=C["aqua"], lw=1.3, label="12-month absolute momentum")
ax1.set_ylabel("Drawdown (%)"); ax1.set_ylim(-60,2); ax1.legend(loc="lower left", ncol=3)
ax1.xaxis.set_major_locator(mdates.YearLocator(4))
fig.tight_layout(); fig.savefig(OUT/"c2_signals.png"); plt.close(fig)

# 3 — lookback sweep
sw = pd.DataFrame(summ["lookback_sweep"])
fig, axes = plt.subplots(1,3, figsize=(11,3.4), dpi=160)
for ax, col, ttl, mult, fmt in zip(axes, ["cagr","sharpe","annual_turnover"],
                                   ["CAGR (%)","Sharpe","Annual turnover (%)"], [100,1,100], ["{:.1f}","{:.2f}","{:.0f}"]):
    vals = sw[col]*mult
    cols = [C["red"] if lb==10 else "#9bbde8" for lb in sw["lookback"]]
    ax.bar(sw["lookback"].astype(str), vals, color=cols)
    ax.set_title(ttl); ax.set_xlabel("Moving-average length (months)")
    for i,v in enumerate(vals):
        ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=8.5, color=C["ink2"])
axes[0].axhline(summ["benchmark"]["cagr"]*100, color=C["orange"], ls="--", lw=1.2)
axes[0].text(-0.45, summ["benchmark"]["cagr"]*100+0.25, "S&P 500 buy & hold", color=C["orange"], ha="left", fontsize=8.5)
axes[0].set_ylim(0, summ["benchmark"]["cagr"]*100+2.0)
axes[1].axhline(summ["momentum"]["sharpe"], color=C["aqua"], ls="--", lw=1.2)
axes[1].text(-0.45, summ["momentum"]["sharpe"]+0.025, "12-mo absolute momentum", color=C["aqua"], ha="left", fontsize=8.5)
axes[1].set_ylim(0, summ["momentum"]["sharpe"]+0.16)
fig.suptitle("Longer is better: every setting above 10 months beat it, and traded less", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"c3_lookback.png"); plt.close(fig)

# 4 — band sweep: turnover vs return
bd = pd.DataFrame(summ["band_sweep"])
fig, ax = plt.subplots(figsize=(11,3.8), dpi=160)
ax.plot(bd["annual_turnover"]*100, bd["cagr"]*100, "-o", color=C["blue"], lw=2, ms=9)
for _, r in bd.iterrows():
    ax.annotate(f"{r['band']*100:.0f}% band", (r["annual_turnover"]*100, r["cagr"]*100),
                textcoords="offset points", xytext=(0,11), ha="center", fontsize=9, color=C["ink2"])
ax.axhline(summ["momentum"]["cagr"]*100, color=C["aqua"], ls="--", lw=1.3)
ax.text(330, summ["momentum"]["cagr"]*100+0.06, "12-month absolute momentum", color=C["aqua"], fontsize=9)
ax.axhline(summ["benchmark"]["cagr"]*100, color=C["orange"], ls="--", lw=1.3)
ax.text(330, summ["benchmark"]["cagr"]*100+0.06, "S&P 500 buy & hold", color=C["orange"], fontsize=9)
ax.set_xlabel("Annual turnover (%)"); ax.set_ylabel("CAGR (%)")
ax.set_title("Adding a buffer around the average cuts trading and lifts returns — up to a point", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"c4_band.png"); plt.close(fig)

# 5 — in/out of sample
io = summ["in_out_sample"]
fig, axes = plt.subplots(1,3, figsize=(11,3.4), dpi=160)
labs = ["1987–2006\n(pre-publication)","2007–2026\n(post-publication)"]
for ax, col, ttl, mult in zip(axes, ["cagr","sharpe","max_drawdown"], ["CAGR (%)","Sharpe","Max drawdown (%)"], [100,1,100]):
    g=np.array([io["in_sample"][col], io["out_of_sample"][col]])*mult
    b=np.array([io["benchmark_in_sample"][col], io["benchmark_out_of_sample"][col]])*mult
    x=np.arange(2); w=0.36
    ax.bar(x-w/2,g,w,color=C["blue"],label="10-month SMA"); ax.bar(x+w/2,b,w,color=C["orange"],label="S&P 500")
    ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_title(ttl)
    for i,v in enumerate(g): ax.text(i-w/2,v,f"{v:.1f}" if mult==100 else f"{v:.2f}",ha="center",va="bottom" if v>=0 else "top",fontsize=8.5,color=C["ink2"])
    for i,v in enumerate(b): ax.text(i+w/2,v,f"{v:.1f}" if mult==100 else f"{v:.2f}",ha="center",va="bottom" if v>=0 else "top",fontsize=8.5,color=C["ink2"])
axes[0].legend(loc="upper right")
fig.suptitle("Before and after Faber published the rule (2007)", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"c5_inout.png"); plt.close(fig)
print("charts written")
