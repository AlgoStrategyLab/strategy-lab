import json
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np, pandas as pd

OUT = Path(__file__).parent / "output"
C = {"blue":"#2a78d6","orange":"#eb6834","aqua":"#1baf7a","yellow":"#eda100","violet":"#6250d6",
     "red":"#e34948","ink":"#0b0b0b","ink2":"#52514e","grid":"#e6e5e2","surface":"#fcfcfb"}
plt.rcParams.update({"figure.facecolor":C["surface"],"axes.facecolor":C["surface"],"axes.edgecolor":C["grid"],
    "axes.grid":True,"grid.color":C["grid"],"grid.linewidth":0.8,"axes.spines.top":False,
    "axes.spines.right":False,"axes.titlesize":13,"axes.titlecolor":C["ink"],"axes.labelcolor":C["ink2"],
    "xtick.color":C["ink2"],"ytick.color":C["ink2"],"font.size":10.5,"font.family":"DejaVu Sans",
    "legend.frameon":False,"legend.fontsize":10})
s = pd.read_csv(OUT/"donchian_series.csv", index_col=0, parse_dates=True)
S = json.load(open(OUT/"donchian_summary.json"))

# 1 — growth of $1
fig, ax = plt.subplots(figsize=(11,5.2), dpi=160)
for col,colr,lab,lw in [("SP500",C["orange"],"S&P 500 buy & hold",1.9),
                        ("Momentum",C["aqua"],"12-mo absolute momentum (monthly)",1.6),
                        ("SMA",C["violet"],"10-mo SMA filter (monthly)",1.5),
                        ("Donchian",C["blue"],"Donchian 20/10 breakout (daily)",2.3)]:
    ax.plot(s.index, s[col], color=colr, lw=lw, label=lab)
ax.set_yscale("log"); ax.set_yticks([1,2,5,10,20,50,100]); ax.set_yticklabels(["$1","$2","$5","$10","$20","$50","$100"])
for col,colr in [("Donchian",C["blue"]),("SP500",C["orange"]),("Momentum",C["aqua"]),("SMA",C["violet"])]:
    ax.text(s.index[-1], s[col].iloc[-1], f"  ${s[col].iloc[-1]:.0f}", color=colr, va="center", fontweight="bold")
ax.set_title("Growth of $1, Jan 1987 – Oct 2026 (log scale)", fontweight="bold")
ax.legend(loc="upper left"); ax.set_xlim(s.index[0], s.index[-1]+pd.Timedelta(days=1000))
ax.xaxis.set_major_locator(mdates.YearLocator(4))
fig.tight_layout(); fig.savefig(OUT/"c1_equity.png"); plt.close(fig)

# 2 — THE crash-response chart
crashes = ["2011 Euro crisis","2015-16 correction","2018 Q4","COVID crash","2022 bear","2025 tariff shock"]
ep = {e["episode"]: e for e in S["episodes"]}
fig, ax = plt.subplots(figsize=(11,4.6), dpi=160)
x = np.arange(len(crashes)); w = 0.26
d = [ep[c]["donchian"]*100 for c in crashes]
m = [ep[c]["momentum"]*100 for c in crashes]
b = [ep[c]["sp500"]*100 for c in crashes]
ax.bar(x-w, d, w, color=C["blue"], label="Donchian 20/10 (daily exit)")
ax.bar(x,   m, w, color=C["aqua"], label="12-mo absolute momentum (monthly)")
ax.bar(x+w, b, w, color=C["orange"], label="S&P 500")
for i,(dv,mv,bv) in enumerate(zip(d,m,b)):
    for off,v in [(-w,dv),(0,mv),(w,bv)]:
        ax.text(i+off, v-1.2, f"{v:.0f}", ha="center", va="top", fontsize=8.5, color=C["ink2"])
ax.axhline(0, color=C["ink2"], lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(crashes, fontsize=9.5)
ax.set_ylabel("Return through the episode (%)"); ax.set_ylim(-42, 6)
ax.set_title("What a daily exit buys you: Donchian in six selloffs", fontweight="bold")
ax.legend(loc="lower left", ncol=1)
fig.tight_layout(); fig.savefig(OUT/"c2_crashes.png"); plt.close(fig)

# 3 — parameter grid heatmap
g = pd.DataFrame(S["grid"])
piv = g.pivot(index="entry", columns="exit", values="cagr")*100
fig, ax = plt.subplots(figsize=(8.2,4.4), dpi=160)
im = ax.imshow(piv.values, cmap="RdYlGn", aspect="auto", vmin=0, vmax=11.5)
ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns)
ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index); ax.grid(False)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i,j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=10,
                    fontweight="bold" if (piv.index[i]==20 and piv.columns[j]==10) else "normal",
                    color="white" if (piv.index[i]==20 and piv.columns[j]==10) else C["ink"])
            if piv.index[i]==20 and piv.columns[j]==10:
                ax.add_patch(plt.Rectangle((j-.5,i-.5),1,1,fill=False,edgecolor=C["ink"],lw=2.5))
ax.set_xlabel("Exit channel (days)"); ax.set_ylabel("Entry channel (days)")
ax.set_title("CAGR by channel length — boxed is the Turtles' System 1 (20/10)\nS&P 500 buy & hold returned 11.3%", fontweight="bold", fontsize=11.5)
fig.tight_layout(); fig.savefig(OUT/"c3_grid.png"); plt.close(fig)

# 4 — cost cliff
cs = pd.DataFrame(S["cost_sensitivity"])
fig, ax = plt.subplots(figsize=(11,3.8), dpi=160)
ax.plot(cs["cost_bps"], cs["cagr"]*100, "-o", color=C["blue"], lw=2.4, ms=10)
for _,r in cs.iterrows():
    ax.annotate(f"{r['cagr']*100:.1f}%", (r["cost_bps"], r["cagr"]*100), textcoords="offset points",
                xytext=(0,12), ha="center", fontsize=9.5, color=C["ink2"])
ax.axhline(0, color=C["red"], ls="--", lw=1.2)
ax.axhline(S["benchmark"]["cagr"]*100, color=C["orange"], ls="--", lw=1.3)
ax.text(50, S["benchmark"]["cagr"]*100-1.0, "S&P 500 buy & hold", color=C["orange"], fontsize=9, ha="right")
ax.set_xlabel("Round-trip cost per trade (basis points)"); ax.set_ylabel("CAGR (%)")
ax.set_title("At 24x annual turnover, costs decide everything", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"c4_costs.png"); plt.close(fig)

# 5 — does a breakout predict anything?
sg = S["signals"]
fig, axes = plt.subplots(1,2, figsize=(11,3.6), dpi=160)
a=axes[0]
vals=[sg["s1_pct_entries_up_20d"]*100, sg["baseline_pct_up_20d"]*100]
a.bar(["After a 20-day\nbreakout","Any random day"], vals, color=[C["blue"],C["ink2"]])
for i,v in enumerate(vals): a.text(i,v,f"{v:.1f}%",ha="center",va="bottom",fontsize=11,fontweight="bold",color=C["ink2"])
a.set_ylim(0,80); a.set_title("Chance the S&P is higher 20 days later")
a=axes[1]
vals=[sg["s1_avg_fwd20_after_entry"]*100, sg["baseline_avg_fwd20"]*100]
a.bar(["After a 20-day\nbreakout","Any random day"], vals, color=[C["blue"],C["ink2"]])
for i,v in enumerate(vals): a.text(i,v,f"+{v:.2f}%",ha="center",va="bottom",fontsize=11,fontweight="bold",color=C["ink2"])
a.set_ylim(0,1.25); a.set_title("Average S&P return over the next 20 days")
fig.suptitle(f"The signal predicts nothing: {sg['s1_entries']} breakouts over 40 years", fontweight="bold")
fig.tight_layout(); fig.savefig(OUT/"c5_edge.png"); plt.close(fig)

# 6 — drawdowns
fig, ax = plt.subplots(figsize=(11,3.8), dpi=160)
ax.fill_between(s.index, s["SP_dd"]*100, 0, color=C["orange"], alpha=0.30, lw=0, label="S&P 500")
ax.plot(s.index, s["D_dd"]*100, color=C["blue"], lw=1.4, label="Donchian 20/10")
ax.set_ylim(-60,2); ax.set_ylabel("Drawdown (%)")
ax.annotate("underwater from Jan 1999 to May 2013", xy=(pd.Timestamp("2006-01-01"), -30),
            xytext=(pd.Timestamp("1993-06-01"), -48), fontsize=9.5, color=C["ink2"],
            arrowprops=dict(arrowstyle="-", color=C["ink2"]))
ax.set_title("Donchian's worst drawdown took fourteen years to recover", fontweight="bold")
ax.legend(loc="lower right", ncol=2); ax.xaxis.set_major_locator(mdates.YearLocator(4))
fig.tight_layout(); fig.savefig(OUT/"c6_drawdown.png"); plt.close(fig)
print("charts written")
