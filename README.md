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

**Current honest result**: a 12-combination sweep over ATR stop multiplier
(1.0–2.0), reward:risk (1.5–2.0) and max-hold-time (15/30 min) against one
week of real `GC=F` 1-minute data lost money in **every single combination**
(-3.0% to -3.7%, 14-29% win rate). Exit tuning can't fix a losing entry
signal — it only moves losses around. This means the stock-tuned EMA/RSI/VWAP
entry logic does not currently show an edge on gold in this sample. Treat the
gold bot as **not validated** until either a longer/different backtest window
shows different results, or the entry logic itself is reworked for gold's
behavior specifically. Running it on the OANDA demo account is still safe
(zero real money) and useful as further forward-testing data, just don't
mistake "it's running" for "it's proven to work."

## Running it on your phone (Termux/Android)

See [`termux/README.md`](termux/README.md) — runs `main_gold.py` directly on
an Android phone via Termux + a Debian environment (`proot-distro`), with
scripts to keep it alive in the background and auto-start on reboot. The code
is also pushed to a private GitHub repo
(`github.com/keabetswe-reisiger/trading-bot`) so it can be pulled onto any
device, not just this one.
