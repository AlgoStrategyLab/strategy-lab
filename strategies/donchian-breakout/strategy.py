"""Donchian channel breakout — the rule the Turtle traders used.

Richard Donchian's channel breakout, as taught to the Turtles by Richard Dennis in 1983:
enter on a new N-day high, exit on a new M-day low. The Turtles ran two systems:
System 1 (20-day entry / 10-day exit) and System 2 (55-day entry / 20-day exit).

This is a long/flat equity-index implementation: the original traded a diversified
basket of futures long AND short, with volatility-based position sizing and pyramiding.
``DonchianVolSized`` adds the sizing piece so the two can be separated.

Params
  risky, safe : tickers
  entry       : lookback (trading days) for the breakout high
  exit        : lookback (trading days) for the exit low
  target_vol  : annualised volatility target for the sized variant (0 = full size)
  vol_window  : trading days used to estimate realised volatility
  max_weight  : cap on the risky weight for the sized variant
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategylab.strategy import Strategy


def _donchian_state(px: pd.Series, entry: int, exit: int) -> pd.Series:
    """Boolean 'in the market' series. Uses only information available at each close."""
    # channels exclude today, so a close is compared with the PRIOR N days
    hi = px.rolling(entry).max().shift(1)
    lo = px.rolling(exit).min().shift(1)
    inmkt = np.zeros(len(px), dtype=bool)
    state = False
    p = px.values; h = hi.values; l = lo.values
    for i in range(len(px)):
        if not state:
            if not np.isnan(h[i]) and p[i] > h[i]:
                state = True
        else:
            if not np.isnan(l[i]) and p[i] < l[i]:
                state = False
        inmkt[i] = state
    return pd.Series(inmkt, index=px.index, name="in_market")


class DonchianBreakout(Strategy):
    def __init__(self, name="Donchian 20/10 breakout", params=None):
        base = {"risky": "VFINX", "safe": "VBMFX", "entry": 20, "exit": 10}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"]]

    def signals(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.Series:
        p = self.params
        st = _donchian_state(prices[p["risky"]], int(p["entry"]), int(p["exit"]))
        return st.reindex(rebalance_dates).ffill().fillna(False).astype(bool)

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        on = self.signals(prices, rebalance_dates)
        w = pd.DataFrame(0.0, index=rebalance_dates, columns=prices.columns)
        w.loc[on.values, p["risky"]] = 1.0
        w.loc[~on.values, p["safe"]] = 1.0
        return w


class DonchianVolSized(Strategy):
    """Same breakout signal, but position size scaled to a volatility target.

    This is the Turtles' actual risk management: size by the market's volatility so each
    position contributes a comparable amount of risk. Remainder goes to the safe asset.
    """

    def __init__(self, name="Donchian 20/10, vol-sized", params=None):
        base = {"risky": "VFINX", "safe": "VBMFX", "entry": 20, "exit": 10,
                "target_vol": 0.15, "vol_window": 20, "max_weight": 1.0}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"]]

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        px = prices[p["risky"]]
        st = _donchian_state(px, int(p["entry"]), int(p["exit"]))
        rv = px.pct_change().rolling(int(p["vol_window"])).std() * np.sqrt(252)
        scale = (float(p["target_vol"]) / rv).clip(upper=float(p["max_weight"])).shift(1)
        on = st.reindex(rebalance_dates).ffill().fillna(False)
        sc = scale.reindex(rebalance_dates).ffill().fillna(0.0)
        wr = (on.astype(float) * sc).clip(0.0, float(p["max_weight"]))
        w = pd.DataFrame(0.0, index=rebalance_dates, columns=prices.columns)
        w[p["risky"]] = wr.values
        w[p["safe"]] = 1.0 - wr.values
        return w
