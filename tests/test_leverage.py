"""The leverage cap and the margin charge added for article #6."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategylab.engine import Backtest
from strategylab.strategy import Strategy


class Fixed(Strategy):
    """Holds a constant weight in one ticker, whatever the market does."""
    def target_weights(self, prices, rb):
        return pd.DataFrame([{self.params["t"]: self.params["w"]}] * len(rb), index=rb)


def flat_prices(n=504, drift=0.0):
    idx = pd.bdate_range("2020-01-01", periods=n)
    px = pd.DataFrame({"A": (1 + drift) ** np.arange(n), "B": np.ones(n)}, index=idx)
    return px


def test_weights_above_one_are_rejected_by_default():
    px = flat_prices()
    bt = Backtest(px, Fixed(name="levered", params={"t": "A", "w": 1.5}),
                  benchmark="B", rebalance="M", cost_bps=0)
    with pytest.raises(ValueError, match="max_gross"):
        bt.run()


def test_raising_the_cap_admits_the_same_weights():
    px = flat_prices()
    r = Backtest(px, Fixed(name="levered", params={"t": "A", "w": 1.5}), benchmark="B",
                 rebalance="M", cost_bps=0, max_gross=2.0).run()
    # 50% of the account is borrowed on every day the position is held. The average
    # over the whole run is a little under that because the first rebalance does not
    # fill until the end of the first month, and until then nothing is held at all.
    assert r.metrics["avg_borrowed"] == pytest.approx(0.5, abs=0.03)
    assert r.metrics["avg_borrowed"] < 0.5
    assert r.metrics["time_levered"] > 0.9


def test_margin_is_charged_only_on_the_borrowed_part():
    px = flat_prices()
    kw = dict(benchmark="B", rebalance="M", cost_bps=0, max_gross=2.0)
    free = Backtest(px, Fixed(name="l", params={"t": "A", "w": 1.5}), margin_bps=0, **kw).run()
    paid = Backtest(px, Fixed(name="l", params={"t": "A", "w": 1.5}), margin_bps=200, **kw).run()
    # 200 bps on 0.5 of the account, over two years, compounds to roughly 2%
    gap = free.equity.iloc[-1] - paid.equity.iloc[-1]
    assert gap == pytest.approx(0.02, abs=0.004)
    assert paid.metrics["annual_margin_cost"] == pytest.approx(0.01, abs=0.001)


def test_margin_leaves_an_unlevered_book_alone():
    px = flat_prices()
    kw = dict(benchmark="B", rebalance="M", cost_bps=0, max_gross=2.0)
    a = Backtest(px, Fixed(name="u", params={"t": "A", "w": 0.6}), margin_bps=0, **kw).run()
    b = Backtest(px, Fixed(name="u", params={"t": "A", "w": 0.6}), margin_bps=500, **kw).run()
    pd.testing.assert_series_equal(a.equity, b.equity)
    assert b.metrics["avg_borrowed"] == 0.0
    assert b.metrics["annual_margin_cost"] == 0.0


def test_leverage_multiplies_the_underlying_move():
    px = flat_prices(drift=0.0004)
    kw = dict(benchmark="B", rebalance="M", cost_bps=0, max_gross=2.0, margin_bps=0)
    one = Backtest(px, Fixed(name="1x", params={"t": "A", "w": 1.0}), **kw).run()
    two = Backtest(px, Fixed(name="2x", params={"t": "A", "w": 2.0}), **kw).run()
    # daily returns scale with the weight; the equity curves then compound apart
    assert two.daily_returns.mean() == pytest.approx(2 * one.daily_returns.mean(), rel=0.02)
    assert two.equity.iloc[-1] > one.equity.iloc[-1]
