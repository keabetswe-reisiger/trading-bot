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
actually tracked realized P&L — it was decorative. **Now fixed for both
bots.** `main_gold.py` fetches the last closed trade's realized P&L from
OANDA directly (`realizedPL` field) when a position disappears between
polls. `main.py` needed a different approach — Alpaca doesn't expose
realized P&L per closed position the way OANDA does, only fill prices —
so `AlpacaBroker.get_last_closed_fill_price()` reads the exit fill price
from the closed bracket order/leg, and `main.py` combines that with its own
locally-tracked entry price/qty (already known from when it submitted the
order) to compute P&L itself, same math as everywhere else in this project.
Verified with a stub test (both the TP/SL-bracket-closed-it path and the
max-hold-time forced-close path) since there are no live Alpaca credentials
here to test against directly.

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

**Volume Spread Analysis "Stopping Volume" — best avg R found, but held
back entirely, not even as a non-default option.** From Tom Williams'
VSA methodology (`strategy/volume_confirmation.py`): a reversal is more
credible when the trigger bar shows unusually high volume relative to
recent bars — real participation, not a low-conviction wiggle. Notably,
VSA's "Spring"/"Upthrust" patterns are conceptually identical to
`stophunt_signal`, independent validation of that signal's core idea from
an established, decades-old methodology unrelated to anything else tested
here. Combined with stop-hunt + candle confirmation: **16 trades, 75% win
rate, +2.45%, avg R +0.53, max drawdown 0.56%** — the best avg R in this
project.

**Not wired into `main_gold.py` at all, unlike breakout.** This result
depends on real traded volume (Yahoo's futures data), but OANDA reports
*tick volume* for gold (price-update count, not actual traded volume) —
already the reason `MIN_AVG_VOLUME` is disabled by default. Whether tick
volume behaves similarly enough for "Stopping Volume" to mean the same
thing on live OANDA data is unknown, not just untested — a more serious
gap than the usual small-sample caveat (16 trades is also small). Needs
validation against OANDA's actual tick-volume data before it's a real
candidate, live or backtested.

**"No Demand" / "No Supply" from the same VSA book — tested, rejected.**
`strategy/vsa_bars.py` codifies two more concepts from Tom Williams'
*Master the Markets*, distinct from Stopping Volume above: a bar that looks
directionally fine on price alone but whose volume gives it away. **No
Demand** — an up-bar, narrow spread, volume below the previous two bars' —
is a bearish tell despite the up close. **No Supply** — a down-bar, narrow
spread, volume below the previous two bars', closing in the middle/high of
its range — is a bullish tell despite the down close. Tested two ways
against the same `GC=F` data used throughout this project:

| Approach | Trades | Win% | Return% | Avg R |
|---|---|---|---|---|
| stop-hunt + candle confirm (live default, baseline) | 37 | 59.5% | +3.39% | 0.30 |
| No Demand/No Supply as standalone contrarian entries | 25 | 28.0% | -1.50% | -0.21 |
| stop-hunt + candle confirm, with a No Demand/No Supply veto | 30 | 53.3% | +1.30% | 0.16 |

Standalone, it loses money — confirmed robust across narrow-spread lookback
windows of 5/10/20 bars, all negative (avg R -0.24 to -0.18), so this isn't
a lookback-tuning artifact. Layered as a veto on the validated live default
(skip a stop-hunt long if a No Demand bar just printed, skip a short if a
No Supply bar just printed), it filtered out 7 of 37 trades but return and
avg R both dropped — the veto removed winners along with losers, net
negative, the same "a plausible-sounding filter with no measured benefit"
outcome as the DXY filter and Fibonacci-stacking tests above. Not adopted
either way. Code kept in the repo (untested ideas from the same source
sometimes combine differently later), not wired into `main_gold.py`.

**"Quality" mode — stacking the three best-proven building blocks, best
spread-cost survival found so far.** Every idea tested in this project so
far was tried as a *replacement* for the live default. This one instead
*combines* three independently-validated pieces: the structural trigger
(stop-hunt or breakout), each with its own already-validated candle
confirmation, gated further by VSA "Stopping Volume"
(`strategy/volume_confirmation.py`) — the trigger bar must also show real
elevated volume, not just a price wiggle. README already noted stop-hunt +
candle + volume alone found the best avg R in the project (+0.53) as a
side observation, but it was never actually built or swept properly until
now. Swept the volume multiplier (1.3/1.5/2.0) against fresh `GC=F` data:

| Config | Trades | Win% | Return% | Avg R | Max DD% |
|---|---|---|---|---|---|
| stop-hunt+confirm (live default, baseline) | 37 | 59.5% | +3.39% | 0.30 | 1.34% |
| breakout+confirm (baseline) | 21 | 61.9% | +3.41% | 0.48 | 1.06% |
| stop-hunt+confirm+volume (x1.5) | 16 | 75.0% | +2.45% | 0.53 | 0.56% |
| breakout+confirm+volume (x1.5) | 9 | 66.7% | +0.89% | 0.29 | 0.81% |
| **either signal, both quality-gated (x1.5)** | **23** | **73.9%** | **+3.13%** | **0.44** | **0.56%** |

Higher volume multipliers push win rate and avg R up further (x2.0:
stop-hunt+volume alone hit 81.8% win, avg R 0.74) but on ever-smaller trade
counts (11 trades) — a real quality/quantity tradeoff, not noise, since it's
monotonic across all three multipliers tested. Picked x1.5 "either" as the
best-balanced config: more trades than any single quality-gated leg (23 vs
16 or 9), so a somewhat larger sample, while keeping win rate and avg R well
above the live default.

**Spread-cost tested, and this is where it earned adoption as an option**:
at a realistic $0.40 OANDA spread, it beats stop-hunt+confirm on every
metric — 60.0% win vs 54.1%, +1.88% vs +1.68%, avg R 0.31 vs 0.15 (roughly
double). At $1.00 spread both go negative, but the quality-gated version
degrades less (avg R -0.17 vs -0.24).

Added as `GOLD_ENTRY_MODE=quality` (`main_gold.py:_quality_signal`,
`GOLD_QUALITY_VOLUME_MULTIPLIER` in `.env.example`, default 1.5) — **not the
new default**. Same unresolved gap as Stopping Volume always had: OANDA
reports tick volume for gold, not real traded volume, and this has only
been validated against Yahoo's real-volume `GC=F` data, never against
OANDA's actual tick volume. Available to run on the practice account
alongside `stophunt` to see how it behaves live before considering a
default change.

**Pre-trade spread guard — added.** Nothing previously checked the live
bid/ask spread before submitting an order; on a scalp with a tight
ATR-based stop, a spread spike (news, thin liquidity) could eat a large
chunk of the risk budget before the trade even started. `OandaBroker.
get_current_spread()` now reads the current `closeoutBid`/`closeoutAsk`,
and `run_once()` skips a fired signal if the spread exceeds `GOLD_MAX_SPREAD`
(default $0.50 — between this project's own "$0.40 = typical" and "$1.00 =
wide, kills the edge" spread-cost test bracket). **Not backtestable** — no
historical bid/ask data exists for `GC=F` anywhere in this project — so
this is a live/paper-only safety net, verified only by a stub test (forced
signal, wide vs. narrow mocked spread, confirms the order is/isn't
submitted), not by a trade-metrics table like everything else here.

**Session restriction for stop-hunt — tested, explicitly rejected.**
`GOLD_RESTRICT_SESSION=true` only ever applied to `pullback` mode; `stophunt`
(the live default) has always ignored it, which looked like an obvious bug.
It isn't one. Backtested applying the same London/NY-only gate
(`strategy/gold_entry.in_active_session`) to `stophunt+confirm` against the
same fresh `GC=F` window:

| Config | Trades | Win% | Return% | Avg R | Max DD% |
|---|---|---|---|---|---|
| session-restricted (London/NY only) | 18 | 38.9% | -0.4% | -0.05 | 1.88% |
| unrestricted (current live behavior) | 29 | 55.2% | +2.3% | 0.24 | 1.34% |

Restricting the session makes every metric worse. Plausible reason: a
stop-hunt is a liquidity-sweep pattern, and thinner overnight liquidity may
be exactly what makes resting stops easier to sweep — the opposite of what
a lagging crossover trigger (`pullback`) needs from a quiet session. Not
applied to `stophunt`; `GOLD_RESTRICT_SESSION` still only gates `pullback`.

**Day-trading (hours-long hold) swing strategy — re-tested with a real
sample, confirmed not a viable alternative to scalping.** `strategy/
gold_swing.py` + `backtest/gold_swing.py` (EMA(9/21) crossover on 5-minute
bars, confirmed by 3-of-4 higher timeframes, ATR stops, up to 8h hold) were
built earlier and only ever validated on a small, unrecorded sample. Unlike
every 1-minute strategy in this project — capped at ~7-8 days of history by
Yahoo's 1-minute data limit — 5-minute bars are available back 60 days,
giving this a real 117-162 trade sample per config, the largest in this
project by far:

| ATR× | R:R | Hold | Trades | Win% | Return% | Avg R | Max DD% |
|---|---|---|---|---|---|---|---|
| 1.5 | 2.0 | 4h | 162 | 33.3% | +3.12% | -0.02 | 12.8% |
| 1.5 | 2.0 | 8h | 161 | 32.9% | +5.44% | -0.01 | 12.8% |
| 1.5 | 3.0 | 4h | 161 | 26.1% | -0.51% | -0.05 | 14.1% |
| 1.5 | 3.0 | 8h | 157 | 23.6% | -0.10% | -0.06 | 12.8% |
| 2.5 | 2.0 | 4h | 140 | 33.6% | -14.53% | -0.13 | 22.6% |
| 2.5 | 2.0 | 8h | 124 | 35.5% | +3.42% | +0.02 | 13.7% |
| 2.5 | 3.0 | 4h | 140 | 30.7% | -17.25% | -0.16 | 21.8% |
| 2.5 | 3.0 | 8h | 117 | 29.1% | -5.68% | -0.07 | 11.1% |

Win rate is stuck at 23-36% across every configuration (a trend-following
signature — many small losses, occasional bigger wins), but avg R is
negative in 6 of 8 configs, and the 2 "positive" ones are essentially zero
(+0.02, -0.01). The best-looking config by return (1.5×/2:1/8h, +5.44%) has
avg R -0.01 — noise landing slightly positive in dollars this window, not a
real edge. Drawdowns (11-23%) are far worse than anything on the scalping
side (0.56-1.88%), and get worse, not better, at wider stops. **Confirms
this specific entry (EMA crossover) doesn't have an edge on gold at this
timeframe** — larger sample size resolved the ambiguity the original small
test left open. Not adopted; no live version was ever built, and none is
planned unless a different entry signal is tried at this timeframe (e.g.
adapting stop-hunt/breakout logic to 5m/1h bars would be new work, not a
re-run of this).

**Adapting stop-hunt/breakout to the swing timeframe — the first
spread-robust edge found anywhere in this project, but not validated yet.**
The crossover swing entry above had no edge; stop-hunt/breakout (validated
on 1-minute data) hadn't been tried at 5-minute/hours-hold. Made
`strategy.gold_swing.aligned_signal` and `backtest.gold_swing.simulate_swing`
accept a swappable `entry_signal_fn` (same pattern as the 1-minute
`strategy.multi_timeframe.aligned_signal`), and added `spread_cost` support
to the swing backtest engine (it didn't have any before).

First pass (1.5x ATR, 2:1 reward:risk, 8h hold, default 1-minute-tuned
`lookback=40, swing_order=3`): stop-hunt bare was the only promising one
(248 trades, +8.1%, avg R 0.05) — candle confirmation, which helps a lot at
1-minute, **hurt** both stop-hunt and breakout here (a genuine per-timeframe
finding, not a bug). Full 8-combo exit-parameter grid on stop-hunt/breakout
bare found the best config: stop-hunt, 1.5x ATR, 2:1, 4h hold — 252 trades,
36.9% win, +15.52%, avg R 0.08, max DD 12.95%.

Then swept `lookback`/`swing_order` (untested until now — inherited
unchanged from 1-minute) at that exit setting. `lookback=80` produced 0
trades at every `swing_order` — a **test-harness artifact**, not a result:
`simulate_swing`'s `entry_window` caps the bars handed to the signal at 60,
so a signal requesting 80 can never fire; not a real backtest of that
setting. Excluding that, `swing_order=5` (a stricter, more isolated swing
point) beat `swing_order=3` at every lookback tested:

| Config | Spread | Trades | Win% | Return% | Avg R | Max DD% |
|---|---|---|---|---|---|---|
| lookback=20, order=5 | $0 | 119 | 41.2% | +14.92% | 0.18 | 10.31% |
| lookback=20, order=5 | $0.40 (typical) | 119 | 40.3% | +9.01% | 0.11 | 11.04% |
| lookback=20, order=5 | $1.00 (wide) | 118 | 40.7% | +1.92% | +0.03 | 11.14% |
| lookback=40, order=5 | $0 | 194 | 39.2% | +19.38% | 0.13 | 13.29% |
| lookback=40, order=5 | $0.40 | 193 | 38.9% | +10.28% | 0.08 | 13.7% |
| lookback=40, order=5 | $1.00 | 193 | 38.9% | -2.87% | -0.02 | 18.09% |

This looked like the first config anywhere in this project to survive a
$1.00 "wide" spread test — but that claim didn't survive its own
follow-up check. Yahoo's 5-minute data can't be re-fetched from a genuinely
separate historical period (it's a rolling 60-day window from today, not a
selectable range), so the closest available validation is splitting the
same 60-day sample in half and checking both halves tell the same story:

| Window | Trades | Win% | Return% (0 / $0.40 / $1.00) | Avg R (0 / $0.40 / $1.00) | Max DD |
|---|---|---|---|---|---|
| Full 60 days | 119 | 41.2% | +14.92% / +9.01% / +1.92% | 0.18 / 0.11 / +0.03 | 10.3% |
| First half | 59 | 35.6% | -1.83% / -4.51% / -7.27% | -0.02 / -0.09 / -0.17 | 10.3% |
| Second half | 54 | 50.0% | +18.62% / +15.98% / +12.09% | 0.47 / 0.41 / +0.32 | 4.2% |

They don't. The first half loses money at every spread level; the second
half is the best isolated result in this entire project. The "config that
survives a $1 spread" was an average of a bad stretch and a great stretch,
not a consistent effect — the textbook signature of `swing_order=5` being
the best of 12 combinations swept on one sample, tuned to whatever happened
in part of the data rather than reflecting real, durable behavior.

**Verdict: rejected.** Doesn't generalize even within the single 60-day
sample it came from, so there's no basis to trust it forward. Net result
of the whole swing-timeframe exploration (crossover, then stop-hunt/
breakout): **no entry signal tested so far has shown a real, consistent
edge on gold at the 5-minute/hours-hold timeframe.** No live implementation
exists at this timeframe, and none is warranted on this evidence.

## Genuine multi-day swing/position trading (daily bars)

`strategy/gold_position.py` + `backtest/gold_position.py` — not to be
confused with `gold_swing.py`, which despite its name is actually intraday
(5-minute entries, max 8h hold, never overnight). This is the real thing:
entries on daily bars, confirmed by weekly/monthly trend, holds of days to
weeks. Entry logic isn't reinvented — it reuses `stophunt_signal`,
`breakout_signal`, and `divergence_signal` from the 1-minute/5-minute work,
just handed daily bars with day-scale parameters instead of minute-scale
ones.

**The decisive advantage over every other timeframe in this project**:
Yahoo has 25+ years of daily gold futures history (`GC=F`, 2000-08-30
onward), vs. ~7-8 days at 1-minute or ~60 days at 5-minute. That's enough
to do a **genuine train/test split by calendar period** — discover on one
era, validate on a completely separate, later, never-touched era — instead
of splitting one continuous window after the fact (which is all that was
possible at 1-minute or 5-minute, and is exactly what caught the false
"breakthrough" in the 5-minute section above).

**Discovery (train: 2000-08-30 to 2017-12-29, 4,346 bars)**: `stop-hunt`
doesn't transfer to this timeframe (87 trades, avg R -0.03). `breakout` and
`divergence` (RSI momentum fading against a new price extreme) both look
strong — `divergence` especially: **every one of 12 exit-parameter
combinations tested came back with positive avg R** (0.18 to 0.78), not
just one lucky cell.

**Validation (test: 2018-01-02 to 2026-09-22, 2,194 bars — spans the
2018-2019 range, the 2020 COVID crash/spike, the 2022-2023 rate-hike bear
market, and the recent rally — never touched until config was chosen from
train alone):**

| Config | Train Avg R | Test Avg R | Test Win% | Test Trades | Test Max DD |
|---|---|---|---|---|---|
| divergence, 1.5x ATR / 3:1 RR / 40d hold | 0.78 | 0.64 | 42.9% | 35 | 5.6% |
| divergence, 1.5x ATR / 2:1 RR / 20d hold | 0.39 | 0.24 | 43.6% | 39 | 5.76% |
| divergence, 2.5x ATR / 2:1 RR / 20d hold | 0.39 | 0.32 | 55.6% | 27 | 3.48% |
| breakout, 2.5x ATR / 3:1 RR / 40d hold | 0.31 | 0.43 | 42.6% | 47 | 4.03% |

**Every config held its sign and stayed in the same ballpark on genuinely
unseen data.** This is qualitatively different from the 5-minute result
above, which flipped from strongly negative to strongly positive between
the two halves of one sample — here, train and test agree.

**Spread-cost tested on the held-out period and barely moves at all**:
avg R for the best config goes 0.64 → 0.63 ($0.40 spread) → 0.61 ($1.00
spread wide). At this hold length (days to weeks), the dollar move per
trade dwarfs a few cents of spread, so this timeframe is close to
spread-immune — a real structural advantage over every intraday result in
this project, where spread cost was consistently the thing that killed or
badly dented the edge.

**Bottom line**: this is the first strategy in this project validated with
genuine, independent, multi-year, multi-regime out-of-sample testing, and
it passed. `divergence, 2.5x ATR / 2:1 RR / 20d hold` is the most
conservative pick (smallest train→test drop-off: 0.39→0.32, highest win
rate, lowest drawdown) and is the default in `config_position.py`.

**Live implementation — built.** `main_gold_position.py` runs it: checks
every 6 hours (not continuously — a daily strategy has nothing new to see
between one day's close and the next), on its own **separate OANDA
practice account** (`OANDA_POSITION_API_TOKEN`/`OANDA_POSITION_ACCOUNT_ID`
in `.env`) so it never fights the 1-minute bot over the same `XAU_USD`
position slot. Two things done differently from `main_gold.py`/`main.py`
on purpose:
- **Open-trade state is persisted to disk** (`logs/position_state.py`),
  not kept in memory only — a 10-40 day hold is far more likely to outlive
  a phone restart than a 10-minute scalp is.
- **Its own status/activity log files** (`logs/position_status.json`,
  `logs/position_activity.jsonl`, via new optional `path=` parameters on
  `status_writer.write_status`/`activity_log.log_activity`) so it doesn't
  collide with the 1-minute bot's `logs/status.json`/`activity.jsonl`.

Verified against the real second OANDA practice account (not just stubs):
`get_equity()`, `is_tradeable()`, `get_current_spread()`, and
`get_recent_daily_bars()` all confirmed working. Real-money-relevant
observation from that live check: current gold price (~$4,300) is more
than double every level used in this project's backtests when they were
first run (~$2,000) — though confirmed Yahoo's `GC=F` data is current, not
stale (most recent closes ~$4,370-4,425, matching OANDA's live XAU_USD
closely). The live spread observed was $1.61, wider than the "$1.00 =
wide" spread test used everywhere else in this project.

**Re-tested at the actual observed $1.61 spread — still holds.** Re-ran
the held-out test period (2018-2026) at $1.61 instead of the old $1.00
assumption:

| Config | Avg R: $0 | $0.40 | $1.00 | **$1.61 (actual live)** |
|---|---|---|---|---|
| divergence, 1.5x/3:1/40d | 0.64 | 0.63 | 0.61 | **0.59** |
| divergence, 2.5x/2:1/20d (default) | 0.32 | 0.31 | 0.30 | **0.29** |
| breakout, 2.5x/3:1/40d | 0.43 | 0.42 | 0.41 | **0.40** |

Barely moves at any spread level tested, including the real one observed
live today. The spread-immunity claim holds at actual current market
conditions, not just the backtest's original assumptions — this timeframe
really is close to spread-cost-immune, confirmed rather than assumed.

## Running it on your phone (Termux/Android)

See [`termux/README.md`](termux/README.md) — runs `main_gold.py` directly on
an Android phone via Termux + a Debian environment (`proot-distro`), with
scripts to keep it alive in the background and auto-start on reboot. The code
is also pushed to a private GitHub repo
(`github.com/keabetswe-reisiger/trading-bot`) so it can be pulled onto any
device, not just this one.
