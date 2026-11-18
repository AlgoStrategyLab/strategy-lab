"""Article #5: pairs trading by the distance method, on a liquid ETF universe."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).parent))

from strategylab import Backtest, load_prices  # noqa: E402
from strategylab.strategy import Strategy  # noqa: E402
from strategy import PairsTrading, select_pairs  # noqa: E402

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

UNIVERSE = ["SPY", "DIA", "QQQ", "IWM", "MDY",
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
            "EWA", "EWC", "EWG", "EWH", "EWJ", "EWS", "EWU", "EWW"]

DATA_START = "1998-12-22"      # the sector SPDRs list; 20 of 22 names exist from here
EVAL = "2000-01-03"            # first trading window opens after a 12-month formation
SPLIT = "2007-01-01"           # Gatev, Goetzmann & Rouwenhorst published in 2006
COST = 10
BORROW = 50                    # bps a year to borrow a liquid ETF


def build():
    px = load_prices(UNIVERSE, start=DATA_START)
    return px[px["SPY"].notna()]


class BuyHold(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{"SPY": 1.0}] * len(rb), index=rb)


class SixtyForty(Strategy):
    """60/40 proxy from the universe we have: equities and a defensive sector blend."""
    def target_weights(self, prices, rb):
        return pd.DataFrame([{"SPY": 0.6, "XLP": 0.4}] * len(rb), index=rb)


class RandomPairs(PairsTrading):
    """The same machinery, but the pairs are drawn at random instead of by closeness.

    This is the control the distance method needs. If picking the closest-tracking pairs
    carries information, it has to beat pairs chosen by coin flip from the same universe
    on the same dates with the same entry rule. If it does not, the selection step —
    the part everyone argues about — is doing nothing.
    """

    def __init__(self, name="Random pairs (control)", params=None, seed=0):
        super().__init__(name=name, params=params)
        self.seed = seed

    def weight_matrix(self, prices):
        import strategy as _mod
        rng = np.random.default_rng(self.seed)
        real = _mod.select_pairs

        def shuffled(formation, n_pairs):
            every = real(formation, 10 ** 9)          # every eligible pair, ranked
            if not every:
                return []
            picks = rng.choice(len(every), size=min(n_pairs, len(every)), replace=False)
            return [every[i] for i in picks]

        _mod.select_pairs = shuffled
        try:
            return super().weight_matrix(prices)
        finally:
            _mod.select_pairs = real


def episode_returns(daily, bench, episodes):
    rows = []
    for name, a, b in episodes:
        seg, bseg = daily.loc[a:b], bench.loc[a:b]
        if len(seg) < 2:
            continue
        rows.append({"episode": name,
                     "pairs": round(float((1 + seg).prod() - 1), 4),
                     "sp500": round(float((1 + bseg).prod() - 1), 4)})
    return rows


EPISODES = [
    ("Dot-com bust", "2000-03-24", "2002-10-09"),
    ("2003-07 bull", "2002-10-09", "2007-10-09"),
    ("Financial crisis", "2007-10-09", "2009-03-09"),
    ("Quant quake (Aug 2007)", "2007-08-01", "2007-08-31"),
    ("2010s bull", "2009-03-09", "2020-02-19"),
    ("COVID crash", "2020-02-19", "2020-03-23"),
    ("2022 bear", "2022-01-03", "2022-10-12"),
    ("AI bull", "2022-10-12", "2025-02-19"),
    ("2025 tariff shock", "2025-02-19", "2025-04-08"),
]


def main():
    px = build()
    print("data:", px.index[0].date(), "->", px.index[-1].date(), px.shape)
    kw = dict(benchmark="SPY", rebalance="D", cost_bps=COST, start=EVAL, borrow_bps=BORROW)

    base = PairsTrading()
    main_r = Backtest(px, base, **kw).run()
    main_r.save(OUT / "pairs_main.json")
    trades = base.trades

    bh = Backtest(px, BuyHold(name="S&P 500 buy & hold"), **{**kw, "cost_bps": 0, "rebalance": "M"}).run()
    sf = Backtest(px, SixtyForty(name="60/40 proxy"), **{**kw, "rebalance": "M"}).run()

    # --- does the selection step do anything? -----------------------------
    randoms, random_curves = [], {}
    for seed in range(5):
        r = Backtest(px, RandomPairs(seed=seed), **kw).run()
        randoms.append(r.metrics)
        random_curves[f"random_{seed}"] = r.equity
    rand_mean = {k: float(np.mean([m[k] for m in randoms]))
                 for k in ["cagr", "sharpe", "max_drawdown", "volatility", "annual_turnover"]}

    # --- parameter grids ---------------------------------------------------
    pair_sweep = []
    for n in [1, 3, 5, 10, 20, 40]:
        r = Backtest(px, PairsTrading(params={"n_pairs": n}), **kw).run()
        pair_sweep.append({"n_pairs": n, **{k: r.metrics[k] for k in
                          ["cagr", "sharpe", "max_drawdown", "volatility", "annual_turnover",
                           "avg_gross_exposure", "beta"]}})

    sigma_sweep = []
    for sig in [1.0, 1.5, 2.0, 2.5, 3.0]:
        r = Backtest(px, PairsTrading(params={"entry_sigma": sig}), **kw).run()
        sigma_sweep.append({"entry_sigma": sig, **{k: r.metrics[k] for k in
                           ["cagr", "sharpe", "max_drawdown", "annual_turnover", "avg_gross_exposure"]}})

    costs = [{"cost_bps": c, **{k: Backtest(px, PairsTrading(), **{**kw, "cost_bps": c}).run().metrics[k]
              for k in ["cagr", "sharpe", "max_drawdown"]}} for c in [0, 5, 10, 25, 50]]

    borrows = [{"borrow_bps": b, **{k: Backtest(px, PairsTrading(), **{**kw, "borrow_bps": b}).run().metrics[k]
                for k in ["cagr", "sharpe", "annual_borrow_cost"]}} for b in [0, 25, 50, 100, 200, 400]]

    # --- before and after the paper ---------------------------------------
    def window(a, b, strat=None):
        r = Backtest(px, strat or PairsTrading(), **{**kw, "start": a, "end": b}).run()
        return {"start": a, "end": b, **{k: r.metrics[k] for k in
                ["cagr", "sharpe", "max_drawdown", "volatility", "beta", "annual_turnover"]}}

    inout = {
        "in_sample": window(EVAL, "2006-12-31"),
        "out_of_sample": window(SPLIT, None),
        "benchmark_in_sample": {"cagr": Backtest(px, BuyHold(name="bh"), **{**kw, "cost_bps": 0, "rebalance": "M", "start": EVAL, "end": "2006-12-31"}).run().metrics["cagr"]},
        "benchmark_out_of_sample": {"cagr": Backtest(px, BuyHold(name="bh"), **{**kw, "cost_bps": 0, "rebalance": "M", "start": SPLIT}).run().metrics["cagr"]},
    }

    # --- what does the method actually select? -----------------------------
    counts = trades["pair"].value_counts()
    conv = trades["reason"].value_counts().to_dict()
    trade_stats = {
        "trades": int(len(trades)),
        "converged": int(conv.get("converged", 0)),
        "closed_at_period_end": int(conv.get("period end", 0)),
        "convergence_rate": round(conv.get("converged", 0) / max(len(trades), 1), 4),
        "avg_holding_days": round(float(trades["days"].mean()), 1),
        "median_holding_days": float(trades["days"].median()),
        "top_pairs": [{"pair": p, "times_selected": int(c)} for p, c in counts.head(12).items()],
        "distinct_pairs": int(counts.size),
    }

    # how close are the chosen pairs, really?
    sample = []
    idx = px.index
    for start in range(0, len(idx) - 378, 126):
        form = px.iloc[start:start + 252]
        picked = select_pairs(form, 5)
        for p in picked:
            sample.append({"date": str(idx[start + 252].date()), "pair": f"{p.a}/{p.b}",
                           "ssd": round(p.ssd, 4), "sigma": round(p.sigma, 5)})

    S = {
        "main": main_r.metrics,
        "main_extended": main_r.extended,
        "benchmark": main_r.benchmark_metrics,
        "benchmark_extended": main_r.benchmark_extended,
        "buy_hold": bh.metrics,
        "sixty_forty": sf.metrics,
        "random_pairs_mean": rand_mean,
        "random_pairs_runs": randoms,
        "pair_sweep": pair_sweep,
        "sigma_sweep": sigma_sweep,
        "cost_sensitivity": costs,
        "borrow_sensitivity": borrows,
        "in_out_sample": inout,
        "trades": trade_stats,
        "selections": sample,
        "episodes": episode_returns(main_r.daily_returns, main_r.benchmark_equity.pct_change().fillna(0), EPISODES),
        "drawdowns": main_r.drawdowns,
        "yearly": main_r.yearly,
        "config": {"universe": UNIVERSE, "data_start": DATA_START, "eval_start": EVAL,
                   "split": SPLIT, "cost_bps": COST, "borrow_bps": BORROW,
                   "rule": "12-month formation, 5 closest pairs by SSD, enter at 2 sigma, "
                           "exit on convergence or at the end of a 6-month trading window"},
    }
    (OUT / "pairs_summary.json").write_text(json.dumps(S, indent=2, default=str))

    pd.DataFrame({"Pairs": main_r.equity, "SP500": main_r.benchmark_equity,
                  "Pairs_dd": main_r.drawdown,
                  "SP_dd": main_r.benchmark_equity / main_r.benchmark_equity.cummax() - 1}).to_csv(OUT / "pairs_series.csv")
    trades.to_csv(OUT / "trades.csv", index=False)
    pd.DataFrame({"chosen": main_r.equity, **random_curves}).to_csv(OUT / "selection_curves.csv")

    m, b = S["main"], S["benchmark"]
    print(f"\nPairs   CAGR {m['cagr']:+.4f}  vol {m['volatility']:.4f}  Sharpe {m['sharpe']:.3f}  "
          f"DD {m['max_drawdown']:.4f}  beta {m['beta']:+.3f}  turn {m['annual_turnover']:.2f}")
    print(f"S&P 500 CAGR {b['cagr']:+.4f}  vol {b['volatility']:.4f}  Sharpe {b['sharpe']:.3f}  DD {b['max_drawdown']:.4f}")
    print(f"gross {m['avg_gross_exposure']:.3f}  short {m['avg_short_exposure']:.3f}  "
          f"net {m['avg_net_exposure']:+.4f}  borrow drag {m['annual_borrow_cost']:.4f}")
    print("\nrandom-pair control:", {k: round(v, 4) for k, v in rand_mean.items()})
    print("\ntrades:", json.dumps(trade_stats["top_pairs"][:6]), trade_stats["convergence_rate"])
    print("\npair sweep:"); print(pd.DataFrame(pair_sweep).to_string(index=False))
    print("\nsigma sweep:"); print(pd.DataFrame(sigma_sweep).to_string(index=False))
    print("\ncosts:"); print(pd.DataFrame(costs).to_string(index=False))
    print("\nborrow:"); print(pd.DataFrame(borrows).to_string(index=False))
    print("\nin/out:", json.dumps(inout, indent=1, default=str))
    print("\nepisodes:"); print(pd.DataFrame(S["episodes"]).to_string(index=False))


if __name__ == "__main__":
    main()
