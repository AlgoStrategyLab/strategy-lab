"""Cross-strategy comparison charts for the /compare/ page.

The articles each cover their own history, which is right for the article and wrong
for a comparison: dual momentum starts in 1997 and the rest in 1987, so their
headline figures are not measured over the same market. These charts use the window
all strategies share, recomputed from the committed equity series, and the page says
so next to them.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRADING_DAYS = 252

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

#: Which column of each strategy's committed series holds its equity curve.
EQUITY_COLUMN = {
    "dual-momentum": "GEM",
    "sma-trend-filter": "SMA",
    "donchian-breakout": "Donchian",
    "rsi2-mean-reversion": "RSI2",
}

COLOURS = [C["blue"], C["aqua"], C["violet"], C["yellow"], C["red"]]


def _series_path(slug: str) -> Path | None:
    out = ROOT / "strategies" / slug / "output"
    for p in sorted(out.glob("*series*.csv")):
        if "basket" not in p.name:
            return p
    return None


def load_curves(strategies) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Equity curves for every strategy plus the index, rebased over the shared window."""
    raw, bench = {}, None
    for s in strategies:
        path = _series_path(s.slug)
        col = EQUITY_COLUMN.get(s.slug)
        if path is None or col is None:
            continue
        d = pd.read_csv(path, index_col=0, parse_dates=True)
        if col not in d.columns:
            continue
        raw[s.slug] = d[col]
        if bench is None and "SP500" in d.columns:
            bench = d["SP500"]
    if not raw:
        raise ValueError("no equity series found to compare")

    start = max(v.index[0] for v in raw.values())
    end = min(v.index[-1] for v in raw.values())
    if bench is not None:
        raw["__benchmark__"] = bench

    frame = pd.DataFrame(raw).loc[start:end].dropna(how="all").ffill()
    frame = frame / frame.iloc[0]          # rebase every curve to $1 at the shared start
    return frame, start, end


def window_stats(frame: pd.DataFrame) -> dict[str, dict]:
    """CAGR, volatility, Sharpe and max drawdown recomputed over the shared window."""
    years = (frame.index[-1] - frame.index[0]).days / 365.25
    stats = {}
    for col in frame.columns:
        eq = frame[col].dropna()
        if eq.empty:
            continue
        ret = eq.pct_change().dropna()
        vol = float(ret.std() * np.sqrt(TRADING_DAYS))
        cagr = float(eq.iloc[-1] ** (1 / years) - 1)
        stats[col] = {
            "cagr": cagr,
            "volatility": vol,
            "sharpe": float(ret.mean() / ret.std() * np.sqrt(TRADING_DAYS)) if ret.std() else 0.0,
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "final": float(eq.iloc[-1]),
        }
    return stats



# Market episodes inside the shared window. Peak-to-trough and trough-to-peak dates for
# the index, so every strategy is judged over the same stretch of the same market.
EPISODES = [
    ("Dot-com bust",      "2000-03-24", "2002-10-09"),
    ("2003\u201307 bull",     "2002-10-09", "2007-10-09"),
    ("Financial crisis",  "2007-10-09", "2009-03-09"),
    ("2010s bull",        "2009-03-09", "2020-02-19"),
    ("COVID crash",       "2020-02-19", "2020-03-23"),
    ("COVID rebound",     "2020-03-23", "2021-12-31"),
    ("2022 bear",         "2022-01-03", "2022-10-12"),
    ("AI bull",           "2022-10-12", "2025-02-19"),
    ("2025 tariff shock", "2025-02-19", "2025-04-08"),
]


def capture_ratios(frame: pd.DataFrame, col: str) -> tuple[float, float]:
    """Up- and down-capture against the index, on monthly returns.

    Up-capture is the strategy's average return in months the index rose, as a
    percentage of the index's average rise; down-capture is the same for months it
    fell. The index is 100/100 by construction. Low down-capture with high
    up-capture is the whole point of a defensive rule, and it is invisible on an
    equity curve.
    """
    m = frame[[col, "__benchmark__"]].resample("ME").last().pct_change().dropna()
    up, down = m[m["__benchmark__"] > 0], m[m["__benchmark__"] < 0]
    u = float(up[col].mean() / up["__benchmark__"].mean() * 100) if len(up) else float("nan")
    d = float(down[col].mean() / down["__benchmark__"].mean() * 100) if len(down) else float("nan")
    return u, d


def render(strategies, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    frame, start, end = load_curves(strategies)
    stats = window_stats(frame)
    label = {s.slug: (s.meta.get("short_name") or s.slug) for s in strategies}
    order = [s.slug for s in strategies if s.slug in frame.columns]
    colour = {slug: COLOURS[i % len(COLOURS)] for i, slug in enumerate(order)}
    bench = frame["__benchmark__"]

    # --- 1. growth of $1 ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5.4), dpi=160)
    ax.plot(frame.index, bench, color=C["orange"], lw=2.2, label="S&P 500", zorder=5)
    for slug in order:
        ax.plot(frame.index, frame[slug], color=colour[slug], lw=1.9, label=label[slug])
    ax.set_yscale("log")
    ticks = [0.5, 1, 2, 4, 8, 16]
    ax.set_yticks(ticks); ax.set_yticklabels([f"${t:g}" for t in ticks])
    for slug in order:
        ax.text(frame.index[-1], frame[slug].iloc[-1], f"  ${frame[slug].iloc[-1]:.1f}",
                color=colour[slug], va="center", fontsize=9.5, fontweight="semibold")
    ax.text(frame.index[-1], bench.iloc[-1], f"  ${bench.iloc[-1]:.1f}",
            color=C["orange"], va="center", fontsize=9.5, fontweight="semibold")
    ax.set_xlim(frame.index[0], frame.index[-1] + pd.Timedelta(days=1250))
    ax.set_title(f"Growth of $1 over the window every strategy shares "
                 f"({start:%B %Y} \u2013 {end:%B %Y}, log scale)")
    ax.legend(loc="upper left", ncol=2)
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    fig.tight_layout(); fig.savefig(outdir / "compare_growth.png"); plt.close(fig)

    # --- 2. measured against the benchmark, not beside it -------------------
    # Each curve divided by the index. Flat means keeping pace; falling means the
    # index is winning even while the strategy makes money.
    fig, ax = plt.subplots(figsize=(11, 5.4), dpi=160)
    ax.axhline(1.0, color=C["orange"], lw=2.0, zorder=4)
    # Sit the baseline label mid-chart: any strategy finishing near parity would
    # collide with it at the right-hand edge, and one of them finishes at 1.11x.
    ax.text(frame.index[int(len(frame) * 0.60)], 1.0, "S&P 500 \u2014 parity",
            color=C["orange"], fontsize=10, fontweight="semibold",
            va="bottom", ha="center",
            bbox=dict(facecolor=C["surface"], edgecolor="none", pad=2.5))
    for slug in order:
        rel = frame[slug] / bench
        ax.plot(frame.index, rel, color=colour[slug], lw=1.9, label=label[slug])
        ax.text(frame.index[-1], rel.iloc[-1], f"  {rel.iloc[-1]:.2f}\u00d7",
                color=colour[slug], va="center", fontsize=9.5, fontweight="semibold")
    ax.set_yscale("log")
    ax.set_yticks([0.125, 0.25, 0.5, 1, 2, 4])
    ax.set_yticklabels(["0.125\u00d7", "0.25\u00d7", "0.5\u00d7", "1\u00d7", "2\u00d7", "4\u00d7"])
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())   # no 6x10^-1 clutter
    ax.set_ylabel("Value relative to the S&P 500")
    ax.set_xlim(frame.index[0], frame.index[-1] + pd.Timedelta(days=1100))
    ax.set_title("Every strategy divided by the index. Rising means winning; flat means keeping pace.")
    ax.legend(loc="lower left", ncol=2)
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    fig.tight_layout(); fig.savefig(outdir / "compare_relative.png"); plt.close(fig)

    # --- 3. up-capture against down-capture --------------------------------
    caps = {slug: capture_ratios(frame, slug) for slug in order}
    fig, ax = plt.subplots(figsize=(9.6, 6.0), dpi=160)
    ax.axhline(100, color=C["grid"], lw=1.2, zorder=1)
    ax.axvline(100, color=C["grid"], lw=1.2, zorder=1)
    # The meaningful reference is equal capture. Above this line a strategy keeps a
    # larger share of the index's good months than of its bad ones, which is the only
    # sense in which a defensive rule is doing its job.
    ax.plot([-15, 115], [-15, 115], color=C["aqua"], lw=1.6, ls="--", zorder=1)
    ax.text(-12, -4, "equal capture \u2014 above this line a strategy keeps more\n"
            "of the index's rise than of its fall", color=C["aqua"], fontsize=9.5,
            fontweight="semibold", va="top", ha="left")
    for slug in order:
        u, d = caps[slug]
        ax.scatter(d, u, s=200, color=colour[slug], edgecolor="white", linewidth=1.5, zorder=4)
        ax.annotate(label[slug], (d, u), textcoords="offset points", xytext=(12, -3),
                    fontsize=9.5, color=C["ink2"], zorder=5)
    ax.scatter(100, 100, s=220, marker="D", color=C["orange"], edgecolor="white",
               linewidth=1.5, zorder=4)
    ax.annotate("S&P 500", (100, 100), textcoords="offset points", xytext=(12, -3),
                fontsize=9.5, color=C["orange"], fontweight="semibold", zorder=5)
    ax.set_xlabel("Down-capture: share of the index's bad months, %  \u2192  worse")
    ax.set_ylabel("Up-capture: share of the index's good months, %")
    ax.set_title("How much of the index each strategy actually catches")
    ax.set_xlim(-18, 118); ax.set_ylim(-22, 115)
    fig.tight_layout(); fig.savefig(outdir / "compare_capture.png"); plt.close(fig)

    # --- 4. excess return through each market episode ----------------------
    rows, used = [], []
    for name, a, b in EPISODES:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if a < frame.index[0] or b > frame.index[-1]:
            continue
        seg = frame.loc[a:b]
        if len(seg) < 2:
            continue
        bgrow = float(seg["__benchmark__"].iloc[-1] / seg["__benchmark__"].iloc[0])
        # Relative wealth change, not absolute excess: an eleven-year bull and a
        # one-month crash cannot be compared on points of excess return, and the long
        # episode would swamp the colour scale. This is how much of the index's result
        # each strategy kept, which is the same quantity the ratio chart above plots.
        rows.append([float(seg[s].iloc[-1] / seg[s].iloc[0]) / bgrow - 1 for s in order])
        used.append(f"{name}\n({(bgrow-1)*100:+.0f}% index)")
    grid = np.array(rows) * 100

    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=160)
    lim = float(np.nanmax(np.abs(grid))) if grid.size else 1.0
    im = ax.imshow(grid.T, cmap="RdYlGn", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(used)))
    ax.set_xticklabels(used, fontsize=8.5, rotation=32, ha="right")
    ax.set_yticks(range(len(order))); ax.set_yticklabels([label[s] for s in order], fontsize=10)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid[i, j]
            ax.text(i, j, f"{v:+.0f}%", ha="center", va="center", fontsize=9,
                    color="#111" if abs(v) < lim * 0.65 else "white", fontweight="semibold")
    ax.set_title("How each strategy fared against the index through every market episode")
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="gained / lost against the S&P 500", shrink=0.85)
    fig.tight_layout(); fig.savefig(outdir / "compare_episodes.png"); plt.close(fig)

    return {"start": start, "end": end, "stats": stats, "labels": label,
            "order": order, "capture": caps}
