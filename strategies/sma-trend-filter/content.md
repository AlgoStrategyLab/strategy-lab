If you have read anything about tactical asset allocation, you have met this rule. Each month, compare the S&P 500's price to its 10-month moving average. Above it, hold stocks. Below it, hold bonds or cash. Mebane Faber's 2007 paper made it the default starting point for a generation of retail systematic investors, and it is the engine inside a large share of the "trend following for normal people" content published since.

[Last time](../dual-momentum/) I found that Dual Momentum's entire contribution came from its [absolute momentum](gl:absolute-momentum) test — a different [trend filter](gl:trend-filter), built on 12-month returns rather than a moving average. I promised to find out whether the moving average does anything that filter does not.

The short answer, over 39.8 years of daily data: **no, and it charges you for the privilege.** The two filters make the same call 88% of the time. The moving average version switches 48 times to momentum's 27, gives up 1.2 percentage points a year, and ends with $35 per dollar invested against momentum's $55.

But the more useful finding is the one nobody mentions: **10 months is close to the worst setting you could pick.** Every longer average I tested beat it, on both return and Sharpe, while trading less.

:::note
**New to systematic trading?** Terms like [CAGR](../glossary/#cagr), [Sharpe ratio](../glossary/#sharpe), [whipsaw](../glossary/#whipsaw) and [walk-forward analysis](../glossary/#walk-forward) are explained in plain language in the [glossary](../glossary/) — 64 definitions, no prior knowledge assumed. Dotted underlines link straight to the relevant entry.
:::

## The rule, exactly as backtested

On the last trading day of each month, using month-end closes:

- Compute the 10-month simple moving average of the S&P 500's month-end closes.
- If the latest close is _above_ that average, hold 100% equities.
- If it is at or below, hold 100% US aggregate bonds.
- Execute at the next trading day's close. Hold until the next month-end.

Faber's original used cash as the defensive asset and applied the rule across five asset classes. I use bonds here so the comparison against Dual Momentum's absolute-momentum test is apples to apples — that rule also parks in bonds. The T-bill version is reported in the variants table below, and it is worse.

{{table: sma_t_setup.png | Backtest setup: Yahoo Finance daily closes, January 1987 to October 2026, monthly rebalance, next-close execution, 10 bps costs}}

**One warm-up detail that matters more than it sounds.** A 10-month average needs ten months of history before it exists. If you start the price series at the safe asset's inception, the filter is undefined for the first ten months and the strategy sits in bonds through whatever the market does. In my first run that artifact alone turned 1987 into a 31% loss, because the rule missed the rally and then bought in just before the October crash. A real investor in January 1987 had seven years of S&P history, so the [backtest](gl:backtest) loads price data from 1980 and only evaluates from 1987. If you build this yourself, check that first.

## Results

Over 39.8 years, the moving-average filter returned 9.38% a year against 10.61% for absolute momentum and 11.24% for simply holding the index. All three ended with very different risk: the filters cut [maximum drawdown](gl:max-drawdown) from 55% to around 34%.

{{table: sma_t_headline.png | Head-to-head table comparing the 10-month SMA filter, 12-month absolute momentum, the S&P 500 and 60/40}}

{{fig: c1_equity.png | Growth of $1 from 1987 to 2026 on a log scale for the SMA filter, absolute momentum, the S&P 500 and 60/40 | Both filters track the index closely for long stretches, separate during bear markets, and never fully catch up afterwards.}}

Note what this table does _not_ show: a filter beating the market. Neither does. This is the same conclusion as the last article — a trend filter is a risk-management tool that happens to roughly keep pace, not a way to earn more. The 60/40 column is there as a reminder that a plain static allocation got a better [Sharpe ratio](gl:sharpe) than either filter, with no trading at all.

## Are they even different filters?

This is the question the article exists to answer, and the clearest way to see it is to plot what each filter was doing, month by month, for forty years.

{{fig: c2_signals.png | Timeline showing when each filter was risk-on or risk-off from 1987 to 2026, with disagreements highlighted, above a drawdown chart | Coloured means risk-on, grey means in bonds. The big grey blocks — 2001–03, 2008–09, 2022 — are nearly identical. Red marks the months they disagreed.}}

The two filters agreed on 88% of the 478 months. More importantly, they agreed on all the months that mattered: both sat out most of the dot-com bust, both sat out the financial crisis, both were fully invested through the 2020 crash. The disagreements are thin slivers at the edges of regime changes.

{{table: sma_t_agreement.png | Table of agreement statistics between the two filters}}

When they did disagree, neither was reliably right. The moving average won 62% of those months and momentum 53% — on samples of 26 and 32 months, which is far too small to call a winner. But the _size_ of the calls differed: in months when only momentum was invested, equities returned 3.1% on average; when only the moving average was invested, 1.6%. Momentum's rare solo bets were worth about twice as much.

{{table: sma_t_disagree.png | The longest disagreement episodes and which filter was right}}

So the gap between the two strategies is not explained by better calls. It is explained by **how often each one trades**. The moving average switched 48 times against momentum's 27, holding a position for 209 days on average against 371. Every one of those extra switches is a chance to sell low and buy back higher — [whipsaw](gl:whipsaw) — and in aggregate they cost about 1.2 points a year.

## When it works, when it bleeds

{{table: sma_t_episodes.png | Performance of both filters and the S&P 500 across eleven major market episodes from 1987 to 2026}}

**The good.** The dot-com bust is the showcase: the moving average returned +11.6% while the index lost 47%, because the signal turned negative in late 2000 and stayed negative for two years. The financial crisis is almost as good, –3.5% against –54.9%. These are the slow, grinding declines a monthly filter is built for, and it did its job.

**The bad.** October 1987 is the clearest lesson in the whole series. Both filters were fully invested going into Black Monday, both sold at the month-end immediately after, and both finished the episode down 24.1% — _worse_ than the 19.5% you would have lost doing nothing. A monthly rule cannot react to a one-day crash, and selling at the bottom of one converts a recoverable loss into a locked-in one. The same pattern repeats, less dramatically, in 2020.

2022 is the other instructive failure: the moving average lost 26.6%, worse than both momentum (–19.2%) and the index (–24.1%), because it flipped in and out three times while bonds were falling alongside stocks. A trend filter whose defensive asset is also trending down has nowhere to hide.

{{table: sma_t_drawdowns.png | The five deepest drawdowns of the 10-month SMA filter}}

## Robustness

### 1. The famous number is the wrong number

Faber's paper used 10 months, and essentially everyone who followed copied it. Over this window, that is close to the worst choice available.

{{fig: c3_lookback.png | Bar charts of CAGR, Sharpe and turnover across moving-average lengths from 6 to 16 months}}

Every setting longer than 10 months produced a higher return, a higher Sharpe _and_ less trading. At 16 months the filter returns 11.27% — effectively matching buy-and-hold while keeping the drawdown protection — on a third less turnover than the 10-month version.

Two honest caveats. First, this is a single 40-year sample; a monotonic ranking across six settings is suggestive, not proof. Second, I am reading this chart _after_ seeing it, which is exactly the hindsight the [walk-forward test](gl:walk-forward) below exists to control for. What I would not do is claim 16 is the right number — the defensible claim is narrower: the evidence for 10 specifically is weak, and the cost of being wrong about it is around two points a year.

### 2. A buffer fixes about half the gap

If the problem is too much switching, the standard remedy is hysteresis: require the price to clear the average by some margin before buying back, and to fall below it by the same margin before selling. This is a one-parameter change.

{{fig: c4_band.png | Scatter of CAGR against annual turnover for buffer widths from 0% to 5% | Each point is a buffer width. Widening it to 3% cuts turnover almost in half and adds 1.3 points of annual return.}}

A 3% band takes the strategy from 9.38% to 10.68% and cuts turnover from 239% to 128% — roughly closing the gap to absolute momentum, which is itself a slower-moving signal. That is the real lesson: **most of the moving average's underperformance is trading friction, not bad judgment**, and anything that makes it slower helps. Past 3% the buffer starts costing more in late entries than it saves in whipsaw.

### 3. Before and after publication

Faber published in 2007. Splitting there, with no refitting:

{{fig: c5_inout.png | Bar chart comparing CAGR, Sharpe and maximum drawdown before and after 2007}}

Before: 11.29% a year against the index's 11.63%, with drawdown cut from 48% to 33% — a good risk-adjusted outcome. After: 7.36% against 10.85%, trailing by 3.5 points a year. The same post-publication decay that Dual Momentum showed, and for the same reason — the second half simply contained fewer of the slow bear markets this kind of rule is built to catch.

### 4. Walk-forward, and a surprise

Re-choosing the moving-average length each year from the best of the previous five years, then trading it out-of-sample for the next year, across 34 annual windows from 1992:

{{table: sma_t_walkforward.png | Walk-forward results: optimised 9.27%, fixed 10-month 8.47%, S&P 500 10.58%}}

This is the opposite of what happened in the last article, where optimising made Dual Momentum worse. Here it helped, by 0.8 points a year. The reason is visible in the sweep chart: the moving average's parameter surface slopes in one direction rather than wandering, so an optimiser looking backwards keeps choosing longer windows and keeps being right. When a parameter has a real gradient, fitting it works. When it is noise, fitting it fails. The same test tells you which situation you are in — which is the whole argument for running it.

### 5. Does combining them help?

{{table: sma_t_variants.png | Table of every variant tested including AND, OR, and the T-bill version}}

Requiring both filters to agree before investing (AND) makes things worse — 8.41%, the weakest variant tested — because it inherits both filters' late entries. Investing when _either_ is positive (OR) produced the best numbers in the whole study: 11.59% a year at a 0.81 Sharpe with the drawdown still capped at 33.8%, the only variant to beat buy-and-hold on return while halving the risk.

I would treat that result with suspicion rather than enthusiasm. It is the best of roughly a dozen variants I examined, which is exactly the setup that manufactures false positives, and the mechanism is mundane — OR is simply a slower, more reluctant filter, which is the same thing the buffer and the longer lookback achieved. I would want to see it hold on international indices and on a different era before trading it.

## What I'd change before trading this

**Don't use 10 months.** It is the weakest defensible setting in the range, and its popularity comes from one influential paper rather than from any evidence that it is optimal. Something in the 12–16 month range, or a buffer around the 10-month average, recovers most of the lost return and trades less.

**Expect no help in fast crashes.** 1987 and 2020 both show the filter fully invested at the bottom, then selling into it. If that matters, the fix is not a shorter average — shorter was worse at every length I tested — but a second, faster overlay accepting more whipsaw.

**Check your defensive asset.** The T-bill version returns 8.31% against the bond version's 9.38%, and 2022 showed bonds are not always safe either. A rule that compares bonds against T-bills before parking in them would have helped in both regimes.

**And consider not using this one at all.** On this evidence the 12-month absolute momentum test does the same job with less trading and better numbers. If you want a single trend filter, that is the one I would take — which is a slightly deflating conclusion for the most famous rule in the field, but it is what forty years of data says.
