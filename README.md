# Strategy Lab

Systematic trading strategies, backtested properly: exact rules, every metric, the robustness tests
that decide whether any of it means anything, and all the code.

One engine, one execution model, one cost assumption, one results schema — so numbers compare
across strategies instead of each article being its own island. Each strategy pairs with a write-up
at [algostrategylab.github.io](https://algostrategylab.github.io/) and on Medium.

Author: Abhinav Taduka — software architect, quant algo developer. EPAT (QuantInsti).

## Strategies

<!-- strategies:start -->
| # | Strategy | Family | Rebalance | Period | CAGR | Sharpe | Max DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | [Dual Momentum (GEM)](strategies/dual-momentum) | trend-following | monthly | 1997–2026 | 10.25% | 0.72 | −33.83% |
| 02 | [10-month SMA filter](strategies/sma-trend-filter) | trend-following | monthly | 1987–2026 | 9.38% | 0.71 | −35.18% |
| 03 | [Donchian 20/10 breakout](strategies/donchian-breakout) | trend-following | daily | 1987–2026 | 5.24% | 0.56 | −35.83% |
| 04 | [RSI(2) mean reversion](strategies/rsi2-mean-reversion) | mean-reversion | daily | 1987–2026 | 3.62% | 0.79 | −15.69% |
<!-- strategies:end -->

Benchmarks and the full metric sheet for each run live in that strategy's `output/*.json`.
The generated [comparison table](https://algostrategylab.github.io/compare/) is built from those
files directly, so it cannot drift from the articles that quote it.

## Layout

```
strategylab/              the engine: data loading, Strategy interface, simulator, metrics, robustness
strategies/<slug>/
  strategy.py             the rules, as a Strategy subclass
  run.py                  full backtest + robustness suite -> output/*.json
  make_charts.py          this article's charts
  make_tables.py          this article's tables, rendered as PNGs
  meta.yml                taxonomy, provenance, where the numbers live
  content.md              the prose, with numbers as references rather than literals
  output/                 results, committed, so every published figure is reproducible
sitebuild/
  render.py               the shared table renderer
  values.py               resolves {{v: path | format}} against a strategy's results
  generate.py             builds the site: article pages, hub, comparison, feed
data/                     one shared price cache for every strategy
tests/                    regression tests, including the warm-up trap described below
```

## Running it

```bash
pip install -r requirements.txt
python strategies/donchian-breakout/run.py        # fetches prices (cached), writes output/
python strategies/donchian-breakout/make_charts.py
python -m sitebuild.generate                      # builds site/ from meta.yml + content.md + JSON
pytest                                            # regression tests
```

## The harness

- **Execution:** signals on the rebalance date's close, fills at the next trading day's close
  (one-day lag, no same-bar look-ahead). Weights drift between rebalances.
- **Costs:** flat basis points per unit of turnover, charged on fill.
- **Rebalancing:** `D` for daily systems, `W`/`M`/`Q` for the last trading day of each period.
- **Metrics:** ~90, grouped the way a fund fact sheet groups them — returns, risk, risk-adjusted,
  and benchmark-relative — plus yearly and monthly tables and a drawdown table with recovery dates.
- **Robustness:** `parameter_sweep`, `in_vs_out_of_sample`, anchored-window `walk_forward`.
- **Output:** one JSON per run with metrics, config, yearly table, equity/drawdown series and
  allocation changes — the same shape for every strategy.

Adding a strategy: create `strategies/<slug>/`, subclass `Strategy` in `strategy.py` implementing
`target_weights(prices, rebalance_dates)` (rows sum to ≤ 1.0, remainder is cash), copy a `run.py`,
then write `meta.yml` and `content.md`.

## Why the numbers are references, not text

Every figure in an article is written as `{{v: main.cagr | pct2}}` and resolved at build time from
that strategy's results file. A reference that does not resolve fails the build. This exists because
the three articles written before the generator had their numbers typed in by hand, and a re-run
with another year of data would have left the pages quietly stale while still looking authoritative.

## The warm-up trap

The first run of article #2 reported a 31% loss for 1987 while the index gained 5% — a spectacular
finding that was entirely an artifact. Price history had been sliced at the bond fund's 1986
inception, leaving a 10-month moving average undefined for the opening stretch, so the strategy sat
in bonds through the rally and bought in just before the crash.

Two things in `strategylab/data.py` exist because of it: the cache is anchored to the repository
rather than the working directory, and every download runs from a fixed early date so a cached file
is always a superset of any request. A request whose start precedes a ticker's own history now
raises a warning instead of passing quietly. `tests/test_data_cache.py` pins all of it.

A backtest will hand you a dramatic number that is really a bug in your data setup, and it will not
tell you which one you have. The only defence is to go looking.

## Disclaimer

Research and education only, not investment advice. Backtests benefit from hindsight in instrument
choice and start date; past performance does not predict future results.

## License

MIT — see [LICENSE](LICENSE).
