"""Regression tests for the two data-loading bugs that nearly shipped in article #2.

Neither test touches the network: they seed a fake cache and read it back.
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

import pandas as pd
import pytest

from strategylab import data as D


def _seed(cache: Path, ticker: str, first: str, last: str = "2026-01-01") -> None:
    """Write a parquet that looks like a real cached download."""
    idx = pd.bdate_range(first, last)
    frame = pd.DataFrame(
        {c: 100.0 for c in ["Open", "High", "Low", "Close", "Volume"]}, index=idx
    )
    cache.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache / f"{ticker}.parquet")
    D._write_meta()


def test_cache_dir_is_repo_anchored_not_cwd(tmp_path, monkeypatch):
    """The original bug: the cache lived at Path.cwd()/'data'.

    Running each strategy from its own folder therefore created a *separate* cache,
    and a freshly created one silently held less history than the caller asked for.
    """
    monkeypatch.delenv("STRATEGYLAB_DATA", raising=False)
    monkeypatch.chdir(tmp_path)
    assert D.cache_dir() == D._REPO_ROOT / "data"
    assert D.cache_dir() != tmp_path / "data"


def test_warns_when_history_starts_after_requested_start(tmp_path, monkeypatch):
    """The trap: ask for 1980, get 1987, and the 10-month average is undefined
    for the opening stretch — so the strategy sits in the wrong asset and the
    backtest reports a spectacular number that is purely an artifact."""
    monkeypatch.setenv("STRATEGYLAB_DATA", str(tmp_path))
    _seed(tmp_path, "VBMFX", first="1986-12-11")

    with pytest.warns(UserWarning, match="warm-up artifact"):
        px = D.load_prices(["VBMFX"], start="1980-01-01")

    assert px.index[0].year == 1986


def test_no_warning_when_history_covers_the_request(tmp_path, monkeypatch):
    monkeypatch.setenv("STRATEGYLAB_DATA", str(tmp_path))
    _seed(tmp_path, "VFINX", first="1980-01-02")

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning fails the test
        px = D.load_prices(["VFINX"], start="1987-01-01")

    assert px.index[0].year == 1987


def test_stale_cache_version_forces_refetch(tmp_path, monkeypatch):
    """Caches written before EARLIEST was fixed hold 1990+ data only, so they
    must not be trusted for an earlier request."""
    monkeypatch.setenv("STRATEGYLAB_DATA", str(tmp_path))
    _seed(tmp_path, "SPY", first="1993-01-29")
    (tmp_path / ".cache-meta.json").write_text('{"version": 1, "earliest": "1990-01-01"}')

    calls = []
    monkeypatch.setattr(D, "_download", lambda t, end: calls.append(t) or pd.DataFrame(
        {c: 100.0 for c in ["Open", "High", "Low", "Close", "Volume"]},
        index=pd.bdate_range("1993-01-29", "2026-01-01")))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        D.load_prices(["SPY"], start="1993-01-29")

    assert calls == ["SPY"], "a cache from an older fetch window must be refetched"
