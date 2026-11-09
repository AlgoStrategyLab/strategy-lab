Every strategy in this series so far has bought strength. [Dual momentum](../dual-momentum/) buys whichever asset rose most over the last year. The [10-month moving average](../sma-trend-filter/) buys an index that is above its own average. The [Donchian breakout](../donchian-breakout/) buys a new 20-day high. All three hold for weeks or months, and all three bleed in choppy markets — the Donchian rule spent fourteen consecutive years underwater, almost entirely to chop rather than to any crash.

So this article tests the opposite bet. RSI(2) buys weakness and holds it for days.

I went in expecting a complement: a rule that earns its keep in exactly the conditions that punish trend following. That is not what the data says, and the reason is more interesting than the thesis would have been.

**It wins {{v: trades.win_rate | pct1}} of its trades, and annualises {{v: exposure.annualised_while_invested | pct1}} on the days it is actually invested** — nearly three times the index. The signal is real.

**It also returns {{v: main.cagr | pct2}} a year against {{v: benchmark.cagr | pct2}} for doing nothing, and {{v: decomposition.cash_share_of_return | pct0}} of what it does return is interest on the cash it isn't investing.**

:::note
**New to systematic trading?** Terms like [CAGR](../glossary/#cagr), [Sharpe ratio](../glossary/#sharpe), [turnover](../glossary/#turnover), [drawdown](../glossary/#drawdown) and [mean reversion](../glossary/#mean-reversion) are explained in plain language in the [glossary](../glossary/) — no prior knowledge assumed. Dotted underlines link straight to the relevant entry.
:::

## The rule, exactly as backtested

Larry Connors and Cesar Alvarez published this in *Short Term Trading Strategies That Work* in 2008. It has been copied into retail trading content ever since, usually without a cost assumption attached.

Every trading day, using closing prices:

- If flat, and the close is **above** the 200-day simple moving average, and the 2-period [RSI](gl:rsi) closes **below 5**, buy equities.
- If long, and the close is **above** the 5-day simple moving average, sell and return to cash.
- Otherwise do nothing.
- Execute at the next day's close.

{{table: rsi_t_setup.png | Backtest setup: Yahoo Finance daily closes, January 1987 to November 2026, daily evaluation, next-close execution, 10 bps costs}}

A 2-period RSI is an unusual object. Wilder's smoothing constant at n=2 is one half, so the indicator reacts almost entirely to the last two closes. Dropping below 5 means roughly "the last two days were almost all down" — it is a short-term oversold trigger, not a trend measure. Capital sits in T-bills while flat, which matters more than it sounds like it should.

## Results

{{table: rsi_t_headline.png | Headline table comparing RSI(2) against the 10-month SMA filter, 60/40 and the S&P 500}}

{{fig: rsi_c1_equity.png | Forty years of compounding. The flat stretches are not drawdowns — they are the 94% of the time the strategy holds no equities at all.}}

The Sharpe ratio of {{v: main.sharpe | x}} is the best in the series so far, better than the index's {{v: benchmark.sharpe | x}}, and the maximum drawdown of {{v: main.max_drawdown | pct1}} is less than a third of the index's {{v: benchmark.max_drawdown | pct1}}. On the ratios alone this is the best-behaved strategy I have tested.

It also finished with less than a tenth of the money.

## Where the return actually comes from

The strategy is invested on {{v: exposure.days_in_market | num0}} of {{v: exposure.total_days | num0}} trading days — {{v: exposure.exposure | pct1}} of the record. Comparing its CAGR with buy-and-hold is therefore close to meaningless: for 94% of the period the two are not doing the same kind of thing at all.

Split the return into the part earned while invested and the part earned while sitting in T-bills:

{{fig: rsi_c2_decomposition.png | The strategy's own trades contributed less than the Treasury bills did.}}

{{table: rsi_t_exposure.png | Exposure statistics: days invested, growth while invested, and average daily return in and out of the market}}

Annualised over the days it holds equities, the strategy returns {{v: exposure.annualised_while_invested | pct1}}. That is a genuinely strong number and it is not an artifact — it survives costs, and the per-trade statistics agree with it.

But the trades contributed {{v: decomposition.trade_cagr | pct2}} a year to the total, and the cash contributed {{v: decomposition.cash_cagr | pct2}}. Most of what this strategy earned over forty years, it earned by not trading.

That reframes what the low drawdown means. A maximum drawdown of {{v: main.max_drawdown | pct1}} against the index's {{v: benchmark.max_drawdown | pct1}} is not evidence of skilful risk management. It is what happens when you are absent.

## The signal is good. The trend filter removes the best half of it.

It is worth separating the two components, because the usual explanation for the 200-day filter — that it keeps you out of bad trades — turns out to be wrong.

{{table: rsi_t_edge.png | Forward 5-day returns after each condition, against the unconditional base rate}}

On any given day the S&P returned {{v: signal_edge.baseline_avg_fwd5 | pct2}} over the following five days, and was higher {{v: signal_edge.baseline_pct_up_5d | pct1}} of the time. After RSI(2) closes below 5, the next five days returned {{v: signal_edge.after_rsi_below_5_avg_fwd5 | pct2}} — more than twice the base rate, across {{v: signal_edge.n_rsi_below_5 | num0}} occurrences. Short-term mean reversion in US equities is real and it is not subtle.

Now split those occurrences by the trend filter. Oversold **above** the 200-day average: {{v: signal_edge.above200_and_oversold_avg_fwd5 | pct2}} over the next five days. Oversold **below** it: {{v: signal_edge.below200_and_oversold_avg_fwd5 | pct2}}.

The setups the filter discards are the better ones. Buying a two-day collapse in a market that is already in a downtrend paid almost twice as well as buying one in an uptrend.

The filter still earns its place, but for a different reason than advertised:

{{table: rsi_t_components.png | Each component switched off in turn}}

Without the filter, CAGR barely moves but the Sharpe falls from {{v: main.sharpe | x}} to {{v: no_trend_filter.sharpe | x}} and the drawdown deepens from {{v: main.max_drawdown | pct1}} to {{v: no_trend_filter.max_drawdown | pct1}}. The filter is not selecting better trades. It is declining to catch falling knives during the one or two episodes per decade when the knife keeps falling, and paying for that insurance with the highest-returning setups in the sample.

Note also the fourth row. The 200-day filter **on its own**, with no RSI at all and no attempt at timing entries, returned {{v: trend_filter_only.cagr | pct2}} — more than double the full strategy. Almost everything this rule does to returns, it does by being out of the market.

## The cost cliff

At {{v: main.annual_turnover | pct0}} annual turnover, this strategy is a bet on your cost structure more than on the market.

{{fig: rsi_c4_costs.png | Each basis point of round-trip cost removes roughly 0.19 points of annual return.}}

{{table: rsi_t_costs.png | Cost sensitivity from frictionless to 100 bps}}

Frictionless it returns {{v: cost_sensitivity.0.cagr | pct2}}. At 10 bps, {{v: main.cagr | pct2}}. At 25 bps, {{v: cost_sensitivity.3.cagr | pct2}}. At 50 bps it is {{v: cost_sensitivity.4.cagr | pct2}} — the strategy destroys capital. Nothing about the signal changed; only the bill did.

This is the same finding as the Donchian article, and it is becoming the most reliable result in the series: any rule that trades often is, in practice, a wager that your execution is cheap. Published backtests almost never say so.

## A trap in the parameter grid

The grid holds something worth stopping on, because it is a mistake I have seen in published strategy write-ups and nearly made here.

{{fig: rsi_c5_sharpe_trap.png | The highest Sharpe ratios in the grid belong to settings that are almost never invested.}}

The best Sharpe in the entire grid is 6.9, with a maximum drawdown of 0.59%. It comes from RSI(5) below 5, which triggered on four days in forty years. The second best, 6.0, triggered on seven. These are not strategies; they are rounding errors with a ratio attached.

A Sharpe ratio says nothing about whether the opportunity exists often enough to matter, and optimising for it across a grid will reliably hand you the setting that trades least. The published setting — RSI(2) below 5 — sits in the middle of the cloud at a Sharpe of {{v: main.sharpe | x}} with {{v: exposure.exposure | pct1}} exposure, which is the honest region of the chart.

Any parameter search over a rule like this needs a minimum-exposure or minimum-trade-count floor, or the optimiser will walk straight off the edge.

## Before and after the book

This is the third strategy in the series to be tested against its own publication date, and the third to fail.

{{fig: rsi_c3_inout.png | The split is at January 2009, just after the book appeared.}}

{{table: rsi_t_inout.png | Performance before and after publication, with the index for comparison}}

Before 2009: {{v: in_out_sample.in_sample.cagr | pct2}} a year at a Sharpe of {{v: in_out_sample.in_sample.sharpe | x}}, with a worst drawdown of {{v: in_out_sample.in_sample.max_drawdown | pct1}}. That is an outstanding record.

After 2009: {{v: in_out_sample.out_of_sample.cagr | pct2}} a year at a Sharpe of {{v: in_out_sample.out_of_sample.sharpe | x}}, with a drawdown three times deeper.

The index moved the other way over the same split, from {{v: in_out_sample.benchmark_in_sample.cagr | pct2}} to {{v: in_out_sample.benchmark_out_of_sample.cagr | pct2}}. So this is not a story about a harder market. Whatever this rule was capturing, it captured much less of it after it was printed in a bestseller.

I cannot separate publication from the other things that changed in 2009 — decimalisation had already happened, but high-frequency market making scaled up over exactly this window, and short-horizon mean reversion is precisely the inefficiency that activity arbitrages away. Publication and competition are confounded here, and I would not claim otherwise.

## The thesis I set out to test, and why it failed

The premise was straightforward: trend following bleeds in chop, mean reversion should feed on it, so the two ought to be complements. The Donchian article left a specific window to test against — January 1999 to May 2013, the fourteen years that rule spent underwater, caused by chop rather than any crash.

{{fig: rsi_c6_regimes.png | The chop window at the far left is the test. RSI(2) did not win it.}}

{{table: rsi_t_regimes.png | Total return through each episode}}

Through that window RSI(2) returned {{v: regimes.0.rsi2 | pct1}}. The index returned {{v: regimes.0.sp500 | pct1}} and the monthly SMA filter — a trend system — returned {{v: regimes.0.sma_filter | pct1}}. The strategy that was supposed to thrive in chop came last by a wide margin.

What it does do is survive. Through the dot-com bust it returned {{v: regimes.1.rsi2 | pct1}} while the index lost {{v: regimes.1.sp500 | pct1}}; through the financial crisis, {{v: regimes.2.rsi2 | pct1}} against {{v: regimes.2.sp500 | pct1}}; through the 2022 bear market, {{v: regimes.6.rsi2 | pct1}} against {{v: regimes.6.sp500 | pct1}}. Those look like brilliant defensive numbers until you remember the exposure table. It survived those episodes the way a savings account survives them.

The complementarity thesis fails because mean reversion and trend following are not opposites in the way the framing suggests. Both need direction. A trend system needs price to keep going; this rule needs price to snap back. A genuinely rangebound market — the 1999–2013 window — delivers neither reliably, so both rules spend it paying costs for round trips that go nowhere. Chop is not the trend follower's enemy and the mean reverter's friend. It is just hostile.

## What I'd take from this

The signal is the most interesting thing here and it is not the strategy. Short-term oversold conditions in US equities really do predict higher forward returns, by a margin that is large and that persisted across {{v: signal_edge.n_rsi_below_5 | num0}} occurrences over forty years. {{v: trades.win_rate | pct1}} of trades were winners, over {{v: trades.trades | num0}} of them, at an average holding period of {{v: trades.avg_holding_days | num1}} days.

What the strategy does with that signal is where it falls apart. It is right often and paid little for being right — the average winner is {{v: trades.avg_win | pct2}} against an average loser of {{v: trades.avg_loss | pct2}}, a payoff ratio below one. It is invested too rarely for the edge to compound into anything. And it trades often enough that execution cost, not the signal, determines the outcome.

If I were trying to use this, I would not trade it as published. I would treat RSI(2) as an **overlay on a position I already hold** rather than as a standalone system — scaling exposure up on oversold closes rather than moving between equities and cash — which keeps the signal's value without paying to re-enter the market from scratch every few days, and without leaving 94% of the period in T-bills. That is a different article, and the honest thing to say is that I have not tested it yet.

## Caveats worth stating plainly

This is a long-only, single-index, fully-invested-or-flat implementation. Connors' own work applies the rule across many stocks and ETFs simultaneously, which changes the exposure arithmetic completely: twenty uncorrelated instruments each invested 6% of the time is a portfolio that is usually holding something. That is the strongest version of the argument against the conclusion here, and this backtest does not address it.

The cash return is real but period-specific. T-bills averaged a little under 3% over this window; a decade of zero rates would remove most of the contribution I just attributed to cash, and the strategy's total return with it.

The 5-day exit is one of several published variants, and the grid shows the result is not fragile to it — exiting on RSI(2) above 65 does slightly better, a fixed 5-day hold slightly worse. Entry at RSI below 10 rather than 5, which is the more commonly quoted version, roughly doubles the exposure and halves the Sharpe.

And as always: this is one market over one history, with instrument choice and start date selected with hindsight.
