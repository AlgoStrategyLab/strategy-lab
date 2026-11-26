"""Article #6: volatility targeting, applied to every strategy in the series."""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from strategylab import load_prices, Backtest
from strategylab.engine import rebalance_calendar
from strategylab.strategy import Strategy
from strategy import VolatilityTargeted, realised_vol, pseudo_returns

OUT = Path(__file__).parent / "output"; OUT.mkdir(exist_ok=True)

COST = 10
MARGIN = 150            # bps over the cash rate, a realistic retail margin spread
TARGET = 0.10           # 10% annualised, roughly half the S&P's long-run volatility
LOOKBACK = 60
SPLIT = "2017-01-01"    # Moreira & Muir published in 2017


# --------------------------------------------------------------------------- books
def cash_index(start):
    irx = load_prices(["^IRX"], start=start)["^IRX"].ffill().clip(lower=0)
    return (1 + (irx / 100.0 / 252.0).shift(1).fillna(0)).cumprod().rename("CASH")


def equity_frame(warmup="1980-01-01"):
    px = load_prices(["VFINX", "VBMFX"], start=warmup).join(cash_index(warmup), how="left")
    px["CASH"] = px["CASH"].ffill()
    px = px[px["VFINX"].notna() & px["CASH"].notna()]
    px["VBMFX"] = px["VBMFX"].ffill().bfill()
    return px


def global_frame(start="1996-04-01"):
    px = load_prices(["VFINX", "VGTSX", "VBMFX"], start=start).join(cash_index(start), how="left")
    px["CASH"] = px["CASH"].ffill()
    return px.dropna()


class BuyHold(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{self.params["t"]: 1.0}] * len(rb), index=rb)


class ConstantScale(Strategy):
    """The control: the same average exposure, held constant instead of timed.

    If volatility targeting works only because it holds less on average, this matches
    it. Whatever separates the two is what the timing is worth.
    """
    def target_weights(self, prices, rb):
        base = self.params["base"].target_weights(prices, rb).reindex(columns=prices.columns).fillna(0.0)
        return base * float(self.params["scale"])

    def describe(self):
        return {"name": self.name, "params": {"scale": self.params["scale"]},
                "base": self.params["base"].describe()}


def _load(folder: str, name: str):
    """Import a sibling strategy module under a unique name.

    Every strategy folder has a file called strategy.py, so a plain import would hand
    back whichever one landed on sys.path first — most likely this article's own.
    """
    import importlib.util
    path = Path(__file__).parent.parent / folder / "strategy.py"
    spec = importlib.util.spec_from_file_location(f"_sl_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_books():
    """Every strategy in the series, with the price frame and engine settings its own
    article used, so each base line here reproduces the number that article published."""
    eq, gl = equity_frame(), global_frame()

    sma = _load("sma-trend-filter", "sma")
    dmom = _load("dual-momentum", "dmom")
    donch = _load("donchian-breakout", "donch")
    rsi2 = _load("rsi2-mean-reversion", "rsi2")

    eqkwM = dict(benchmark="VFINX", rebalance="M", start="1981-11-01")
    eqkwD = dict(benchmark="VFINX", rebalance="D", start="1987-01-01")

    return {
        "S&P 500 buy & hold": dict(px=eq, base=BuyHold(name="S&P 500 buy & hold",
                                   params={"t": "VFINX"}), kw=eqkwM),
        "10-month SMA filter": dict(px=eq, base=sma.SmaTrendFilter(), kw=eqkwM),
        "Dual momentum": dict(px=gl, base=dmom.DualMomentum(),
                              kw=dict(benchmark="VFINX", rebalance="M", start="1997-05-01")),
        "Donchian 20/10": dict(px=eq, base=donch.DonchianBreakout(),
                               kw=dict(benchmark="VFINX", rebalance="D", start="1981-11-01")),
        "RSI(2)": dict(px=eq, base=rsi2.RSI2MeanReversion(), kw=eqkwD),
    }, eq, gl


def run_pair(px, base, kw, target=TARGET, lookback=LOOKBACK, method="simple",
             max_scale=1.0, cost=COST, margin=MARGIN):
    """Base strategy and its volatility-targeted version, over the same window."""
    vt = VolatilityTargeted(name=f"{base.name} + vol target", params=dict(
        base=base, target_vol=target, lookback=lookback, method=method, max_scale=max_scale))
    b = Backtest(px, base, cost_bps=cost, **kw).run()
    v = Backtest(px, vt, cost_bps=cost, max_gross=max(max_scale, 1.0), margin_bps=margin, **kw).run()
    return b, v, vt


class ScaleSeries(Strategy):
    """Applies a given sequence of scales to a base strategy, whatever its origin.

    Used for the shuffled control: the same multiset of position sizes, applied on
    the wrong days. If volatility targeting works because volatility clusters — small
    positions landing on the turbulent stretches — then shuffling destroys the effect
    while leaving the distribution of exposures identical.
    """
    def target_weights(self, prices, rb):
        base = self.params["base"].target_weights(prices, rb).reindex(columns=prices.columns).fillna(0.0)
        s = pd.Series(self.params["scales"], index=rb[:len(self.params["scales"])])
        return base.mul(s.reindex(rb).fillna(1.0), axis=0).fillna(0.0)

    def describe(self):
        return {"name": self.name, "params": {"n_scales": len(self.params["scales"])},
                "base": self.params["base"].describe()}


def rb_dates(px, kw):
    """The dates the engine will actually rebalance on, for this frame and settings.

    The scale has to be measured on the same calendar the engine trades on. Reading it
    off the daily weights instead quietly averages a monthly rule over every day it was
    merely held, which is a different number.
    """
    idx = rebalance_calendar(px.index, kw.get("rebalance", "M"))
    lo = pd.Timestamp(kw["start"]) if kw.get("start") else px.index[0]
    hi = pd.Timestamp(kw["end"]) if kw.get("end") else px.index[-1]
    return idx[(idx >= lo) & (idx <= hi)]


def row(label, r, extra=None):
    m = r.metrics
    d = {"name": label, "cagr": m["cagr"], "volatility": m["volatility"], "sharpe": m["sharpe"],
         "max_drawdown": m["max_drawdown"], "annual_turnover": m["annual_turnover"],
         "avg_net_exposure": m["avg_net_exposure"], "time_levered": m.get("time_levered", 0.0),
         "avg_borrowed": m.get("avg_borrowed", 0.0), "sortino": m.get("sortino"),
         "beta": m.get("beta"), "calmar": m.get("calmar")}
    return {**d, **(extra or {})}


def main():
    books, eq, gl = load_books()
    out = {"config": {"cost_bps": COST, "margin_bps": MARGIN, "target_vol": TARGET,
                      "lookback": LOOKBACK, "method": "simple", "split": SPLIT,
                      "execution": "signal at close, fill next close"}}

    # ---------------------------------------------------------------- 1. the layer
    # Every strategy, unmanaged and volatility-targeted, de-risking only (max 1.0x).
    layer, levered, controls, scale_detail = [], [], [], {}
    for label, cfg in books.items():
        b, v, vt = run_pair(cfg["px"], cfg["base"], cfg["kw"])
        s = vt.scales(cfg["px"], rb_dates(cfg["px"], cfg["kw"]))
        avg_scale = float(s["scale"].mean())

        layer.append({**row(label, b), "variant": "base"})
        layer.append({**row(label, v), "variant": "vol target",
                      "avg_scale": round(avg_scale, 4),
                      "d_sharpe": round(v.metrics["sharpe"] - b.metrics["sharpe"], 3),
                      "d_cagr": round(v.metrics["cagr"] - b.metrics["cagr"], 4),
                      "d_vol": round(v.metrics["volatility"] - b.metrics["volatility"], 4),
                      "d_maxdd": round(v.metrics["max_drawdown"] - b.metrics["max_drawdown"], 4)})

        # the control: same average exposure, never timed
        c = Backtest(cfg["px"], ConstantScale(name=f"{label} at {avg_scale:.2f}x",
                     params={"base": cfg["base"], "scale": avg_scale}),
                     cost_bps=COST, **cfg["kw"]).run()
        controls.append({**row(label, c), "variant": "constant scale", "scale": round(avg_scale, 4),
                         "d_sharpe_vs_timed": round(c.metrics["sharpe"] - v.metrics["sharpe"], 3)})

        # with leverage allowed, financed at the cash rate plus a margin spread
        bl, vl, vtl = run_pair(cfg["px"], cfg["base"], cfg["kw"], max_scale=2.0)
        levered.append({**row(label, vl), "variant": "vol target, 2x cap",
                        "d_sharpe_vs_base": round(vl.metrics["sharpe"] - b.metrics["sharpe"], 3),
                        "d_cagr_vs_base": round(vl.metrics["cagr"] - b.metrics["cagr"], 4)})

        scale_detail[label] = {
            "avg_scale": round(avg_scale, 4),
            "min_scale": round(float(s["scale"].min()), 4),
            "p05_scale": round(float(s["scale"].quantile(0.05)), 4),
            "median_scale": round(float(s["scale"].median()), 4),
            "share_below_half": round(float((s["scale"] < 0.5).mean()), 4),
            "share_at_cap": round(float((s["scale"] >= 0.999).mean()), 4),
            "median_realised_vol": round(float(s["realised_vol"].median()), 4),
        }
        print(f"{label:24s} base S {b.metrics['sharpe']:+.3f} -> vt S {v.metrics['sharpe']:+.3f} "
              f"(2x {vl.metrics['sharpe']:+.3f}, const {c.metrics['sharpe']:+.3f}) scale {avg_scale:.2f}")

    out["layer"] = layer
    out["controls"] = controls
    out["levered"] = levered
    out["scales"] = scale_detail

    # primary subject for the headline: the layer on plain buy & hold, longest history
    pxe = books["S&P 500 buy & hold"]["px"]; bh = books["S&P 500 buy & hold"]["base"]
    kwM = books["S&P 500 buy & hold"]["kw"]
    base_r, main_r, main_vt = run_pair(pxe, bh, kwM)
    out["main"] = main_r.metrics
    out["main_extended"] = main_r.extended
    out["base"] = base_r.metrics
    out["benchmark"] = base_r.benchmark_metrics
    main_r.save(OUT / "voltarget_main.json")
    print("MAIN", json.dumps({k: out["main"][k] for k in
          ["cagr", "volatility", "sharpe", "max_drawdown", "annual_turnover"]}, indent=1))

    def dd(e):
        return e / e.cummax() - 1.0
    pd.DataFrame({"VT": main_r.equity, "SP500": main_r.benchmark_equity, "Base": base_r.equity,
                  "VT_dd": dd(main_r.equity), "SP_dd": dd(main_r.benchmark_equity),
                  "Base_dd": dd(base_r.equity)}).to_csv(OUT / "voltarget_series.csv")

    s = main_vt.scales(pxe, rb_dates(pxe, kwM))
    s.to_csv(OUT / "scales.csv")

    with open(OUT / "voltarget_summary.json", "w") as f:
        json.dump(out, f, indent=2, default=float)
    return out, books, pxe, bh, kwM


def extras(out, books, pxe, bh, kwM, base_r, main_r, main_vt):
    """Everything that probes why the layer does what it does."""
    rng = np.random.default_rng(20261125)
    rb = rb_dates(pxe, kwM)
    s = main_vt.scales(pxe, rb)["scale"]

    # ---- 2. shuffled timing: same sizes, wrong days
    shuffled, shuf_curves = [], {}
    for k in range(5):
        vals = rng.permutation(s.dropna().values)
        r = Backtest(pxe, ScaleSeries(name=f"shuffled {k+1}",
                     params={"base": bh, "scales": vals}), cost_bps=COST, **kwM).run()
        shuffled.append(row(f"shuffled draw {k+1}", r))
        shuf_curves[f"Shuffled {k+1}"] = r.equity
    out["shuffled"] = shuffled
    shuf_curves["Timed"] = main_r.equity
    shuf_curves["Base"] = base_r.equity
    pd.DataFrame(shuf_curves).to_csv(OUT / "shuffled_curves.csv")
    out["shuffled_mean"] = {k: round(float(np.mean([d[k] for d in shuffled])), 4)
                            for k in ["cagr", "volatility", "sharpe", "max_drawdown"]}

    # ---- 3. parameter sweeps on the primary subject
    out["target_sweep"] = [
        {"target_vol": tv, **{k: v for k, v in run_pair(pxe, bh, kwM, target=tv)[1].metrics.items()
                              if k in ("cagr", "volatility", "sharpe", "max_drawdown", "annual_turnover")}}
        for tv in [0.06, 0.08, 0.10, 0.12, 0.15, 0.20]]
    out["lookback_sweep"] = [
        {"lookback": lb, **{k: v for k, v in run_pair(pxe, bh, kwM, lookback=lb)[1].metrics.items()
                            if k in ("cagr", "volatility", "sharpe", "max_drawdown", "annual_turnover")}}
        for lb in [20, 40, 60, 90, 120, 250]]
    out["method_sweep"] = [
        {"method": m, **{k: v for k, v in run_pair(pxe, bh, kwM, method=m)[1].metrics.items()
                         if k in ("cagr", "volatility", "sharpe", "max_drawdown", "annual_turnover")}}
        for m in ["simple", "ewma"]]
    out["cap_sweep"] = [
        {"max_scale": c, **{k: v for k, v in run_pair(pxe, bh, kwM, max_scale=c)[1].metrics.items()
                            if k in ("cagr", "volatility", "sharpe", "max_drawdown", "annual_turnover",
                                     "time_levered", "avg_borrowed", "annual_margin_cost")}}
        for c in [1.0, 1.25, 1.5, 2.0, 3.0]]

    # ---- 4. what it costs to run
    out["cost_sweep"] = [
        {"cost_bps": c, **{k: v for k, v in run_pair(pxe, bh, kwM, cost=c)[1].metrics.items()
                           if k in ("cagr", "sharpe", "max_drawdown")},
         "base_cagr": Backtest(pxe, bh, cost_bps=c, **kwM).run().metrics["cagr"]}
        for c in [0, 5, 10, 25, 50]]
    out["margin_sweep"] = [
        {"margin_bps": mb, **{k: v for k, v in run_pair(pxe, bh, kwM, max_scale=2.0, margin=mb)[1].metrics.items()
                              if k in ("cagr", "sharpe", "max_drawdown", "annual_margin_cost")}}
        for mb in [0, 75, 150, 300, 500]]

    # ---- 5. before and after Moreira & Muir
    io = {}
    for tag, (a, b) in {"in_sample": ("1981-11-01", SPLIT),
                        "out_of_sample": (SPLIT, None)}.items():
        kw = {**kwM, "start": a, **({"end": b} if b else {})}
        bb, vv, _ = run_pair(pxe, bh, kw)
        io[tag] = {"base_cagr": bb.metrics["cagr"], "base_sharpe": bb.metrics["sharpe"],
                   "vt_cagr": vv.metrics["cagr"], "vt_sharpe": vv.metrics["sharpe"],
                   "d_sharpe": round(vv.metrics["sharpe"] - bb.metrics["sharpe"], 3),
                   "start": a, "end": b or str(pxe.index[-1].date())}
    out["in_out_sample"] = io

    # ---- 6. episodes
    EP = [("Dot-com bust", "2000-03-24", "2002-10-09"), ("2003-07 bull", "2002-10-10", "2007-10-09"),
          ("Financial crisis", "2007-10-10", "2009-03-09"), ("2010s bull", "2009-03-10", "2020-02-19"),
          ("COVID crash", "2020-02-20", "2020-03-23"), ("2022 bear", "2022-01-04", "2022-10-12"),
          ("2023-26 recovery", "2022-10-13", None)]
    eqd = {"vt": main_r.equity, "base": base_r.equity, "sp500": base_r.benchmark_equity}
    eps = []
    for name, a, b in EP:
        rec = {"name": name, "start": a, "end": b or str(main_r.equity.index[-1].date())}
        for k, ser in eqd.items():
            w = ser.loc[a:b] if b else ser.loc[a:]
            rec[k] = round(float(w.iloc[-1] / w.iloc[0] - 1), 4) if len(w) > 1 else None
        # exposure carried through the episode
        sw = s.loc[a:b] if b else s.loc[a:]
        rec["avg_scale"] = round(float(sw.mean()), 3) if len(sw) else None
        eps.append(rec)
    out["episodes"] = eps

    # ---- 7. the scale itself, for the charts
    full = main_vt.scales(pxe, rb)
    out["scale_stats"] = {
        "mean": round(float(full["scale"].mean()), 4),
        "median": round(float(full["scale"].median()), 4),
        "min": round(float(full["scale"].min()), 4),
        "share_at_cap": round(float((full["scale"] >= 0.999).mean()), 4),
        "share_below_half": round(float((full["scale"] < 0.5).mean()), 4),
        "share_below_quarter": round(float((full["scale"] < 0.25).mean()), 4),
        "median_realised_vol": round(float(full["realised_vol"].median()), 4),
        "p95_realised_vol": round(float(full["realised_vol"].quantile(0.95)), 4),
    }
    # does last month's vol predict this month's? the premise, stated as a number
    pr = pseudo_returns(bh.target_weights(pxe, pd.DatetimeIndex(pxe.index)).reindex(
        pxe.index).ffill().fillna(0.0), pxe.pct_change().fillna(0.0))
    v = realised_vol(pr, LOOKBACK).dropna()
    nxt = realised_vol(pr, LOOKBACK).shift(-LOOKBACK).dropna()
    j = pd.concat([v.rename("now"), nxt.rename("next")], axis=1).dropna()
    out["vol_persistence"] = {
        "corr_next_60d": round(float(j["now"].corr(j["next"])), 4),
        "rank_corr": round(float(j["now"].corr(j["next"], method="spearman")), 4),
        "corr_return_next_60d": round(float(j["now"].corr(
            pr.rolling(LOOKBACK).mean().shift(-LOOKBACK).reindex(j.index).fillna(0))), 4),
        "n": int(len(j)),
    }
    return out


if __name__ == "__main__":
    out, books, pxe, bh, kwM = main()
    base_r, main_r, main_vt = run_pair(pxe, bh, kwM)
    out = extras(out, books, pxe, bh, kwM, base_r, main_r, main_vt)
    with open(OUT / "voltarget_summary.json", "w") as f:
        json.dump(out, f, indent=2, default=float)
    print("\nvol persistence", out["vol_persistence"])
    print("shuffled mean  ", out["shuffled_mean"])
    print("scale stats    ", out["scale_stats"])
