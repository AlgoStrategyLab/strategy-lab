"""RSI(2) mean reversion — buying weakness inside an uptrend.

Larry Connors and Cesar Alvarez popularised this in *Short Term Trading Strategies
That Work* (2008): with price above its 200-day moving average, buy when a 2-period
RSI drops below a low threshold, and sell once price closes back above a short moving
average. It is the opposite bet to every strategy tested in this series so far —
trend systems buy strength and hold for months, this buys weakness and holds for days.

The interesting structural feature is that it is out of the market most of the time.
That makes a headline CAGR comparison with buy-and-hold close to meaningless, so the
run script reports return per day of exposure alongside it.

Params
  risky, safe   : tickers; ``safe`` is where capital sits while flat
  rsi_period    : RSI lookback in trading days (2 in the published rule)
  entry         : enter when RSI closes below this
  exit_rsi      : exit when RSI closes above this (set 0 to disable)
  exit_sma      : exit when price closes above this SMA (set 0 to disable)
  trend_sma     : regime filter; only take entries with price above this SMA (0 disables)
  max_hold      : force an exit after this many days (0 disables)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategylab.strategy import Strategy


def wilder_rsi(px: pd.Series, n: int) -> pd.Series:
    """Wilder's RSI. At n=2 the smoothing constant is 1/2, so it reacts almost at once.

    A run of only-up closes leaves average loss at zero; RSI is 100 there by definition,
    and 0 for the mirror case. Returning NaN would silently suppress signals instead.
    """
    delta = px.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    avg_up = up.ewm(alpha=1.0 / n, adjust=False).mean()
    avg_down = down.ewm(alpha=1.0 / n, adjust=False).mean()

    rsi = pd.Series(np.nan, index=px.index, dtype=float)
    both_zero = (avg_up == 0) & (avg_down == 0)
    only_up = (avg_down == 0) & (avg_up > 0)
    only_down = (avg_up == 0) & (avg_down > 0)
    normal = ~(both_zero | only_up | only_down)

    rs = avg_up[normal] / avg_down[normal]
    rsi[normal] = 100.0 - 100.0 / (1.0 + rs)
    rsi[only_up] = 100.0
    rsi[only_down] = 0.0
    rsi[both_zero] = 50.0
    rsi.iloc[0] = np.nan           # no delta available on the first bar
    return rsi.rename(f"rsi{n}")


def rsi_state(px: pd.Series, rsi_period: int, entry: float, exit_rsi: float,
              exit_sma: int, trend_sma: int, max_hold: int = 0) -> pd.Series:
    """Boolean 'in the market' series, using only information available at each close."""
    rsi = wilder_rsi(px, int(rsi_period))
    trend_ok = (px > px.rolling(int(trend_sma)).mean()) if trend_sma else pd.Series(True, index=px.index)
    sma_x = px.rolling(int(exit_sma)).mean() if exit_sma else None

    r = rsi.values
    t = trend_ok.values
    p = px.values
    sx = sma_x.values if sma_x is not None else None

    out = np.zeros(len(px), dtype=bool)
    state = False
    held = 0
    for i in range(len(px)):
        if state:
            held += 1
            leave = False
            if exit_rsi and not np.isnan(r[i]) and r[i] > exit_rsi:
                leave = True
            if sx is not None and not np.isnan(sx[i]) and p[i] > sx[i]:
                leave = True
            if max_hold and held >= max_hold:
                leave = True
            if leave:
                state, held = False, 0
        else:
            if (not np.isnan(r[i])) and r[i] < entry and bool(t[i]):
                state, held = True, 1
        out[i] = state
    return pd.Series(out, index=px.index, name="in_market")


class RSI2MeanReversion(Strategy):
    """The published rule: RSI(2) < 5, price above its 200-day average, exit above SMA(5)."""

    def __init__(self, name="RSI(2) mean reversion", params=None):
        base = {"risky": "VFINX", "safe": "CASH", "rsi_period": 2, "entry": 5.0,
                "exit_rsi": 0.0, "exit_sma": 5, "trend_sma": 200, "max_hold": 0}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["risky"], p["safe"]]

    def signals(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.Series:
        p = self.params
        st = rsi_state(prices[p["risky"]], p["rsi_period"], p["entry"], p["exit_rsi"],
                       p["exit_sma"], p["trend_sma"], p["max_hold"])
        return st.reindex(rebalance_dates).ffill().fillna(False).astype(bool)

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        on = self.signals(prices, rebalance_dates)
        w = pd.DataFrame(0.0, index=rebalance_dates, columns=prices.columns)
        w.loc[on.values, p["risky"]] = 1.0
        w.loc[~on.values, p["safe"]] = 1.0
        return w
