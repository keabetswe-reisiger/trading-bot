import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


def _list(name: str, default: str) -> list[str]:
    return [s.strip().upper() for s in os.getenv(name, default).split(",") if s.strip()]


ALPACA_API_KEY_ID = os.getenv("ALPACA_API_KEY_ID", "")
ALPACA_API_SECRET_KEY = os.getenv("ALPACA_API_SECRET_KEY", "")
ALPACA_PAPER = _bool("ALPACA_PAPER", "true")

SYMBOLS = _list("SYMBOLS", "AAPL,MSFT")

RISK_PER_TRADE_PCT = float(os.getenv("RISK_PER_TRADE_PCT", "1.0"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "3.0"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "2"))
MIN_AVG_VOLUME = int(os.getenv("MIN_AVG_VOLUME", "2000"))

STOP_MODE = os.getenv("STOP_MODE", "atr")  # "atr" (volatility-adjusted) or "pct" (fixed percent)
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.3"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.15"))
ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
ATR_STOP_MULTIPLIER = float(os.getenv("ATR_STOP_MULTIPLIER", "1.5"))
REWARD_RISK_RATIO = float(os.getenv("REWARD_RISK_RATIO", "2.0"))
MAX_HOLD_MINUTES = int(os.getenv("MAX_HOLD_MINUTES", "10"))

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

if not ALPACA_API_KEY_ID or not ALPACA_API_SECRET_KEY:
    raise RuntimeError(
        "Missing ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY. "
        "Copy .env.example to .env and fill in your Alpaca PAPER keys."
    )
