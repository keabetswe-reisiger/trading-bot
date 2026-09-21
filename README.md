# Scalping bot (Alpaca paper trading)

A simple scalping bot for US stocks/ETFs via Alpaca, running on **paper trading**
(simulated money) by default.

## How it decides to trade

Think of it like checking traffic before pulling into an intersection — you
don't just look at the light right in front of you, you glance at the wider
flow of cars first.

- **Trend timeframes** (1h, 30m, 20m, 15m): is the stock generally trending up
  or down right now?
- **Confirm timeframes** (5m, 3m): does the medium-term picture still agree?
- **Entry timeframe** (1m): the actual scalp trigger — a fast/slow EMA
  crossover, filtered by RSI (not overbought/oversold) and VWAP (trading with
  the session's volume-weighted average price).

A trade only fires when the 1-minute trigger agrees with at least 3 of the 4
trend timeframes AND at least 1 of the 2 confirm timeframes. This trades less
often than a bare 1-minute crossover, but each signal has more of the market
"agreeing" with it — see `strategy/multi_timeframe.py` to loosen/tighten the
`min_trend_agree` / `min_confirm_agree` thresholds.

Symbols averaging fewer than `MIN_AVG_VOLUME` shares/minute over the last 10
bars are skipped — thin symbols eat a scalper's edge in slippage before the
trade even gets going.

These rules (trade with the higher-timeframe trend, use a precise trigger,
keep a tight stop with ~1.5–2x reward:risk, cap losses with a hard daily
stop, and stick to liquid symbols) reflect general scalping principles
described across public trading guides — see
[Dukascopy](https://www.dukascopy.com/swiss/english/marketwatch/articles/forex-scalping-strategies/)
and [ChartingLens](https://chartinglens.com/blog/scalping-trading-strategy).
A book titled "Pips Bible" didn't turn up in a search — if you have a
specific author/edition in mind, point me to it and I can fold in anything
it adds.

Every entry is a **bracket order**: the take-profit and stop-loss are placed
at the same time as the entry, so exits are handled by Alpaca even if this
script isn't running. A position still open after `MAX_HOLD_MINUTES` gets
force-closed — a scalp that hasn't hit its target or stop by then has stopped
being a scalp.

## Backtesting (no Alpaca account needed)

`backtest/` replays the exact same strategy/risk logic bar-by-bar over real
historical prices pulled free from Yahoo Finance (`yfinance`) — no API keys
required. It fetches 1-minute bars, derives every other timeframe from them
by resampling (so they all line up on the same clock), and only ever acts on
a signal at the *next* bar's open — never the bar it was computed from.

```bash
source venv/bin/activate
python -m backtest.run AAPL MSFT NVDA TSLA   # or any symbols you want
```

**Important caveat**: Yahoo only retains 1-minute bars for about the last 8
days, so this is a real-price sanity check over roughly one trading week, not
a statistically meaningful profitability study. A handful of trades per
symbol over one week can't tell you whether a strategy has an edge — it can
only tell you the plumbing (entry/exit/sizing logic) behaves the way it's
supposed to on real prices. Treat wins/losses here as "does this look
reasonable," not "this will make money live."

## Setup

1. Create a free Alpaca account and grab your **paper trading** API key/secret:
   https://app.alpaca.markets/paper/dashboard/overview
2. `cp .env.example .env` and fill in your keys (never commit `.env`).
3. Adjust `SYMBOLS`, risk %, and take-profit/stop-loss/hold-time in `.env` to taste.
4. Install dependencies and run:

```bash
source venv/bin/activate
pip install -r requirements.txt   # already done once, re-run after editing requirements.txt
python main.py
```

The bot only trades while the market is open, checking for signals every
`POLL_INTERVAL_SECONDS`.

## Risk controls already in place

- **Position sizing**: each trade risks `RISK_PER_TRADE_PCT` of account equity
  based on the distance to its stop-loss — not a fixed share count.
- **Daily loss limit**: once realized losses for the day hit
  `DAILY_LOSS_LIMIT_PCT` of equity, no new positions open until the next day.
- **Max open positions**: caps how many symbols can be in a trade at once.
- **Bracket orders**: every position has its exit defined at entry time.

## Known limitations (read before going anywhere near real money)

- **Pattern Day Trader (PDT) rule**: US accounts under $25k equity are limited
  to 3 day trades per rolling 5 business days on margin. A scalping bot will
  blow past that immediately. Paper accounts default to $100k equity so this
  isn't enforced there, but it *will* be enforced the moment you connect a
  real account under $25k. Do not point this at a live account without
  handling that.
- **Max-hold-time tracking is in-memory**: if the process restarts mid-trade,
  it forgets when that position was opened (the bracket order's TP/SL still
  protect it, just not the time-based force-exit).
- **No backtesting yet**: this has been smoke-tested with synthetic data for
  logic correctness, not validated against historical price action for
  profitability. Treat early paper-trading results as "does the plumbing
  work," not "is this strategy profitable."
- **API rate limits**: 7 timeframes × N symbols = 7×N data calls per poll.
  Alpaca's free tier has rate limits — keep `SYMBOLS` short and
  `POLL_INTERVAL_SECONDS` reasonable (60s+) to stay under them.

## Project layout

```
config.py                    # loads .env into typed settings (stock bot)
main.py                      # stock bot run loop (Alpaca)
config_gold.py                # loads .env into typed settings (gold bot, independent of config.py)
main_gold.py                  # gold bot run loop (OANDA, XAU_USD)
strategy/scalp_strategy.py   # 1-min EMA/RSI/VWAP entry signal
strategy/multi_timeframe.py  # multi-timeframe trend confirmation + voting
strategy/resample.py          # derives every timeframe from 1-minute bars
strategy/exits.py             # take-profit/stop-loss levels: fixed-% or ATR-based
risk/risk_manager.py         # position sizing, daily loss limit, max positions
execution/broker.py          # Alpaca API wrapper (data + orders)
execution/oanda_broker.py     # OANDA v20 API wrapper (data + orders)
logs/trade_logger.py         # appends every submitted trade to logs/trades.csv
backtest/                    # replays the strategy over real historical data (no keys needed)
```

## Gold bot (XAU_USD via OANDA)

`main_gold.py` trades real spot gold (XAU_USD) through OANDA instead of a
stock ETF — a genuine forex/CFD instrument, ~23/5 market, typically
leveraged. It reuses the exact same strategy/risk/exit logic as the stock
bot, swapped onto a different broker (`execution/oanda_broker.py`) because
Alpaca doesn't offer spot forex/metals.

**Setup:**
1. Create a free OANDA practice (demo) account: https://www.oanda.com/demo-account/
2. From the practice account dashboard, generate a personal access token and
   note your account ID (format like `101-001-XXXXXXX-001`).
3. Add `OANDA_API_TOKEN` and `OANDA_ACCOUNT_ID` to `.env` (see the gold section
   in `.env.example`). Leave `OANDA_ENVIRONMENT=practice` until you've watched
   it trade successfully.
4. `python main_gold.py`

**Differences from the stock bot worth knowing:**
- OANDA has no native M3/M20 candle granularity, so the bot fetches 1-minute
  candles only and derives every timeframe (3m, 5m, 15m, 20m, 30m, 1h) by
  resampling locally (`strategy/resample.py`) — this is also exactly how the
  gold backtester builds its timeframes, so live and backtest logic match.
- Position sizing is still risk-based (risk % ÷ stop distance = units), which
  is correct regardless of leverage — leverage only changes how much margin
  you need to hold the position, not the P&L math. This bot does **not**
  check margin availability before sizing a trade; watch your practice
  account's margin usage, especially early on.
- "Tradeable" replaces "market open" — OANDA reports this directly via its
  pricing endpoint, since forex/metals trade continuously except roughly
  Friday 5pm ET to Sunday 5pm ET.
- `GOLD_MIN_AVG_VOLUME` defaults to 0 (disabled): OANDA reports tick volume
  (price updates), not real traded volume, and gold futures/spot tick volume
  runs far lower than stock share volume — the stock bot's default would
  silently block every trade.

Backtest it the same way as stocks, using COMEX gold futures (`GC=F`) as a
close proxy for spot XAU_USD — Yahoo doesn't carry spot gold FX history:

```bash
python -m backtest.run GC=F
python -m backtest.tune_gold   # small grid search over ATR stop/target/hold settings
```

**Current honest result — this has not found a working edge on gold yet.**

Two different entry designs were tested against the same real `GC=F`
1-minute data:

1. The stock-style EMA-crossover trigger, swept across 12 exit-parameter
   combinations (ATR stop multiplier, reward:risk, max-hold-time): **every
   combination lost money** (-3.0% to -3.7%, 14-29% win rate).
2. A gold-specific reworked trigger (`strategy/gold_entry.py`) that waits
   for a pullback to the fast EMA and a same-direction confirmation candle,
   restricted to London/NY trading hours: swept across the same 12
   exit-parameter combinations, **also lost money in every single one**
   (-3.0% to -3.94%, 0-27% win rate — several combinations traded too little,
   4-8 trades, to say much beyond "still not profitable here").
3. Added a US Dollar Index (DXY) inverse-correlation filter as an extra
   "live trend" input — professional gold traders do watch this. It made
   **zero difference** in this test window because DXY was persistently
   bullish the whole week, so it never actually blocked a trade either way.
   Not adopted, since a filter with no measured effect is unjustified
   complexity, not a proven improvement.

Two independently-designed entry signals losing money on the same data,
plus a legitimate macro filter having no effect, points at something more
fundamental than "wrong parameters": either this one week was a genuinely
unfavorable sample for this style of strategy, or short-term technical
scalping on gold at this timeframe doesn't have enough edge to clear even a
spread-free backtest — and note **this backtest doesn't model bid/ask
spread or slippage at all**, so real execution would very likely perform
*worse* than these already-negative numbers, not better.

**Update — two more ideas tested, one is the current best candidate.**

From a gold-trading education video, two concepts were concrete enough to
actually codify and test (the other two — supply/demand zones and trendline
breakouts — require subjective manual judgment to draw and can't be turned
into an unambiguous rule without just inventing an arbitrary version):

- **Liquidity sweep / "stop hunt" at support-resistance**
  (`strategy/gold_price_action.py:stophunt_signal`) — price wicks past a
  recent swing high/low, then closes back on the other side. Combined with
  multi-timeframe trend confirmation: **73 trades, 45.2% win rate, +2.31%
  return, avg R +0.04** on the 1-week 1-minute sample — the largest trade
  count of anything tested, and the first genuinely positive result with
  enough trades to mean something.
- **RSI divergence** (`divergence_signal`) — still lost money (-3.4% to -3.9%).

Also confirmed something important by testing *with* and *without* the
multi-timeframe confirmation layer: for this stop-hunt signal, confirmation
helped a lot (bare: 318 trades, -7.5%; confirmed: 73 trades, +2.3%) — the
opposite of what the swing-strategy test showed, where confirmation hurt.
There's no universal rule here; it has to be tested per signal.

**Why this still isn't "found it"**: an average R-multiple of +0.04 is a
razor-thin margin — likely smaller than gold's typical bid-ask spread, which
this backtest still doesn't model. Max drawdown (9.2%) also exceeds the
total return (2.3%), a rough risk-adjusted profile. An attempt to check this
on a bigger, different dataset (60 days of 5-minute bars) wasn't a clean
test — the signal's lookback parameters were tuned for 1-minute bars and
barely fired at 5-minute granularity (5-7 trades), so it neither confirms
nor refutes generalization.

**Bottom line after 6 tested approaches** (crossover scalp, pullback scalp,
mean-reversion fade, raw swing crossover, multi-timeframe-confirmed swing,
stop-hunt, divergence): stop-hunt is the current best candidate and is now
`main_gold.py`'s default (`GOLD_ENTRY_MODE=stophunt`), but "best of six" is
not the same as "validated." Don't treat this as a proven strategy. It's
safe to run against the OANDA demo account (zero real money) as a
forward-testing/learning exercise and to validate the mechanics (data feed,
order execution, risk controls), but there is currently no strong backtest
evidence that it executes gold trades reliably profitably — real spread and
slippage costs, not modeled here, would likely erode this thin an edge.

**Update — stop-hunt held up on a fresh, later data window.** Re-tested
against 2026-09-14 to 09-21 (a different week than the original test, so
this is a real out-of-sample-ish check, not the same data re-run): **66
trades, 45.5% win rate, +1.41% return, avg R +0.03**. Same direction (thin
positive) and similar magnitude as the original +2.31% test — the first
time in this project a signal has held up consistently across two different
data windows, which is meaningfully more reassuring than any single
backtest alone.

**Frequency vs. quality tradeoff (tested, not just assumed)**: there was a
request to trade closer to once per hour (stop-hunt currently fires about
once every 2.5 hours). Tried an OR-ensemble of all four entry signals
(`strategy/gold_price_action.py` + `strategy/gold_entry.py` +
`strategy/scalp_strategy.py`) and mean-reversion with multi-timeframe
confirmation added (`strategy/gold_meanrev.py`) at several confirmation
strictness levels, specifically to push frequency up:

| Approach | Frequency | Return |
|---|---|---|
| stop-hunt alone (current default) | ~1 trade / 2.5 hrs | **+1.41%** |
| OR-ensemble, loose confirmation | ~1 trade / 1.75 hrs | -3.34% |
| OR-ensemble, strict confirmation | ~1 trade / 25 hrs | -3.77% |
| Mean-reversion + confirmation (any level) | ~1 trade / 2-9 hrs | -2.4% to -3.6% |

Every way tried to increase frequency did it by accepting lower-quality
setups, and every one erased the edge. Decision made: keep stop-hunt as-is
rather than force hourly frequency — frequency and (thin, unproven-but-
consistent) quality are in tension here, not independently tunable.

**Important bug found and fixed — re-read backtest numbers above with this
in mind.** `RiskManager` tracked "today" using the real wall-clock date, not
the simulated bar timestamps. Backtests replay a week of trading in seconds
of real time, so "today" never actually advanced during a run — once the
daily loss limit tripped once, it silently stayed tripped for the *rest of
the backtest*, incorrectly suppressing trading for days it shouldn't have.
Fixed by making day-rollover explicit (`RiskManager` methods now take an
`at` timestamp — the simulated bar time in backtests, real time live).
Re-ran the affected tests after the fix: stop-hunt's baseline actually
improved (66 trades → same count, but +5.3% instead of the earlier +3.22%
figure quoted above), confirming the bug was making things look *worse*
than they were, not better — so this wasn't a case of a bug inflating a
result we then trusted. There's a second bug in the same area, not yet
fixed: the live bots (`main.py`, `main_gold.py`) never called
`record_closed_trade()` at all, meaning the live daily-loss-limit has never
actually tracked realized P&L — it was decorative. **Now fixed for
`main_gold.py`** (fetches the last closed trade's realized P&L from OANDA
when a position disappears between polls) but **`main.py` — the stock bot —
still has this gap**, unaddressed since gold has been the active focus.

**Two new ideas from trading-education videos, tested and adopted — best
result in this project so far.** From a breakdown of an auction-market-
theory-based gold strategy video: gamma exposure (GEX) and real order-flow
absorption require specialized options/tick data this project doesn't have
access to, so those weren't implementable. Two things from it were:

1. **"2 consecutive losses = stop for the day"** — a sound risk-discipline
   rule independent of entry logic. Added to `RiskManager` as
   `max_consecutive_losses`.
2. **Candlestick confirmation** (engulfing candle / pin bar,
   `strategy/candle_patterns.py`) required on the stop-hunt trigger bar —
   standard, well-defined patterns (unlike "3-bar reversal" from a separate
   candlestick video, which claimed a higher success rate with no backing
   data shown, so wasn't implemented).

Tested against real GC=F data (post-bug-fix numbers):

| Configuration | Trades | Win% | Return | Avg R | Max DD |
|---|---|---|---|---|---|
| stop-hunt alone | 66 | 47.0% | +5.3% | 0.09 | 7.37% |
| + candle confirmation | 44 | 59.1% | +13.49% | 0.30 | 4.56% |
| + candle confirmation + 2-loss breaker | 35 | **62.9%** | **+13.83%** | **0.38** | **3.77%** |

This is now the default (`GOLD_REQUIRE_CANDLE_CONFIRM=true`,
`GOLD_MAX_CONSECUTIVE_LOSSES=2`). **Important caveat**: unlike bare
stop-hunt (validated on two separate weeks), this specific combination has
only been tested on one week — it hasn't yet had the same out-of-sample
check. Treat it as the best candidate found, one step more promising than
anything before it, not as newly proven.

**Position-size safety cap added.** `RiskManager.max_position_value_pct`
(default 500% of equity) caps notional exposure independent of risk-based
sizing — a backstop against a freak edge case (e.g. a near-zero ATR
reading producing a tiny stop distance) sizing an unreasonably large
position. Verified: an artificial near-zero-stop scenario that would have
sized a ~$440M position was correctly capped to ~$497K.

**Spread cost tested — the edge is thin enough to matter.** Backtests
had assumed zero cost to enter/exit, which is unrealistic.
`backtest/engine.py` now supports `spread_cost` (round-trip cost per unit).
At a realistic OANDA gold spread ($0.30-0.50), avg R on the current best
config drops from 0.30 to 0.11-0.19; at $1.00 it flips negative. Also
observed: re-running the identical config on a freshly-fetched data window
(same week later in the day) gave 37 trades/+3.39% instead of the earlier
35 trades/+13.83% — the rolling 7-day window shifting as real time passes
changes results substantially, a further reminder not to over-trust any
single number here.

**Two more ideas tested and rejected**, from further video breakdowns:
Fair Value Gaps (`strategy/fair_value_gap.py` — unfilled 3-candle price
imbalances) cut trades too aggressively (37 → 4-6) with no benefit, and the
Fibonacci 0.886 retracement filter (`strategy/fibonacci.py`) was mildly
positive alone (avg R +0.23) but made the combined result *worse* when
stacked with candle confirmation (+0.30 → +0.22). Neither adopted.

**Break-and-close continuation trigger — promising but small sample,
not the default yet.** `strategy/breakout.py`: the mirror image of
stop-hunt — price closes cleanly beyond a recent swing level instead of
sweeping past it and reversing. Alone it was roughly breakeven (-0.4%),
but combined with candle confirmation: **17 trades, 64.7% win rate,
+2.43%, avg R +0.48** — the highest avg R found in this project. Available
as `GOLD_ENTRY_MODE=breakout`, but not adopted as default: only 17 trades
is a much smaller sample than stop-hunt's validated 37-66 trade range, and
this project has been burned before by trusting a strong small-sample
result (the earlier "+10.6% swing" number that didn't hold up). Tested
combining stop-hunt + breakout as parallel candle-confirmed signals — this
made things *worse* (avg R +0.07), not better, suggesting the two triggers
fire in different conditions and simple OR-combination dilutes rather than
adds. Worth watching over time before considering a switch.

**More candlestick patterns added, but split by entry mode — broadening
confirmation helps one signal and hurts the other.** From a standard
candlestick-pattern reference: Dragonfly/Gravestone Doji, Harami, and
Tweezers Top/Bottom (`strategy/candle_patterns.py`) — same category as the
existing engulfing/pin-bar, all textbook-defined, unambiguous. Testing the
broader set against both current signals:

| Signal | Narrow confirm (engulfing+pin bar) | Broad confirm (+doji/harami/tweezers) |
|---|---|---|
| stop-hunt | 37 trades, +3.39%, avg R 0.30 | 27 trades, +0.49%, avg R **0.03** |
| breakout | 17 trades, +2.43%, avg R 0.48 | 21 trades, +3.41%, avg R **0.48** (same, more trades) |

Broadening confirmation diluted stop-hunt badly but helped breakout (same
quality, larger sample). Since stop-hunt is the validated live default,
its confirmation stays narrow; breakout (already non-default) now uses the
broader set. `confirms_long`/`confirms_short` = narrow (stop-hunt),
`confirms_long_broad`/`confirms_short_broad` = broad (breakout).

## Running it on your phone (Termux/Android)

See [`termux/README.md`](termux/README.md) — runs `main_gold.py` directly on
an Android phone via Termux + a Debian environment (`proot-distro`), with
scripts to keep it alive in the background and auto-start on reboot. The code
is also pushed to a private GitHub repo
(`github.com/keabetswe-reisiger/trading-bot`) so it can be pulled onto any
device, not just this one.
