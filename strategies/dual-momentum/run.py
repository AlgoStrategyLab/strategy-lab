"""Article #1 run: Dual Momentum (GEM), 1997-2026, mutual-fund proxies + ETF cross-check."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from strategylab import load_prices, Backtest, parameter_sweep, walk_forward, in_vs_out_of_sample  # noqa: E402
from strategy import DualMomentum  # noqa: E402

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)


def cash_index(start="1990-01-01") -> pd.Series:
    """Daily T-bill accrual index from the 13-week bill yield (^IRX, annualised %)."""
    irx = load_prices(["^IRX"], start=start)["^IRX"].ffill().clip(lower=0)
    daily = (irx / 100.0) / 252.0
    return (1 + daily.shift(1).fillna(0)).cumprod().rename("CASH")


def build_prices(us, intl, bonds, start):
    px = load_prices([us, intl, bonds], start=start)
    cash = cash_index(start)
    px = px.join(cash, how="left")
    px["CASH"] = px["CASH"].ffill()
    return px.dropna()


def main():
    COST = 10  # bps per unit turnover
    # ---- Main run: mutual-fund proxies, longest common history
    px = build_prices("VFINX", "VGTSX", "VBMFX", "1996-04-01")
    strat = DualMomentum()
    bt = Backtest(px, strat, benchmark="VFINX", rebalance="M", cost_bps=COST, start="1997-05-01")
    res = bt.run()
    res.save(OUT / "dual_momentum_main.json")
    print("MAIN", json.dumps(res.metrics, indent=1))
    print("BENCH", json.dumps(res.benchmark_metrics, indent=1))

    # 60/40 reference (monthly rebalanced) for context
    from strategylab.strategy import Strategy

    class SixtyForty(Strategy):
        def target_weights(self, prices, rb):
            return pd.DataFrame([{"VFINX": .6, "VBMFX": .4}] * len(rb), index=rb)
    r6040 = Backtest(px, SixtyForty(name="60/40", params={}), benchmark="VFINX", cost_bps=COST, start="1997-05-01").run()
    intl_bh = Backtest(px, type("I", (Strategy,), {"target_weights": lambda self, p, rb: pd.DataFrame([{"VGTSX": 1.0}] * len(rb), index=rb)})(name="Intl B&H", params={}),
                       benchmark="VFINX", cost_bps=0, start="1997-05-01").run()

    # ---- Component ablation: relative-only, absolute-only
    rel_only = Backtest(px, strat.with_params(abs_on=False), benchmark="VFINX", cost_bps=COST, start="1997-05-01").run()
    abs_only = Backtest(px, strat.with_params(rel_on=False), benchmark="VFINX", cost_bps=COST, start="1997-05-01").run()

    # ---- Lookback sensitivity
    sweep = parameter_sweep(px, strat, {"lookback": [3, 6, 9, 10, 12, 15, 18]}, benchmark="VFINX", cost_bps=COST, start="1997-05-01")
    # cost sensitivity
    costs = pd.DataFrame([{"cost_bps": c, **{k: Backtest(px, strat, benchmark="VFINX", cost_bps=c, start="1997-05-01").run().metrics[k] for k in ["cagr", "sharpe", "max_drawdown"]}} for c in [0, 10, 25, 50]])

    # ---- In-sample / out-of-sample split at Antonacci's publication year
    io = in_vs_out_of_sample(px, strat, split="2014-01-01", benchmark="VFINX", cost_bps=COST, start="1997-05-01")

    # ---- Walk-forward: choose lookback on trailing 5y, test next 1y
    wf = walk_forward(px, strat, {"lookback": [3, 6, 9, 12, 15, 18]}, train_years=5, test_years=1,
                      first_test_start="2003-01-01", benchmark="VFINX", cost_bps=COST)

    # ---- ETF cross-check (SPY/EFA/AGG) from 2004-10
    pxe = build_prices("SPY", "EFA", "AGG", "2003-09-01")
    etf = Backtest(pxe, strat.with_params(us="SPY", intl="EFA", bonds="AGG"), benchmark="SPY", cost_bps=COST, start="2004-10-01").run()
    mf_same = Backtest(px, strat, benchmark="VFINX", cost_bps=COST, start="2004-10-01").run()

    # ---- Regime table: strategy vs benchmark in named episodes
    episodes = {
        "Dot-com bust (Mar 2000 – Oct 2002)": ("2000-03-24", "2002-10-09"),
        "GFC (Oct 2007 – Mar 2009)": ("2007-10-09", "2009-03-09"),
        "2011 Euro crisis (May – Oct 2011)": ("2011-05-02", "2011-10-03"),
        "2015–16 correction (May 2015 – Feb 2016)": ("2015-05-21", "2016-02-11"),
        "2018 Q4 (Sep – Dec 2018)": ("2018-09-20", "2018-12-24"),
        "COVID crash (Feb – Mar 2020)": ("2020-02-19", "2020-03-23"),
        "COVID rebound (Mar 2020 – Dec 2020)": ("2020-03-23", "2020-12-31"),
        "2022 bear (Jan – Oct 2022)": ("2022-01-03", "2022-10-12"),
        "2023–24 AI bull (Jan 2023 – Dec 2024)": ("2023-01-03", "2024-12-31"),
        "2025 tariff shock (Feb – Apr 2025)": ("2025-02-19", "2025-04-08"),
    }
    ep_rows = []
    for name, (a, b) in episodes.items():
        s = res.daily_returns.loc[a:b]; bm = px["VFINX"].pct_change().loc[a:b]
        held = res.weights.loc[a:b].idxmax(axis=1).value_counts(normalize=True).round(2).to_dict()
        ep_rows.append({"episode": name, "strategy": round(float((1 + s).prod() - 1), 4),
                        "sp500": round(float((1 + bm).prod() - 1), 4), "held": held})

    # allocation stats
    hold = res.weights.idxmax(axis=1)
    hold = hold.where(res.weights.max(axis=1) > 0.5, "CASH")
    alloc_share = hold.value_counts(normalize=True).round(3).to_dict()
    switches = int((hold != hold.shift()).sum() - 1)

    summary = {
        "main": res.metrics, "benchmark": res.benchmark_metrics,
        "sixty_forty": r6040.metrics, "intl_bh": intl_bh.metrics,
        "relative_only": rel_only.metrics, "absolute_only": abs_only.metrics,
        "lookback_sweep": sweep.to_dict(orient="records"),
        "cost_sensitivity": costs.to_dict(orient="records"),
        "in_out_sample": io,
        "walk_forward": wf.to_dict(orient="records"),
        "etf_crosscheck": {"etf": etf.metrics, "mutual_fund_same_window": mf_same.metrics, "etf_benchmark": etf.benchmark_metrics},
        "episodes": ep_rows,
        "allocation_share": alloc_share, "switches": switches,
        "yearly": res.yearly,
    }
    (OUT / "dual_momentum_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    # series for charts
    pd.DataFrame({"GEM": res.equity, "SP500": res.benchmark_equity, "60/40": r6040.equity, "Intl": intl_bh.equity,
                  "GEM_dd": res.drawdown, "SP500_dd": res.benchmark_equity / res.benchmark_equity.cummax() - 1,
                  "holding": hold}).to_csv(OUT / "dual_momentum_series.csv")
    print(json.dumps({k: summary[k] for k in ["allocation_share", "switches"]}))
    print(sweep.to_string()); print(costs.to_string()); print(wf.to_string())
    print(json.dumps(io, indent=1)); print(json.dumps(ep_rows, indent=1, default=str))
    print("REL", {k: rel_only.metrics[k] for k in ["cagr","sharpe","max_drawdown"]})
    print("ABS", {k: abs_only.metrics[k] for k in ["cagr","sharpe","max_drawdown"]})
    print("6040", {k: r6040.metrics[k] for k in ["cagr","sharpe","max_drawdown"]})
    print("INTL", {k: intl_bh.metrics[k] for k in ["cagr","sharpe","max_drawdown"]})
    print("ETF", {k: etf.metrics[k] for k in ["cagr","sharpe","max_drawdown"]}, "MF", {k: mf_same.metrics[k] for k in ["cagr","sharpe","max_drawdown"]}, "ETFB", {k: etf.benchmark_metrics[k] for k in ["cagr","sharpe","max_drawdown"]})


if __name__ == "__main__":
    main()
