"""The 10-month moving average trend filter (Faber, 2007).

Rules, evaluated on the last trading day of each month, executed next close:
  1. Compare the equity index's month-end close to its trailing `lookback`-month
     simple moving average of month-end closes.
  2. Above the average -> hold 100% equities. At or below -> hold 100% of the
     defensive asset (bonds by default, or T-bills).
  3. Hold until the next month-end. No leverage, no shorting.

Params
  risky     : ticker of the equity sleeve
  safe      : ticker held when the filter is off
  lookback  : months in the moving average (default 10, Faber's published rule)
  band      : optional buffer, e.g. 0.02 requires price > SMA * 1.02 to enter
              and price < SMA * 0.98 to exit (hysteresis to cut whipsaw)
"""
from __future__ import annotations

import pandas as pd

from strategylab.strategy import Strategy


class SmaTrendFilter(Strategy):
    def __init__(self, name="10-month SMA filter", params=None):
        base = {"risky": "VFINX", "safe": "VBMFX", "lookback": 10, "band": 0.0}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"]]

    def signals(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.Series:
        """Boolean 'risk-on' series indexed by rebalance date (exposed for comparison work)."""
        p = self.params
        lb = int(p["lookback"])
        band = float(p["band"])
        me = prices.resample("ME").last()
        sma = me[p["risky"]].rolling(lb).mean()
        px = me[p["risky"]]
        on = []
        state = False
        for d in rebalance_dates:
            row = px.loc[:d]
            s = sma.loc[:d]
            if len(s) == 0 or pd.isna(s.iloc[-1]):
                on.append(False); continue
            price, avg = float(row.iloc[-1]), float(s.iloc[-1])
            if band > 0:
                if not state and price > avg * (1 + band):
                    state = True
                elif state and price < avg * (1 - band):
                    state = False
            else:
                state = price > avg
            on.append(state)
        return pd.Series(on, index=rebalance_dates, name="risk_on")

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        on = self.signals(prices, rebalance_dates)
        rows = []
        for d in rebalance_dates:
            w = {c: 0.0 for c in prices.columns}
            w[p["risky"] if on.loc[d] else p["safe"]] = 1.0
            rows.append(w)
        return pd.DataFrame(rows, index=rebalance_dates)


class AbsoluteMomentum(Strategy):
    """GEM's absolute-momentum half, for head-to-head comparison.

    Risk-on when the equity index's trailing `lookback`-month return beats the
    T-bill return over the same window.
    """

    def __init__(self, name="12-month absolute momentum", params=None):
        base = {"risky": "VFINX", "safe": "VBMFX", "cash": "CASH", "lookback": 12}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"], p["cash"]]

    def signals(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.Series:
        p = self.params
        lb = int(p["lookback"])
        me = prices.resample("ME").last()
        trail = me / me.shift(lb) - 1
        on = []
        for d in rebalance_dates:
            t = trail.loc[:d]
            if len(t) == 0 or t.iloc[-1][[p["risky"], p["cash"]]].isna().any():
                on.append(False); continue
            r = t.iloc[-1]
            on.append(bool(r[p["risky"]] > r[p["cash"]]))
        return pd.Series(on, index=rebalance_dates, name="risk_on")

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        on = self.signals(prices, rebalance_dates)
        rows = []
        for d in rebalance_dates:
            w = {c: 0.0 for c in prices.columns}
            w[p["risky"] if on.loc[d] else p["safe"]] = 1.0
            rows.append(w)
        return pd.DataFrame(rows, index=rebalance_dates)


class CombinedFilter(Strategy):
    """Both filters together: 'and' requires agreement to be risk-on, 'or' needs either."""

    def __init__(self, name="Combined filter", params=None):
        base = {"risky": "VFINX", "safe": "VBMFX", "cash": "CASH",
                "sma_lookback": 10, "mom_lookback": 12, "mode": "and"}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"], p["cash"]]

    def signals(self, prices, rebalance_dates):
        p = self.params
        a = SmaTrendFilter(params={"risky": p["risky"], "safe": p["safe"], "lookback": p["sma_lookback"]}).signals(prices, rebalance_dates)
        b = AbsoluteMomentum(params={"risky": p["risky"], "safe": p["safe"], "cash": p["cash"], "lookback": p["mom_lookback"]}).signals(prices, rebalance_dates)
        return (a & b) if p["mode"] == "and" else (a | b)

    def target_weights(self, prices, rebalance_dates):
        p = self.params
        on = self.signals(prices, rebalance_dates)
        rows = []
        for d in rebalance_dates:
            w = {c: 0.0 for c in prices.columns}
            w[p["risky"] if on.loc[d] else p["safe"]] = 1.0
            rows.append(w)
        return pd.DataFrame(rows, index=rebalance_dates)
