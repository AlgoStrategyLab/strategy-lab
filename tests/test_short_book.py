"""The engine's handling of short positions.

Pairs trading is the first strategy in the series that needs them, and a long/short
book that pays nothing to borrow is a flattering fiction: the borrow is a real,
recurring fee, and on a market-neutral strategy it comes straight off a return that
was never large to begin with.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategylab.engine import Backtest
from strategylab.strategy import Strategy


class LongShort(Strategy):
    """Half long A, half short B, rebalanced monthly."""

    def target_weights(self, prices, rb):
        return pd.DataFrame([{"A": 0.5, "B": -0.5}] * len(rb), index=rb)


class LongOnly(Strategy):
    def target_weights(self, prices, rb):
        return pd.DataFrame([{"A": 1.0}] * len(rb), index=rb)


@pytest.fixture
def prices():
    idx = pd.bdate_range("2020-01-01", "2023-01-01")
    n = len(idx)
    rng = np.random.default_rng(7)
    a = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    b = 100 * np.cumprod(1 + rng.normal(0.0002, 0.01, n))
    return pd.DataFrame({"A": a, "B": b}, index=idx)


def test_borrow_charges_only_the_short_leg(prices):
    free = Backtest(prices, LongShort(name="ls"), benchmark="A", rebalance="M",
                    cost_bps=0, borrow_bps=0).run()
    paid = Backtest(prices, LongShort(name="ls"), benchmark="A", rebalance="M",
                    cost_bps=0, borrow_bps=100).run()

    shorts = free.metrics["avg_short_exposure"]
    assert 0.3 < shorts < 0.6, "the book should be roughly half short"

    drag = free.metrics["cagr"] - paid.metrics["cagr"]
    expected = shorts * 0.01                      # 100 bps on the short side
    assert expected * 0.75 < drag < expected * 1.25, (
        f"borrow drag {drag:.4f} should be near {expected:.4f}")
    assert paid.metrics["annual_borrow_cost"] == pytest.approx(expected, rel=0.05)


def test_borrow_does_not_touch_a_long_only_book(prices):
    free = Backtest(prices, LongOnly(name="lo"), benchmark="A", rebalance="M",
                    cost_bps=0, borrow_bps=0).run()
    paid = Backtest(prices, LongOnly(name="lo"), benchmark="A", rebalance="M",
                    cost_bps=0, borrow_bps=500).run()
    assert free.metrics["cagr"] == pytest.approx(paid.metrics["cagr"], abs=1e-9)
    assert paid.metrics["avg_short_exposure"] == 0.0


def test_exposure_metrics_describe_a_market_neutral_book(prices):
    r = Backtest(prices, LongShort(name="ls"), benchmark="A", rebalance="M",
                 cost_bps=0, borrow_bps=0).run()
    m = r.metrics

    # The pre-existing metric sums signed weights, so a market-neutral book reads 0%
    # and means nothing. These are the ones to quote for a long/short strategy.
    assert m["time_in_market"] < 0.5 < m["time_with_a_position"], (
        "time_in_market sums signed weights, so it under-reports a long/short book "
        "that is in fact holding positions nearly every day")
    assert abs(m["avg_net_exposure"]) < 0.05
    assert 0.8 < m["avg_gross_exposure"] < 1.05
    assert m["time_with_a_position"] > 0.95


def test_short_leg_profits_when_it_falls(prices):
    """A falling short leg must add to the return, not subtract from it."""
    idx = pd.bdate_range("2020-01-01", "2021-01-01")
    flat = np.full(len(idx), 100.0)
    falling = np.linspace(100, 50, len(idx))
    px = pd.DataFrame({"A": flat, "B": falling}, index=idx)

    r = Backtest(px, LongShort(name="ls"), benchmark="A", rebalance="M",
                 cost_bps=0, borrow_bps=0).run()
    assert r.metrics["cagr"] > 0.15, "shorting a halving asset should make money"
