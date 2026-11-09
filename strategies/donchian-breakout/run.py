"""Article #3: Donchian channel breakout (the Turtle rule) on equity indices."""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from strategylab import load_prices, Backtest, parameter_sweep, walk_forward, in_vs_out_of_sample
from strategylab.strategy import Strategy
from strategylab.engine import rebalance_calendar
from strategy import DonchianBreakout, DonchianVolSized, _donchian_state

OUT = Path(__file__).parent / "output"; OUT.mkdir(exist_ok=True)
COST = 10


def cash_index(start):
    irx = load_prices(["^IRX"], start=start)["^IRX"].ffill().clip(lower=0)
    return (1 + (irx / 100.0 / 252.0).shift(1).fillna(0)).cumprod().rename("CASH")


def build(warmup="1980-01-01"):
    px = load_prices(["VFINX", "VBMFX"], start=warmup).join(cash_index(warmup), how="left")
    px["CASH"] = px["CASH"].ffill()
    px = px[px["VFINX"].notna() & px["CASH"].notna()]
    px["VBMFX"] = px["VBMFX"].ffill().bfill()
    return px


class BH(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{self.params["t"]: 1.0}] * len(rb), index=rb)


class SixtyForty(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{"VFINX": .6, "VBMFX": .4}] * len(rb), index=rb)


class SmaFilter(Strategy):
    def target_weights(self, prices, rb):
        me = prices.resample("ME").last()
        sma = me["VFINX"].rolling(10).mean()
        rows = []
        for d in rb:
            s = sma.loc[:d]
            on = len(s) and not pd.isna(s.iloc[-1]) and float(me["VFINX"].loc[:d].iloc[-1]) > float(s.iloc[-1])
            rows.append({"VFINX": 1.0} if on else {"VBMFX": 1.0})
        return pd.DataFrame(rows, index=rb).fillna(0.0)


class AbsMom(Strategy):
    def target_weights(self, prices, rb):
        me = prices.resample("ME").last()
        tr = me / me.shift(12) - 1
        rows = []
        for d in rb:
            t = tr.loc[:d]
            on = len(t) and not t.iloc[-1][["VFINX", "CASH"]].isna().any() and t.iloc[-1]["VFINX"] > t.iloc[-1]["CASH"]
            rows.append({"VFINX": 1.0} if on else {"VBMFX": 1.0})
        return pd.DataFrame(rows, index=rb).fillna(0.0)


def main():
    px = build()
    EVAL = "1987-01-01"
    print("data:", px.index[0].date(), "->", px.index[-1].date())
    kwD = dict(benchmark="VFINX", rebalance="D", cost_bps=COST, start=EVAL)
    kwM = dict(benchmark="VFINX", rebalance="M", cost_bps=COST, start=EVAL)

    d1 = Backtest(px, DonchianBreakout(), **kwD).run()
    d2 = Backtest(px, DonchianBreakout(name="Donchian 55/20", params={"entry": 55, "exit": 20}), **kwD).run()
    dv = Backtest(px, DonchianVolSized(), **kwD).run()
    sma = Backtest(px, SmaFilter(name="10-month SMA filter", params={}), **kwM).run()
    mom = Backtest(px, AbsMom(name="12-month absolute momentum", params={}), **kwM).run()
    bh = Backtest(px, BH(name="S&P 500 buy & hold", params={"t": "VFINX"}), **{**kwM, "cost_bps": 0}).run()
    sf = Backtest(px, SixtyForty(name="60/40", params={}), **kwM).run()
    d1.save(OUT / "donchian_main.json")

    # signal stats
    rb = rebalance_calendar(px.index, "D"); rb = rb[rb >= pd.Timestamp(EVAL)]
    st1 = _donchian_state(px["VFINX"], 20, 10).reindex(rb)
    st2 = _donchian_state(px["VFINX"], 55, 20).reindex(rb)
    yrs = len(rb) / 252
    sig = {
        "days": int(len(rb)), "years": round(yrs, 1),
        "s1_time_in_market": round(float(st1.mean()), 4),
        "s2_time_in_market": round(float(st2.mean()), 4),
        "s1_switches": int((st1 != st1.shift()).sum() - 1),
        "s2_switches": int((st2 != st2.shift()).sum() - 1),
        "s1_switches_per_year": round(float((st1 != st1.shift()).sum() - 1) / yrs, 1),
        "s2_switches_per_year": round(float((st2 != st2.shift()).sum() - 1) / yrs, 1),
        "s1_avg_holding_days": None,  # filled below
        "s2_avg_holding_days": None,
    }
    # how many breakouts were profitable 20 days later?
    fwd20 = px["VFINX"].pct_change(20).shift(-20).reindex(rb)
    st1b = st1.astype(bool)
    ent1 = st1b & ~st1b.shift(1, fill_value=False).astype(bool)
    st2b = st2.astype(bool)
    ent2 = st2b & ~st2b.shift(1, fill_value=False).astype(bool)
    sig["s1_avg_holding_days"] = round(float(st1b.sum() / max(int(ent1.sum()), 1)), 1)
    sig["s2_avg_holding_days"] = round(float(st2b.sum() / max(int(ent2.sum()), 1)), 1)
    sig["s2_entries"] = int(ent2.sum())
    sig["s1_entries"] = int(ent1.sum())
    sig["s1_pct_entries_up_20d"] = round(float((fwd20[ent1] > 0).mean()), 4)
    sig["s1_avg_fwd20_after_entry"] = round(float(fwd20[ent1].mean()), 5)
    sig["baseline_pct_up_20d"] = round(float((fwd20 > 0).mean()), 4)
    sig["baseline_avg_fwd20"] = round(float(fwd20.mean()), 5)

    # parameter grid
    rows = []
    for e in [10, 20, 40, 55, 100, 200]:
        for x in [5, 10, 20, 50]:
            if x >= e: continue
            r = Backtest(px, DonchianBreakout(params={"entry": e, "exit": x}), **kwD).run()
            rows.append({"entry": e, "exit": x, **{k: r.metrics[k] for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]}})
    grid = pd.DataFrame(rows)

    costs = pd.DataFrame([{"cost_bps": c, **{k: Backtest(px, DonchianBreakout(), **{**kwD, "cost_bps": c}).run().metrics[k]
                          for k in ["cagr", "sharpe", "max_drawdown"]}} for c in [0, 5, 10, 25, 50]])
    io = in_vs_out_of_sample(px, DonchianBreakout(), split="2003-01-01", **kwD)
    wf = walk_forward(px, DonchianBreakout(), {"entry": [10, 20, 40, 55, 100, 200]}, train_years=5, test_years=1,
                      first_test_start="1992-01-01", benchmark="VFINX", rebalance="D", cost_bps=COST)

    # ---- the diversification test: same rule on a basket
    tick = ["SPY", "EFA", "TLT", "GLD", "DBC", "VNQ"]
    bpx = load_prices(tick, start="2000-01-01").dropna()
    bstart = str(bpx.index[0].date())
    bcash = cash_index("2000-01-01")
    bpx = bpx.join(bcash, how="left"); bpx["CASH"] = bpx["CASH"].ffill()
    bpx = bpx.dropna()

    class BasketDonchian(Strategy):
        def target_weights(self, prices, rb):
            ts = self.params["tickers"]; e, x = self.params["entry"], self.params["exit"]
            states = pd.DataFrame({t: _donchian_state(prices[t], e, x).reindex(rb).astype(bool) for t in ts})
            n_long = states.sum(axis=1)
            w = pd.DataFrame(0.0, index=rb, columns=prices.columns)
            for t in ts:
                # equal weight across whichever assets are trending; fully invested when any are
                w[t] = np.where(n_long > 0, states[t].astype(float) / n_long.replace(0, 1), 0.0)
            w["CASH"] = 1.0 - w[ts].sum(axis=1)
            return w

    kwB = dict(benchmark="SPY", rebalance="D", cost_bps=COST, start=bstart)
    basket = Backtest(bpx, BasketDonchian(name="Donchian 20/10 on a 6-asset basket",
                                          params={"tickers": tick, "entry": 20, "exit": 10}), **kwB).run()
    single = Backtest(bpx, BasketDonchian(name="Donchian 20/10 on SPY only",
                                          params={"tickers": ["SPY"], "entry": 20, "exit": 10}), **kwB).run()
    spy_bh = Backtest(bpx, BH(name="SPY buy & hold", params={"t": "SPY"}), **{**kwB, "cost_bps": 0, "rebalance": "M"}).run()

    eps = {"Dot-com bust": ("2000-03-24", "2002-10-09"), "GFC": ("2007-10-09", "2009-03-09"),
           "2011 Euro crisis": ("2011-05-02", "2011-10-03"), "2015-16 correction": ("2015-05-21", "2016-02-11"),
           "2018 Q4": ("2018-09-20", "2018-12-24"), "COVID crash": ("2020-02-19", "2020-03-23"),
           "COVID rebound": ("2020-03-23", "2020-12-31"), "2022 bear": ("2022-01-03", "2022-10-12"),
           "2023-24 AI bull": ("2023-01-03", "2024-12-31"), "2025 tariff shock": ("2025-02-19", "2025-04-08")}
    ep = [{"episode": n,
           "donchian": round(float((1 + d1.daily_returns.loc[a:b]).prod() - 1), 4),
           "sma": round(float((1 + sma.daily_returns.loc[a:b]).prod() - 1), 4),
           "momentum": round(float((1 + mom.daily_returns.loc[a:b]).prod() - 1), 4),
           "sp500": round(float((1 + px["VFINX"].pct_change().loc[a:b]).prod() - 1), 4)} for n, (a, b) in eps.items()]

    S = {"donchian_20_10": d1.metrics, "donchian_55_20": d2.metrics, "donchian_vol_sized": dv.metrics,
         "sma": sma.metrics, "momentum": mom.metrics, "buy_hold": bh.metrics, "sixty_forty": sf.metrics,
         "benchmark": d1.benchmark_metrics, "donchian_extended": d1.extended,
         "signals": sig, "grid": grid.to_dict(orient="records"), "cost_sensitivity": costs.to_dict(orient="records"),
         "in_out_sample": io, "walk_forward": wf.to_dict(orient="records"), "episodes": ep,
         "drawdowns": d1.drawdowns, "yearly": d1.yearly,
         "basket": {"start": bstart, "tickers": tick, "basket": basket.metrics,
                    "single_spy": single.metrics, "spy_buy_hold": spy_bh.metrics,
                    "benchmark": basket.benchmark_metrics}}
    (OUT / "donchian_summary.json").write_text(json.dumps(S, indent=2, default=str))

    pd.DataFrame({"Donchian": d1.equity, "Donchian55": d2.equity, "VolSized": dv.equity,
                  "SMA": sma.equity, "Momentum": mom.equity, "SP500": d1.benchmark_equity, "SixtyForty": sf.equity,
                  "D_dd": d1.drawdown, "SP_dd": d1.benchmark_equity / d1.benchmark_equity.cummax() - 1
                  }).to_csv(OUT / "donchian_series.csv")
    pd.DataFrame({"Basket": basket.equity, "SingleSPY": single.equity, "SPY": basket.benchmark_equity}).to_csv(OUT / "basket_series.csv")
    pd.DataFrame({"in_market": st1.astype(int)}).to_csv(OUT / "signals.csv")

    for k in ["donchian_20_10", "donchian_55_20", "donchian_vol_sized", "sma", "momentum", "buy_hold", "sixty_forty"]:
        m = S[k]; print(f"{k:22s} CAGR {m['cagr']:.4f}  Sharpe {m['sharpe']:.3f}  DD {m['max_drawdown']:.4f}  turn {m['annual_turnover']:.2f}")
    print(json.dumps(sig, indent=1))
    print(grid.to_string()); print(costs.to_string())
    print("IO in ", {k: io["in_sample"][k] for k in ["start","end","cagr","sharpe","max_drawdown"]})
    print("IO out", {k: io["out_of_sample"][k] for k in ["start","end","cagr","sharpe","max_drawdown"]})
    print("bench", io["benchmark_in_sample"], io["benchmark_out_of_sample"])
    g = lambda c: round(float(np.prod([1 + r[c] for r in S["walk_forward"]]) ** (1/len(S["walk_forward"])) - 1), 4)
    print("WF oos", g("oos_return"), "default", g("default_return"), "bench", g("benchmark_return"), "n", len(wf))
    print("BASKET from", bstart); [print(" ", k, {kk: round(v[kk],4) for kk in ["cagr","sharpe","max_drawdown","annual_turnover"] if kk in v}) for k,v in S["basket"].items() if isinstance(v, dict)]
    print(json.dumps(ep, indent=1))


if __name__ == "__main__":
    main()
