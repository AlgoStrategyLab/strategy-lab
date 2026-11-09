"""Dual Momentum (Global Equities Momentum, Antonacci 2014).

Rules, evaluated on the last trading day of each month, executed next close:
  1. Absolute momentum: if the US equity index's trailing `lookback`-month total return
     exceeds the trailing cash (T-bill) return, equities are "on"; otherwise hold bonds.
  2. Relative momentum: when equities are on, hold whichever of US / international
     has the higher trailing `lookback`-month return.
  3. 100% in the chosen asset. No leverage, no shorting.

Params
  us, intl, bonds : tickers
  cash            : ticker of a cash-return index (daily T-bill accrual)
  lookback        : months (default 12)
  abs_on          : use absolute-momentum filter (default True) — False = relative-only
  rel_on          : use relative momentum (default True) — False = US-only with trend filter
"""
from __future__ import annotations

import pandas as pd

from strategylab.strategy import Strategy


class DualMomentum(Strategy):
    def __init__(self, name="Dual Momentum (GEM)", params=None):
        base = {"us": "VFINX", "intl": "VGTSX", "bonds": "VBMFX", "cash": "CASH",
                "lookback": 12, "abs_on": True, "rel_on": True}
        super().__init__(name=name, params={**base, **(params or {})})

    @property
    def tickers(self):
        p = self.params
        return [p["us"], p["intl"], p["bonds"], p["cash"]]

    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        p = self.params
        lb = int(p["lookback"])
        # trailing return over `lb` months using month-end closes available at each rebalance date
        me = prices.resample("ME").last()
        trail = me / me.shift(lb) - 1
        rows = []
        for d in rebalance_dates:
            t = trail.loc[:d].iloc[-1]           # month-end row at or before d (d is a month end)
            if t.isna().any():
                rows.append({c: 0.0 for c in prices.columns}); continue
            if p["rel_on"]:
                risky = p["us"] if t[p["us"]] >= t[p["intl"]] else p["intl"]
            else:
                risky = p["us"]
            if p["abs_on"] and t[p["us"]] <= t[p["cash"]]:
                pick = p["bonds"]
            else:
                pick = risky
            w = {c: 0.0 for c in prices.columns}
            w[pick] = 1.0
            rows.append(w)
        return pd.DataFrame(rows, index=rebalance_dates)
