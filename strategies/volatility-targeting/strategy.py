"""Volatility targeting as a layer over an existing strategy.

Every strategy in this series so far answers *what to own*. This one answers *how
much*, and it answers it the same way whatever the thing underneath decides.

The rule, from Moreira and Muir (2017) and a long practitioner tradition before it:
measure how volatile the strategy's own returns have been lately, and scale the
position so that the volatility you expect next month is the one you asked for. When
markets are calm you hold more; when they thrash you hold less.

Two implementation choices matter more than the formula, so they are explicit:

* **The volatility measured is the strategy's, not the market's.** A trend filter that
  is already in cash has no volatility to damp, and scaling its zero exposure by three
  still gives zero. Using the market's volatility instead would lever a cash position.

* **The scale is computed from the strategy's own realised returns up to the rebalance
  date and no further.** The base weights are known a day ahead of the fill, so the
  pseudo-return series below is the one an investor could actually have measured on the
  morning they traded. There is no peeking at the volatility being targeted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategylab.strategy import Strategy


def realised_vol(returns: pd.Series, lookback: int, method: str = "simple",
                 halflife: int | None = None) -> pd.Series:
    """Annualised trailing volatility of a daily return series.

    ``simple`` is an equal-weighted standard deviation over ``lookback`` days — what
    most write-ups mean by realised vol. ``ewma`` weights recent days more heavily,
    which reacts faster to a regime change and is what most risk systems actually run.
    """
    if method == "ewma":
        hl = halflife or max(lookback // 3, 1)
        var = returns.ewm(halflife=hl, min_periods=max(lookback // 2, 5)).var(bias=False)
    elif method == "simple":
        var = returns.rolling(lookback, min_periods=max(lookback // 2, 5)).var()
    else:
        raise ValueError(f"unknown vol method: {method}")
    return np.sqrt(var * 252.0)


def pseudo_returns(weights_daily: pd.DataFrame, asset_returns: pd.DataFrame,
                   cash_rate: float = 0.0) -> pd.Series:
    """Daily returns the base strategy would have produced, before costs.

    Yesterday's weights times today's returns, with anything uninvested earning the
    cash rate. Costs are left out on purpose: this series exists only to measure
    volatility, and a cost charged on rebalance days adds a spike to the variance that
    has nothing to do with the risk being measured.
    """
    w = weights_daily.shift(1).fillna(0.0)
    r = (w * asset_returns).sum(axis=1)
    if cash_rate:
        idle = (1.0 - w.sum(axis=1)).clip(lower=0.0)
        r = r + idle * ((1 + cash_rate) ** (1 / 252) - 1)
    return r


@dataclass
class VolatilityTargeted(Strategy):
    """Wraps a base strategy and scales its weights towards a volatility target.

    params:
      base            the Strategy being scaled
      target_vol      annualised volatility to aim for, e.g. 0.10 for 10%
      lookback        trading days of history used to measure realised volatility
      method          "simple" or "ewma"
      max_scale       largest multiple of the base position (1.0 = de-risk only)
      min_scale       smallest multiple; 0.0 lets the rule go flat
      floor_vol       realised vol below this is treated as this, so a quiet patch
                      cannot produce an enormous scale from a near-zero denominator
    """

    def __post_init__(self):
        self.params.setdefault("target_vol", 0.10)
        self.params.setdefault("lookback", 60)
        self.params.setdefault("method", "simple")
        self.params.setdefault("max_scale", 1.0)
        self.params.setdefault("min_scale", 0.0)
        self.params.setdefault("floor_vol", 0.02)

    @property
    def base(self) -> Strategy:
        return self.params["base"]

    @property
    def tickers(self) -> list[str]:
        return self.base.tickers

    def scales(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """The scale applied on each rebalance date, with the inputs behind it.

        Returned rather than hidden because the whole article is about this number.
        """
        base_w = self.base.target_weights(prices, rebalance_dates)
        base_w = base_w.reindex(columns=prices.columns).fillna(0.0)

        # The base strategy's weights as held day by day: set on the day after the
        # signal, exactly as the engine fills them, and carried until the next change.
        daily = base_w.reindex(prices.index).shift(1).ffill().fillna(0.0)
        rets = prices.pct_change().fillna(0.0)
        pr = pseudo_returns(daily, rets)

        vol = realised_vol(pr, self.params["lookback"], self.params["method"])
        floor = float(self.params["floor_vol"])
        vol_used = vol.clip(lower=floor)

        raw = float(self.params["target_vol"]) / vol_used
        scale = raw.clip(lower=float(self.params["min_scale"]),
                         upper=float(self.params["max_scale"]))
        # A rebalance date with no volatility estimate yet (the first `lookback` days)
        # gets the base position untouched rather than a guess.
        scale = scale.reindex(rebalance_dates).fillna(1.0)
        return pd.DataFrame({
            "realised_vol": vol.reindex(rebalance_dates),
            "vol_used": vol_used.reindex(rebalance_dates),
            "raw_scale": raw.reindex(rebalance_dates),
            "scale": scale,
            "base_exposure": base_w.sum(axis=1).reindex(rebalance_dates),
        })

    def target_weights(self, prices: pd.DataFrame,
                       rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        base_w = self.base.target_weights(prices, rebalance_dates)
        base_w = base_w.reindex(columns=prices.columns).fillna(0.0)
        s = self.scales(prices, rebalance_dates)["scale"]
        return base_w.mul(s, axis=0).fillna(0.0)

    def describe(self) -> dict:
        p = {k: v for k, v in self.params.items() if k != "base"}
        return {"name": self.name, "params": p, "base": self.base.describe()}
