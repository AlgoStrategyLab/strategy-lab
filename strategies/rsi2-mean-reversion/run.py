"""Article #4: RSI(2) mean reversion on the S&P 500 — the opposite bet to the series so far."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).parent))

from strategylab import Backtest, in_vs_out_of_sample, load_prices, walk_forward  # noqa: E402
from strategylab.engine import rebalance_calendar  # noqa: E402
from strategylab.strategy import Strategy  # noqa: E402
from strategy import RSI2MeanReversion, rsi_state, wilder_rsi  # noqa: E402

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)
COST = 10
EVAL = "1987-01-01"
WARMUP = "1980-01-01"          # 200-day SMA needs a year; take seven to be safe
SPLIT = "2009-01-01"           # Connors & Alvarez published in 2008


def cash_index(start):
    irx = load_prices(["^IRX"], start=start)["^IRX"].ffill().clip(lower=0)
    return (1 + (irx / 100.0 / 252.0).shift(1).fillna(0)).cumprod().rename("CASH")


def build():
    px = load_prices(["VFINX", "VBMFX"], start=WARMUP).join(cash_index(WARMUP), how="left")
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


def trade_stats(state: pd.Series, px: pd.Series) -> dict:
    """Per-trade statistics. A trade runs from the first in-market close to the exit close."""
    s = state.astype(bool)
    entries = s & ~s.shift(1, fill_value=False).astype(bool)
    exits = (~s) & s.shift(1, fill_value=False).astype(bool)
    e_idx = list(state.index[entries])
    x_idx = list(state.index[exits])
    if len(x_idx) < len(e_idx):
        x_idx.append(state.index[-1])

    rets, holds = [], []
    for a, b in zip(e_idx, x_idx):
        # entered at the close after the signal, exited at the close after the exit signal
        try:
            ia = px.index.get_loc(a) + 1
            ib = px.index.get_loc(b) + 1
        except KeyError:
            continue
        if ib >= len(px) or ia >= len(px) or ib <= ia:
            continue
        rets.append(float(px.iloc[ib] / px.iloc[ia] - 1))
        holds.append(int(ib - ia))

    r = np.array(rets) if rets else np.array([0.0])
    h = np.array(holds) if holds else np.array([0])
    wins = r[r > 0]
    losses = r[r <= 0]
    return {
        "trades": int(len(rets)),
        "trades_per_year": round(len(rets) / (len(state) / 252), 1),
        "avg_holding_days": round(float(h.mean()), 2),
        "median_holding_days": float(np.median(h)),
        "max_holding_days": int(h.max()),
        "time_in_market": round(float(s.mean()), 4),
        "win_rate": round(float((r > 0).mean()), 4),
        "avg_trade": round(float(r.mean()), 5),
        "avg_win": round(float(wins.mean()), 5) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 5) if len(losses) else None,
        "best_trade": round(float(r.max()), 4),
        "worst_trade": round(float(r.min()), 4),
        "payoff_ratio": round(float(abs(wins.mean() / losses.mean())), 3) if len(wins) and len(losses) and losses.mean() != 0 else None,
    }


def exposure_adjusted(result, risky: str = "VFINX") -> dict:
    """What the strategy earns per day it is actually exposed.

    Comparing a strategy that is invested 6% of the time with buy-and-hold on CAGR
    alone flatters buy-and-hold and tells you almost nothing about the signal. This
    annualises the strategy's return over its days in market only.

    The mask comes from the engine's own weight record, not from the signal series.
    ``weights`` holds the position at the *end* of each day, so day i+1's return is
    earned by day i's weights. Masking with the unshifted signal instead charges the
    strategy for the sharp down day that triggered the entry — which it never owned,
    since fills happen at the next close. That error turns this strategy's return
    negative, so it is worth getting right.
    """
    daily = result.daily_returns
    s = (result.weights[risky].shift(1).fillna(0.0) > 1e-9).reindex(daily.index).fillna(False)
    in_days = int(s.sum())
    if in_days == 0:
        return {}
    growth = float((1 + daily[s]).prod())
    return {
        "days_in_market": in_days,
        "total_days": int(len(daily)),
        "exposure": round(in_days / len(daily), 4),
        "growth_while_invested": round(growth, 4),
        "annualised_while_invested": round(growth ** (252.0 / in_days) - 1, 4),
        "avg_daily_return_in_market": round(float(daily[s].mean()), 6),
        "avg_daily_return_out": round(float(daily[~s].mean()), 6),
    }


def main():
    px = build()
    print("data:", px.index[0].date(), "->", px.index[-1].date())
    kwD = dict(benchmark="VFINX", rebalance="D", cost_bps=COST, start=EVAL)
    kwM = dict(benchmark="VFINX", rebalance="M", cost_bps=COST, start=EVAL)

    base = RSI2MeanReversion()
    main_r = Backtest(px, base, **kwD).run()
    main_r.save(OUT / "rsi2_main.json")

    # --- variants that isolate each component -----------------------------
    no_trend = Backtest(px, RSI2MeanReversion(
        name="RSI(2) without the 200-day filter", params={"trend_sma": 0}), **kwD).run()

    class TrendOnly(Strategy):
        """Hold equities whenever price is above its 200-day average. The regime filter
        on its own, so the RSI entry can be judged against it rather than against cash."""
        def target_weights(self, prices, rb):
            on = (prices["VFINX"] > prices["VFINX"].rolling(200).mean()).reindex(rb).ffill().fillna(False)
            w = pd.DataFrame(0.0, index=rb, columns=prices.columns)
            w.loc[on.values, "VFINX"] = 1.0
            w.loc[~on.values, "CASH"] = 1.0
            return w

    filt = Backtest(px, TrendOnly(name="200-day SMA filter, always invested"), **kwD).run()
    exit_rsi = Backtest(px, RSI2MeanReversion(
        name="RSI(2), exit on RSI > 65", params={"exit_sma": 0, "exit_rsi": 65.0}), **kwD).run()
    hold5 = Backtest(px, RSI2MeanReversion(
        name="RSI(2), fixed 5-day hold", params={"exit_sma": 0, "exit_rsi": 0.0, "max_hold": 5}), **kwD).run()
    bonds = Backtest(px, RSI2MeanReversion(
        name="RSI(2), parked in bonds while flat", params={"safe": "VBMFX"}), **kwD).run()

    bh = Backtest(px, BH(name="S&P 500 buy & hold", params={"t": "VFINX"}), **{**kwM, "cost_bps": 0}).run()
    sf = Backtest(px, SixtyForty(name="60/40"), **kwM).run()
    sma = Backtest(px, SmaFilter(name="10-month SMA filter"), **kwM).run()

    # --- signal and trade behaviour ---------------------------------------
    rb = rebalance_calendar(px.index, "D")
    rb = rb[rb >= pd.Timestamp(EVAL)]
    state = base.signals(px, rb)
    rsi = wilder_rsi(px["VFINX"], 2).reindex(rb)

    stats = trade_stats(state, px["VFINX"])
    exposure = exposure_adjusted(main_r)

    # Split the total return into what the cash earned while flat and what the trades
    # earned while invested. The two compound to the headline CAGR exactly.
    yrs = exposure["total_days"] / 252.0
    flat_days = exposure["total_days"] - exposure["days_in_market"]
    cash_growth = (1 + exposure["avg_daily_return_out"]) ** flat_days
    decomposition = {
        "cash_growth": round(float(cash_growth), 4),
        "trade_growth": round(float(exposure["growth_while_invested"]), 4),
        "cash_cagr": round(float(cash_growth ** (1 / yrs) - 1), 5),
        "trade_cagr": round(float(exposure["growth_while_invested"] ** (1 / yrs) - 1), 5),
        "cash_share_of_return": None,
    }
    decomposition["cash_share_of_return"] = round(
        decomposition["cash_cagr"] / (decomposition["cash_cagr"] + decomposition["trade_cagr"]), 4)

    # does a low RSI actually predict anything, or is it the trend filter doing the work?
    fwd5 = px["VFINX"].pct_change(5).shift(-5).reindex(rb)
    above200 = (px["VFINX"] > px["VFINX"].rolling(200).mean()).reindex(rb)
    oversold = rsi < 5
    edge = {
        "baseline_avg_fwd5": round(float(fwd5.mean()), 5),
        "baseline_pct_up_5d": round(float((fwd5 > 0).mean()), 4),
        "after_rsi_below_5_avg_fwd5": round(float(fwd5[oversold].mean()), 5),
        "after_rsi_below_5_pct_up": round(float((fwd5[oversold] > 0).mean()), 4),
        "n_rsi_below_5": int(oversold.sum()),
        "above200_avg_fwd5": round(float(fwd5[above200].mean()), 5),
        "above200_and_oversold_avg_fwd5": round(float(fwd5[above200 & oversold].mean()), 5),
        "above200_and_oversold_pct_up": round(float((fwd5[above200 & oversold] > 0).mean()), 4),
        "n_above200_and_oversold": int((above200 & oversold).sum()),
        "below200_and_oversold_avg_fwd5": round(float(fwd5[(~above200) & oversold].mean()), 5),
        "below200_and_oversold_pct_up": round(float((fwd5[(~above200) & oversold] > 0).mean()), 4),
        "n_below200_and_oversold": int(((~above200) & oversold).sum()),
    }

    # --- parameter grid ----------------------------------------------------
    rows = []
    for period in [2, 3, 4, 5]:
        for ent in [5, 10, 15, 20, 30]:
            r = Backtest(px, RSI2MeanReversion(params={"rsi_period": period, "entry": float(ent)}), **kwD).run()
            rows.append({"rsi_period": period, "entry": ent,
                         **{k: r.metrics[k] for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]},
                         "time_in_market": round(float(RSI2MeanReversion(
                             params={"rsi_period": period, "entry": float(ent)}).signals(px, rb).mean()), 4)})
    grid = pd.DataFrame(rows)

    exits = pd.DataFrame([
        {"exit_rule": "close > SMA(5)", **{k: main_r.metrics[k] for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]}},
        {"exit_rule": "RSI(2) > 65", **{k: exit_rsi.metrics[k] for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]}},
        {"exit_rule": "fixed 5-day hold", **{k: hold5.metrics[k] for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]}},
    ])

    costs = pd.DataFrame([{"cost_bps": c, **{k: Backtest(px, RSI2MeanReversion(), **{**kwD, "cost_bps": c}).run().metrics[k]
                           for k in ["cagr", "sharpe", "max_drawdown"]}} for c in [0, 5, 10, 25, 50, 100]])

    io = in_vs_out_of_sample(px, RSI2MeanReversion(), split=SPLIT, **kwD)
    wf = walk_forward(px, RSI2MeanReversion(), {"entry": [5.0, 10.0, 15.0, 20.0, 30.0]},
                      train_years=5, test_years=1, first_test_start="1992-01-01",
                      benchmark="VFINX", rebalance="D", cost_bps=COST)

    # --- the regime question the series has been building toward -----------
    # Donchian's worst stretch was Jan 1999 -> Mar 2009, caused by chop rather than a crash.
    # If mean reversion is the complement of trend following, this is where it should shine.
    regimes = {
        "Donchian's 14-year drawdown (chop)": ("1999-01-04", "2013-05-31"),
        "Dot-com bust": ("2000-03-24", "2002-10-09"),
        "GFC": ("2007-10-09", "2009-03-09"),
        "2010s low-vol bull": ("2012-01-03", "2019-12-31"),
        "COVID crash": ("2020-02-19", "2020-03-23"),
        "COVID rebound": ("2020-03-23", "2020-12-31"),
        "2022 bear": ("2022-01-03", "2022-10-12"),
        "2023-24 AI bull": ("2023-01-03", "2024-12-31"),
        "2025 tariff shock": ("2025-02-19", "2025-04-08"),
    }
    reg = [{"regime": n,
            "rsi2": round(float((1 + main_r.daily_returns.loc[a:b]).prod() - 1), 4),
            "sma_filter": round(float((1 + sma.daily_returns.loc[a:b]).prod() - 1), 4),
            "sp500": round(float((1 + px["VFINX"].pct_change().loc[a:b]).prod() - 1), 4)}
           for n, (a, b) in regimes.items()]

    S = {
        "main": main_r.metrics,
        "no_trend_filter": no_trend.metrics,
        "trend_filter_only": filt.metrics,
        "exit_on_rsi": exit_rsi.metrics,
        "fixed_5day_hold": hold5.metrics,
        "parked_in_bonds": bonds.metrics,
        "buy_hold": bh.metrics,
        "sixty_forty": sf.metrics,
        "sma_filter_monthly": sma.metrics,
        "benchmark": main_r.benchmark_metrics,
        "main_extended": main_r.extended,
        "benchmark_extended": main_r.benchmark_extended,
        "trades": stats,
        "exposure": exposure,
        "decomposition": decomposition,
        "signal_edge": edge,
        "grid": grid.to_dict(orient="records"),
        "exit_rules": exits.to_dict(orient="records"),
        "cost_sensitivity": costs.to_dict(orient="records"),
        "in_out_sample": io,
        "walk_forward": wf.to_dict(orient="records"),
        "regimes": reg,
        "drawdowns": main_r.drawdowns,
        "yearly": main_r.yearly,
        "config": {"eval_start": EVAL, "split": SPLIT, "cost_bps": COST,
                   "rule": "RSI(2) < 5 with close above the 200-day SMA; exit on close above SMA(5)"},
    }
    (OUT / "rsi2_summary.json").write_text(json.dumps(S, indent=2, default=str))

    pd.DataFrame({"RSI2": main_r.equity, "NoTrend": no_trend.equity, "TrendOnly": filt.equity,
                  "Bonds": bonds.equity, "SMA": sma.equity, "SP500": main_r.benchmark_equity,
                  "SixtyForty": sf.equity, "RSI2_dd": main_r.drawdown,
                  "SP_dd": main_r.benchmark_equity / main_r.benchmark_equity.cummax() - 1}).to_csv(OUT / "rsi2_series.csv")
    pd.DataFrame({"in_market": state.astype(int), "rsi2": rsi}).to_csv(OUT / "signals.csv")

    for k in ["main", "no_trend_filter", "trend_filter_only", "exit_on_rsi", "fixed_5day_hold",
              "parked_in_bonds", "buy_hold", "sixty_forty", "sma_filter_monthly"]:
        m = S[k]
        print(f"{k:22s} CAGR {m['cagr']:.4f}  Sharpe {m['sharpe']:.3f}  DD {m['max_drawdown']:.4f}  turn {m['annual_turnover']:.2f}")
    print("\ntrades:", json.dumps(stats, indent=1))
    print("exposure:", json.dumps(exposure, indent=1))
    print("edge:", json.dumps(edge, indent=1))
    print("\ngrid:\n", grid.to_string())
    print("\nexits:\n", exits.to_string())
    print("\ncosts:\n", costs.to_string())
    print("\nIO in ", {k: io["in_sample"][k] for k in ["start", "end", "cagr", "sharpe", "max_drawdown"]})
    print("IO out", {k: io["out_of_sample"][k] for k in ["start", "end", "cagr", "sharpe", "max_drawdown"]})
    print("bench in/out", io["benchmark_in_sample"]["cagr"], io["benchmark_out_of_sample"]["cagr"])
    print("\nregimes:", json.dumps(reg, indent=1))


if __name__ == "__main__":
    main()
