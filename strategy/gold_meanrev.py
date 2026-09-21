"""Bollinger Band mean-reversion entry — fade a touch of the band back
toward the mean, filtered by RSI.

Tested with multi-timeframe confirmation added at several strictness levels
(an improvement that helped the stop-hunt signal a lot) specifically to try
for higher trade frequency (~1/hour) than stop-hunt's ~1/2.5hrs. Every
confirmation level still lost money (-2.4% to -3.6%) on real GC=F data —
confirmation didn't rescue this one the way it did stop-hunt. Not adopted
as the default; kept here as a documented, tested dead end rather than
deleted, so it isn't re-tried from scratch later.
"""

import pandas as pd

from strategy.scalp_strategy import _rsi


def bb_signal(bars: pd.DataFrame, period: int = 20, std_mult: float = 2.0, rsi_period: int = 14) -> str | None:
    if len(bars) < period + 2:
        return None
    close = bars["close"]
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    rsi = _rsi(close, rsi_period)

    prev_close, last_close = close.iloc[-2], close.iloc[-1]
    prev_upper, last_upper = upper.iloc[-2], upper.iloc[-1]
    prev_lower, last_lower = lower.iloc[-2], lower.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    if pd.isna(prev_upper) or pd.isna(prev_rsi):
        return None

    if prev_close >= prev_upper and last_close < last_upper and prev_rsi > 70:
        return "short"
    if prev_close <= prev_lower and last_close > last_lower and prev_rsi < 30:
        return "long"
    return None
