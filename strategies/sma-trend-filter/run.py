"""Article #2: the 10-month SMA trend filter, head-to-head with 12-month absolute momentum."""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from strategylab import load_prices, Backtest, parameter_sweep, walk_forward, in_vs_out_of_sample
from strategylab.strategy import Strategy
from strategy import SmaTrendFilter, AbsoluteMomentum, CombinedFilter

OUT = Path(__file__).parent / "output"; OUT.mkdir(exist_ok=True)
COST = 10
START = "1972-01-01"      # VFINX starts 1980; we fetch wide and let the data decide
EVAL = "1981-11-01"       # 10 months of SMA warmup after VFINX inception


def cash_index(start):
    irx = load_prices(["^IRX"], start=start)["^IRX"].ffill().clip(lower=0)
    return (1 + (irx / 100.0 / 252.0).shift(1).fillna(0)).cumprod().rename("CASH")


def build(warmup_start="1980-01-01"):
    """Full risky-asset history for signal warmup; the safe asset only bounds the eval window.

    VFINX and the T-bill index go back to 1980, so a 1987 investor really did have ten
    months of moving average available. Slicing them at VBMFX's 1986 inception would make
    the filter undefined through the 1987 rally -- a warmup artifact, not a result.
    """
    px = load_prices(["VFINX", "VBMFX"], start=warmup_start)
    px = px.join(cash_index(warmup_start), how="left")
    px["CASH"] = px["CASH"].ffill()
    px = px[px["VFINX"].notna() & px["CASH"].notna()]
    # VBMFX predates nothing we trade before 1987; backfill so returns are defined, never held
    px["VBMFX"] = px["VBMFX"].ffill().bfill()
    return px


class BuyHold(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{self.params["t"]: 1.0}] * len(rb), index=rb)


def main():
    px = build()
    print("data:", px.index[0].date(), "->", px.index[-1].date())
    eval_start = "1987-01-01"   # VBMFX exists from Dec 1986; SMA warmed up since 1980

    sma = SmaTrendFilter()
    mom = AbsoluteMomentum()
    kw = dict(benchmark="VFINX", rebalance="M", cost_bps=COST, start=eval_start)

    r_sma = Backtest(px, sma, **kw).run()
    r_mom = Backtest(px, mom, **kw).run()
    r_and = Backtest(px, CombinedFilter(params={"mode": "and"}), **kw).run()
    r_or  = Backtest(px, CombinedFilter(params={"mode": "or"}), **kw).run()
    r_bh  = Backtest(px, BuyHold(name="S&P 500 buy & hold", params={"t": "VFINX"}), cost_bps=0, **{k: v for k, v in kw.items() if k != "cost_bps"}).run()
    r_6040 = Backtest(px, type("S", (Strategy,), {"target_weights": lambda s, p, rb: pd.DataFrame([{"VFINX": .6, "VBMFX": .4}] * len(rb), index=rb)})(name="60/40", params={}), **kw).run()
    r_sma.save(OUT / "sma_trend_filter_main.json")

    # ---- signal-level comparison
    from strategylab.engine import rebalance_calendar
    rb = rebalance_calendar(px.index, "M")
    rb = rb[(rb >= pd.Timestamp(eval_start))]
    s_sma = sma.signals(px, rb); s_mom = mom.signals(px, rb)
    agree = (s_sma == s_mom)
    both_on = (s_sma & s_mom).mean(); both_off = ((~s_sma) & (~s_mom)).mean()
    sma_only = (s_sma & ~s_mom); mom_only = (s_mom & ~s_sma)

    # next-month equity return following each signal state
    me = px.resample("ME").last()
    fwd = (me["VFINX"].pct_change().shift(-1)).reindex(rb)
    fwd_bond = (me["VBMFX"].pct_change().shift(-1)).reindex(rb)
    comparison = {
        "months": int(len(rb)),
        "agreement_rate": round(float(agree.mean()), 4),
        "both_risk_on": round(float(both_on), 4),
        "both_risk_off": round(float(both_off), 4),
        "sma_on_mom_off": round(float(sma_only.mean()), 4),
        "mom_on_sma_off": round(float(mom_only.mean()), 4),
        "sma_risk_on_pct": round(float(s_sma.mean()), 4),
        "mom_risk_on_pct": round(float(s_mom.mean()), 4),
        "sma_switches": int((s_sma != s_sma.shift()).sum() - 1),
        "mom_switches": int((s_mom != s_mom.shift()).sum() - 1),
        "avg_fwd_equity_return_when_both_on": round(float(fwd[s_sma & s_mom].mean()), 5),
        "avg_fwd_equity_return_when_both_off": round(float(fwd[~s_sma & ~s_mom].mean()), 5),
        "avg_fwd_equity_return_sma_only_on": round(float(fwd[sma_only].mean()), 5) if sma_only.any() else None,
        "avg_fwd_equity_return_mom_only_on": round(float(fwd[mom_only].mean()), 5) if mom_only.any() else None,
        "n_sma_only_on": int(sma_only.sum()), "n_mom_only_on": int(mom_only.sum()),
    }
    # who was right in disagreement months: equity beat bonds next month?
    eq_beat = (fwd > fwd_bond)
    comparison["sma_right_when_disagree"] = round(float(eq_beat[sma_only].mean()), 4) if sma_only.any() else None
    comparison["mom_right_when_disagree"] = round(float(eq_beat[mom_only].mean()), 4) if mom_only.any() else None

    # disagreement episodes (consecutive runs)
    dis = (~agree)
    episodes = []
    run_start = None
    for d, v in dis.items():
        if v and run_start is None: run_start = d
        elif not v and run_start is not None:
            episodes.append((run_start, d)); run_start = None
    if run_start is not None: episodes.append((run_start, dis.index[-1]))
    ep_rows = []
    for a, b in episodes:
        if (b - a).days < 50: continue
        who = "SMA risk-on" if s_sma.loc[a] else "Momentum risk-on"
        eq = float((1 + px["VFINX"].pct_change().loc[a:b]).prod() - 1)
        bd = float((1 + px["VBMFX"].pct_change().loc[a:b]).prod() - 1)
        ep_rows.append({"from": str(a.date()), "to": str(b.date()), "months": round((b - a).days / 30.4),
                        "who_was_in": who, "equities": round(eq, 4), "bonds": round(bd, 4),
                        "right_call": (who == "SMA risk-on") == (eq > bd)})
    ep_rows.sort(key=lambda r: -r["months"])

    # ---- robustness
    sweep = parameter_sweep(px, sma, {"lookback": [6, 8, 10, 12, 14, 16]}, **kw)
    band = parameter_sweep(px, sma, {"band": [0.0, 0.01, 0.02, 0.03, 0.05]}, **kw)
    costs = pd.DataFrame([{"cost_bps": c, **{k: Backtest(px, sma, **{**kw, "cost_bps": c}).run().metrics[k]
                          for k in ["cagr", "sharpe", "max_drawdown", "annual_turnover"]}} for c in [0, 10, 25, 50]])
    io = in_vs_out_of_sample(px, sma, split="2007-01-01", **kw)   # kw carries start=eval_start
    wf = walk_forward(px, sma, {"lookback": [6, 8, 10, 12, 14, 16]}, train_years=5, test_years=1,
                      first_test_start="1992-01-01", benchmark="VFINX", cost_bps=COST)

    # safe-asset variant: T-bills instead of bonds
    r_tbill = Backtest(px, SmaTrendFilter(params={"safe": "CASH"}), **kw).run()

    # episodes
    eps = {
        "Black Monday aftermath (Oct 1987 - Jan 1988)": ("1987-10-01", "1988-01-31"),
        "Dot-com bust (Mar 2000 - Oct 2002)": ("2000-03-24", "2002-10-09"),
        "GFC (Oct 2007 - Mar 2009)": ("2007-10-09", "2009-03-09"),
        "2011 Euro crisis (May - Oct 2011)": ("2011-05-02", "2011-10-03"),
        "2015-16 correction": ("2015-05-21", "2016-02-11"),
        "2018 Q4": ("2018-09-20", "2018-12-24"),
        "COVID crash (Feb - Mar 2020)": ("2020-02-19", "2020-03-23"),
        "COVID rebound (Mar - Dec 2020)": ("2020-03-23", "2020-12-31"),
        "2022 bear": ("2022-01-03", "2022-10-12"),
        "2023-24 AI bull": ("2023-01-03", "2024-12-31"),
        "2025 tariff shock": ("2025-02-19", "2025-04-08"),
    }
    ep2 = []
    for n, (a, b) in eps.items():
        ep2.append({"episode": n,
                    "sma": round(float((1 + r_sma.daily_returns.loc[a:b]).prod() - 1), 4),
                    "momentum": round(float((1 + r_mom.daily_returns.loc[a:b]).prod() - 1), 4),
                    "sp500": round(float((1 + px["VFINX"].pct_change().loc[a:b]).prod() - 1), 4)})

    summary = {
        "sma": r_sma.metrics, "momentum": r_mom.metrics, "combined_and": r_and.metrics,
        "combined_or": r_or.metrics, "buy_hold": r_bh.metrics, "sixty_forty": r_6040.metrics,
        "sma_with_tbills": r_tbill.metrics,
        "sma_extended": r_sma.extended, "momentum_extended": r_mom.extended,
        "benchmark": r_sma.benchmark_metrics,
        "comparison": comparison, "disagreement_episodes": ep_rows,
        "lookback_sweep": sweep.to_dict(orient="records"),
        "band_sweep": band.to_dict(orient="records"),
        "cost_sensitivity": costs.to_dict(orient="records"),
        "in_out_sample": io, "walk_forward": wf.to_dict(orient="records"),
        "episodes": ep2, "drawdowns": r_sma.drawdowns, "yearly": r_sma.yearly,
    }
    (OUT / "sma_trend_filter_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    pd.DataFrame({
        "SMA": r_sma.equity, "Momentum": r_mom.equity, "AND": r_and.equity, "OR": r_or.equity,
        "SP500": r_sma.benchmark_equity, "SixtyForty": r_6040.equity,
        "SMA_dd": r_sma.drawdown, "Mom_dd": r_mom.drawdown,
        "SP500_dd": r_sma.benchmark_equity / r_sma.benchmark_equity.cummax() - 1,
    }).to_csv(OUT / "sma_trend_filter_series.csv")
    pd.DataFrame({"sma_on": s_sma, "mom_on": s_mom}).to_csv(OUT / "signals.csv")

    for k in ["sma", "momentum", "combined_and", "combined_or", "buy_hold", "sixty_forty", "sma_with_tbills"]:
        m = summary[k]
        print(f"{k:16s} CAGR {m['cagr']:.4f}  Sharpe {m['sharpe']:.3f}  MaxDD {m['max_drawdown']:.4f}  turn {m.get('annual_turnover','-')}")
    print(json.dumps(comparison, indent=1))
    print(sweep.to_string()); print(band.to_string()); print(costs.to_string())
    print(json.dumps(io, indent=1, default=str))
    print(json.dumps(ep_rows[:8], indent=1))
    print(json.dumps(ep2, indent=1))
    wfa = lambda c: round(float(np.prod([1 + r[c] for r in wf.to_dict(orient='records')]) ** (1/len(wf)) - 1), 4)
    print("WF oos", wfa("oos_return"), "default", wfa("default_return"), "bench", wfa("benchmark_return"), "n", len(wf))


if __name__ == "__main__":
    main()
