"""Data loading with a local parquet cache so backtests are reproducible offline.

Two things here exist because of a bug that nearly shipped in article #2.

The cache used to live at ``Path.cwd() / "data"``, so running a strategy from its
own folder created a *separate* cache; and the download hardcoded
``start="1990-01-01"`` regardless of the ``start`` the caller asked for. Together
that meant a strategy requesting history from 1980 could silently receive data
from 1990, leaving its moving average undefined for the first N months. The
backtest then reported a dramatic, entirely artificial result.

So: the cache is anchored to the repository, every download runs from `EARLIEST`
(making each cached file a superset of any request), and a request whose start
precedes a ticker's own history raises a warning rather than passing quietly.
"""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pandas as pd

#: Every download starts here, so a cached file is always a superset of any request.
EARLIEST = "1970-01-01"

#: Bump when the cache layout or fetch window changes; older caches are refetched.
CACHE_VERSION = 2

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: A ticker whose history starts this long after the requested start is flagged.
_WARMUP_TOLERANCE = pd.Timedelta(days=5)


def cache_dir() -> Path:
    """Where cached prices live. Anchored to the repo, never to the working directory."""
    return Path(os.environ.get("STRATEGYLAB_DATA", _REPO_ROOT / "data"))


def _meta_path() -> Path:
    return cache_dir() / ".cache-meta.json"


def _read_meta() -> dict:
    try:
        return json.loads(_meta_path().read_text())
    except (OSError, ValueError):
        return {}


def _write_meta() -> None:
    _meta_path().write_text(json.dumps({"version": CACHE_VERSION, "earliest": EARLIEST}, indent=1))


def _download(ticker: str, end: str | None) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(ticker, start=EARLIEST, end=end, progress=False, auto_adjust=True)
    if raw.empty:
        raise ValueError(f"no data returned for {ticker!r}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw[["Open", "High", "Low", "Close", "Volume"]].dropna()


def load_prices(tickers: list[str], start: str = "2000-01-01", end: str | None = None,
                field: str = "Close", refresh: bool = False) -> pd.DataFrame:
    """Return a wide DataFrame of adjusted prices (dividends reinvested) indexed by date.

    Uses yfinance with ``auto_adjust=True`` so ``Close`` is total-return adjusted.
    Each ticker is cached to ``<repo>/data/<TICKER>.parquet``.

    Warns if a ticker's own history begins materially after ``start`` — that is the
    signature of an indicator that will be undefined over the opening stretch of the
    backtest, which is exactly how a warm-up artifact becomes a headline number.
    """
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    stale_cache = _read_meta().get("version") != CACHE_VERSION
    want_start = pd.Timestamp(start)

    frames, late = {}, []
    for t in tickers:
        path = cache / f"{t}.parquet"
        raw = None
        if path.exists() and not refresh and not stale_cache:
            raw = pd.read_parquet(path)
        if raw is None:
            raw = _download(t, end)
            raw.to_parquet(path)

        first = raw.index[0]
        if first > want_start + _WARMUP_TOLERANCE:
            late.append((t, first.date()))
        frames[t] = raw[field]

    if stale_cache:
        _write_meta()

    if late:
        detail = ", ".join(f"{t} from {d}" for t, d in late)
        warnings.warn(
            f"requested history from {want_start.date()} but {detail}. Any indicator with a "
            f"lookback will be undefined over the opening window — evaluate from a later date, "
            f"or the result for that stretch is a warm-up artifact, not a finding.",
            UserWarning, stacklevel=2,
        )

    px = pd.DataFrame(frames).sort_index()
    px = px.loc[start:end] if end else px.loc[start:]
    return px.dropna(how="all")
