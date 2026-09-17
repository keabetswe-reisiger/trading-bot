"""Short-timeframe scalping signal: EMA crossover + RSI filter + VWAP filter.

Rules (all must agree to fire a signal):
  LONG:  fast EMA crosses above slow EMA, RSI is not overbought (<70),
         and price is trading above VWAP (buyers in control for the session).
  SHORT: fast EMA crosses below slow EMA, RSI is not oversold (>30),
         and price is trading below VWAP.

Designed for 1-minute bars. Returns "long", "short", or None per call.
"""

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def _vwap(bars: pd.DataFrame) -> pd.Series:
    typical_price = (bars["high"] + bars["low"] + bars["close"]) / 3
    cum_vol = bars["volume"].cumsum().replace(0, 1e-9)
    return (typical_price * bars["volume"]).cumsum() / cum_vol


def compute_indicators(bars: pd.DataFrame, fast: int = 9, slow: int = 21, rsi_period: int = 14) -> pd.DataFrame:
    """bars must have columns: open, high, low, close, volume, indexed by time, oldest first."""
    out = bars.copy()
    out["ema_fast"] = _ema(out["close"], fast)
    out["ema_slow"] = _ema(out["close"], slow)
    out["rsi"] = _rsi(out["close"], rsi_period)
    out["vwap"] = _vwap(out)
    return out


def generate_signal(bars: pd.DataFrame, min_avg_volume: int = 0) -> str | None:
    """bars: recent 1-min OHLCV, at least ~25 rows, oldest first.

    min_avg_volume: skip thin symbols where scalping slippage would eat the
    edge (checked against the average volume of the last 10 bars).
    """
    if len(bars) < 25:
        return None
    if min_avg_volume and bars["volume"].tail(10).mean() < min_avg_volume:
        return None

    ind = compute_indicators(bars)
    prev, last = ind.iloc[-2], ind.iloc[-1]

    crossed_up = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]
    crossed_down = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]

    if crossed_up and last["rsi"] < 70 and last["close"] > last["vwap"]:
        return "long"
    if crossed_down and last["rsi"] > 30 and last["close"] < last["vwap"]:
        return "short"
    return None
