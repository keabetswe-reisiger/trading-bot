"""Settings for the OANDA XAU_USD (gold) bot — independent of config.py
(the Alpaca stock bot's settings) so this can run without Alpaca keys."""

import os

from dotenv import load_dotenv

load_dotenv()

OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")  # "practice" or "live"

INSTRUMENT = os.getenv("GOLD_INSTRUMENT", "XAU_USD")

RISK_PER_TRADE_PCT = float(os.getenv("GOLD_RISK_PER_TRADE_PCT", "1.0"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("GOLD_DAILY_LOSS_LIMIT_PCT", "3.0"))
MAX_OPEN_POSITIONS = int(os.getenv("GOLD_MAX_OPEN_POSITIONS", "1"))
# 0 = disabled. Stop trading for the day after this many losses in a row.
MAX_CONSECUTIVE_LOSSES = int(os.getenv("GOLD_MAX_CONSECUTIVE_LOSSES", "2"))
# 0 = disabled. Safety cap: position notional value can't exceed this % of
# equity (500% ~= 5x), regardless of what risk-based sizing alone computes.
MAX_POSITION_VALUE_PCT = float(os.getenv("GOLD_MAX_POSITION_VALUE_PCT", "500"))
# OANDA reports tick volume (price updates), not real traded volume, for FX/metals.
# Left at 0 (disabled) by default until you've observed a sane baseline for XAU_USD.
MIN_AVG_VOLUME = int(os.getenv("GOLD_MIN_AVG_VOLUME", "0"))

ENTRY_MODE = os.getenv("GOLD_ENTRY_MODE", "stophunt")  # "stophunt" (default), "breakout", "quality", "pullback", "divergence", or "crossover"
# Only applies when ENTRY_MODE=quality: how many times the recent average
# volume the trigger bar's volume must reach (VSA "Stopping Volume"). Higher
# = fewer, higher-conviction trades (backtested 1.3-2.0; 1.5 is the
# best-balanced point - see strategy.volume_confirmation.has_stopping_volume).
QUALITY_VOLUME_MULTIPLIER = float(os.getenv("GOLD_QUALITY_VOLUME_MULTIPLIER", "1.5"))
RESTRICT_SESSION = os.getenv("GOLD_RESTRICT_SESSION", "true").strip().lower() in ("1", "true", "yes")
# Only applies when ENTRY_MODE=stophunt. Requires an engulfing candle or pin
# bar on the trigger bar too — best-tested combination so far (+13.8% vs
# +5.3% without it on the same week), but only validated on one data window.
REQUIRE_CANDLE_CONFIRM = os.getenv("GOLD_REQUIRE_CANDLE_CONFIRM", "true").strip().lower() in ("1", "true", "yes")

# Live safety guard only — not backtestable (Yahoo's GC=F data has no real
# bid/ask history). $0.50 sits between README's own "$0.40 = typical" and
# "$1.00 = wide, kills the edge" spread-cost test bracket. Checked once a
# signal fires, before the order is submitted.
MAX_SPREAD = float(os.getenv("GOLD_MAX_SPREAD", "0.50"))

STOP_MODE = os.getenv("GOLD_STOP_MODE", "atr")
TAKE_PROFIT_PCT = float(os.getenv("GOLD_TAKE_PROFIT_PCT", "0.3"))
STOP_LOSS_PCT = float(os.getenv("GOLD_STOP_LOSS_PCT", "0.15"))
ATR_PERIOD = int(os.getenv("GOLD_ATR_PERIOD", "14"))
ATR_STOP_MULTIPLIER = float(os.getenv("GOLD_ATR_STOP_MULTIPLIER", "1.5"))
REWARD_RISK_RATIO = float(os.getenv("GOLD_REWARD_RISK_RATIO", "2.0"))
MAX_HOLD_MINUTES = int(os.getenv("GOLD_MAX_HOLD_MINUTES", "10"))

POLL_INTERVAL_SECONDS = int(os.getenv("GOLD_POLL_INTERVAL_SECONDS", "30"))

if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
    raise RuntimeError(
        "Missing OANDA_API_TOKEN / OANDA_ACCOUNT_ID. "
        "Add them to .env — see .env.example for the OANDA section."
    )
