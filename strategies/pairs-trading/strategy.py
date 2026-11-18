"""Pairs trading by the distance method — Gatev, Goetzmann and Rouwenhorst (2006).

The oldest documented statistical arbitrage. Take a universe, measure how closely every
pair of instruments has tracked each other over a formation window, keep the closest few,
and then bet that when one of a close pair wanders away from the other it will come back.
Short the one that rose, buy the one that lagged, and close when they meet again.

What makes it different from everything else in this series is that it needs no market
direction at all. The book is long one instrument and short another in equal size, so a
rising or falling index should cancel out. That also makes it the first strategy here
that cannot be run without borrowing stock, which is a cost the engine had to learn.

The rules, which are the published ones:

  Formation (12 months)  Build a total-return index for each instrument, based at 1.0 on
                         the first day of the window. For every pair, sum the squared
                         daily differences between the two indices. Keep the ``n_pairs``
                         with the smallest sum: those are the pairs that tracked closest.
                         Record the standard deviation of each pair's spread.
  Trading (6 months)     Carry the same indices forward. Open a pair when its spread
                         exceeds ``entry_sigma`` formation standard deviations, short the
                         higher leg and buy the lower one. Close when the spread crosses
                         zero, or when the trading window ends.

Each selected pair is allocated an equal share of capital. An open pair holds half that
long and half short, so the book is cash-neutral; a pair with no position holds cash.

Params
  n_pairs       : how many pairs to carry (5 in the paper's headline result)
  formation_days: length of the formation window, trading days
  trading_days  : length of the trading window, trading days
  entry_sigma   : spread divergence that opens a position, in formation sigmas
  stop_sigma    : abandon a pair whose spread reaches this (0 disables)
  wait_one_day  : enter the day after the trigger rather than on it
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategylab.strategy import Strategy


@dataclass(frozen=True)
class Pair:
    a: str
    b: str
    ssd: float
    sigma: float


def _normalised(prices: pd.DataFrame) -> pd.DataFrame:
    """Total-return index for each column, based at 1.0 on the first row."""
    return (1 + prices.pct_change().fillna(0.0)).cumprod()


def select_pairs(formation: pd.DataFrame, n_pairs: int) -> list[Pair]:
    """The closest-tracking pairs over the formation window, by sum of squared deviation.

    Only instruments that traded for the whole window are eligible: a fund that listed
    halfway through has not had the chance to track anything, and letting it in would
    pick pairs on a few months of coincidence.
    """
    eligible = [c for c in formation.columns if formation[c].notna().all()]
    if len(eligible) < 2:
        return []
    norm = _normalised(formation[eligible])
    values = norm.values
    names = list(norm.columns)

    out: list[Pair] = []
    for i in range(len(names)):
        diff = values[:, i][:, None] - values[:, i + 1:]
        ssd = np.square(diff).sum(axis=0)
        sigma = diff.std(axis=0, ddof=1)
        for k, j in enumerate(range(i + 1, len(names))):
            if sigma[k] > 0 and np.isfinite(ssd[k]):
                out.append(Pair(names[i], names[j], float(ssd[k]), float(sigma[k])))

    out.sort(key=lambda p: p.ssd)
    return out[:n_pairs]


class PairsTrading(Strategy):
    def __init__(self, name="Pairs trading (distance method)", params=None):
        base = {"n_pairs": 5, "formation_days": 252, "trading_days": 126,
                "entry_sigma": 2.0, "stop_sigma": 0.0, "wait_one_day": True}
        super().__init__(name=name, params={**base, **(params or {})})

    # ------------------------------------------------------------------ core
    def _periods(self, index: pd.DatetimeIndex):
        """Yield (formation slice, trading slice) for each non-overlapping cycle."""
        f, t = int(self.params["formation_days"]), int(self.params["trading_days"])
        start = 0
        while start + f + t <= len(index):
            yield index[start:start + f], index[start + f:start + f + t]
            start += t

    def weight_matrix(self, prices: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        n_pairs = int(p["n_pairs"])
        entry, stop = float(p["entry_sigma"]), float(p["stop_sigma"])
        lag = 1 if p["wait_one_day"] else 0

        w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        share = 1.0 / n_pairs if n_pairs else 0.0
        self._trades: list[dict] = []

        for form_idx, trade_idx in self._periods(prices.index):
            pairs = select_pairs(prices.loc[form_idx], n_pairs)
            if not pairs:
                continue
            # carry the formation-based index forward through the trading window
            window = prices.loc[form_idx[0]:trade_idx[-1]]
            norm = _normalised(window)

            for pair in pairs:
                spread = (norm[pair.a] - norm[pair.b]).loc[trade_idx]
                side = 0          # +1 = long a / short b, -1 = the reverse
                opened_on = None
                entry_spread = 0.0
                for k, day in enumerate(spread.index):
                    s = spread.iloc[k]
                    if side == 0:
                        if abs(s) >= entry * pair.sigma:
                            side = -1 if s > 0 else 1    # fade the gap
                            opened_on = day
                            entry_spread = float(s)
                    else:
                        # side == +1 was opened on a negative spread (a below b) and
                        # converges when the gap closes upward; side == -1 is the mirror.
                        converged = (s >= 0) if side == 1 else (s <= 0)
                        stopped = stop > 0 and abs(s) >= stop * pair.sigma
                        if converged or stopped or k == len(spread) - 1:
                            self._trades.append({
                                "pair": f"{pair.a}/{pair.b}", "opened": str(opened_on.date()),
                                "closed": str(day.date()), "side": side,
                                "days": int((day - opened_on).days),
                                "entry_spread_sigma": round(entry_spread / pair.sigma, 2),
                                "reason": "stop" if stopped else ("converged" if converged else "period end"),
                            })
                            side = 0
                            opened_on = None
                            continue
                    if side != 0:
                        # the position is held from the day after the trigger
                        target = spread.index[min(k + lag, len(spread) - 1)]
                        w.loc[target, pair.a] += side * share / 2
                        w.loc[target, pair.b] += -side * share / 2

        return w

    # -------------------------------------------------------------- interface
    def target_weights(self, prices: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        full = self.weight_matrix(prices)
        return full.reindex(rebalance_dates).fillna(0.0)

    @property
    def trades(self) -> pd.DataFrame:
        return pd.DataFrame(getattr(self, "_trades", []))
