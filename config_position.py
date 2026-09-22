"""Settings for the daily-bar gold swing/position bot (main_gold_position.py)
— a separate OANDA account from config_gold.py's 1-minute scalp bot on
purpose. Holds run for days-to-weeks; running it on the same account as the
1-minute bot would fight over the same XAU_USD position slot."""

import os

from dotenv import load_dotenv

load_dotenv()

OANDA_API_TOKEN = os.getenv("OANDA_POSITION_API_TOKEN", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_POSITION_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = os.getenv("OANDA_POSITION_ENVIRONMENT", "practice")  # "practice" or "live"

INSTRUMENT = os.getenv("POSITION_INSTRUMENT", "XAU_USD")

RISK_PER_TRADE_PCT = float(os.getenv("POSITION_RISK_PER_TRADE_PCT", "1.0"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("POSITION_DAILY_LOSS_LIMIT_PCT", "3.0"))
MAX_OPEN_POSITIONS = int(os.getenv("POSITION_MAX_OPEN_POSITIONS", "1"))
# 0 = disabled. Stop trading after this many losses in a row — less likely
# to matter here (a handful of trades a year) than on the scalp bots, kept
# for consistency and as a genuine circuit breaker if it ever does happen.
MAX_CONSECUTIVE_LOSSES = int(os.getenv("POSITION_MAX_CONSECUTIVE_LOSSES", "2"))
MAX_POSITION_VALUE_PCT = float(os.getenv("POSITION_MAX_POSITION_VALUE_PCT", "500"))

# Only "divergence" (RSI momentum fade) is validated for this timeframe —
# genuine independent train (2000-2017) / test (2018-2026) split, held its
# sign and magnitude on the held-out period, near spread-immune. "breakout"
# also held up in the same test but with a less consistent train->test
# match; not the default. See README.md's "Genuine multi-day swing/position
# trading" section for the full numbers.
ENTRY_MODE = os.getenv("POSITION_ENTRY_MODE", "divergence")  # "divergence" (default) or "breakout"

STOP_MODE = "atr"  # the only mode validated at this timeframe
# Most conservative validated config: train avg R 0.39 -> test avg R 0.32,
# highest test win rate (55.6%), lowest test drawdown (3.48%) of everything
# tried. See README.md for the full comparison table.
ATR_PERIOD = int(os.getenv("POSITION_ATR_PERIOD", "14"))
ATR_STOP_MULTIPLIER = float(os.getenv("POSITION_ATR_STOP_MULTIPLIER", "2.5"))
REWARD_RISK_RATIO = float(os.getenv("POSITION_REWARD_RISK_RATIO", "2.0"))
MAX_HOLD_DAYS = int(os.getenv("POSITION_MAX_HOLD_DAYS", "20"))

# Checked once a day, not polled continuously like the scalp bots — a daily
# strategy has nothing new to see between one day's close and the next.
POLL_INTERVAL_SECONDS = int(os.getenv("POSITION_POLL_INTERVAL_SECONDS", str(6 * 3600)))

if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
    raise RuntimeError(
        "Missing OANDA_POSITION_API_TOKEN / OANDA_POSITION_ACCOUNT_ID. "
        "Add them to .env — see .env.example for the position-bot section. "
        "Use a SEPARATE OANDA practice account from OANDA_API_TOKEN/OANDA_ACCOUNT_ID "
        "(config_gold.py's 1-minute bot) — running both against the same account "
        "means they'd fight over the same XAU_USD position slot."
    )
