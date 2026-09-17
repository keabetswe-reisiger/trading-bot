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
# OANDA reports tick volume (price updates), not real traded volume, for FX/metals.
# Left at 0 (disabled) by default until you've observed a sane baseline for XAU_USD.
MIN_AVG_VOLUME = int(os.getenv("GOLD_MIN_AVG_VOLUME", "0"))

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
