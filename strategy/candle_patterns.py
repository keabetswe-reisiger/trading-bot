"""Standard candlestick confirmation patterns (engulfing, pin bar) — meant
to be combined with an existing entry signal as an extra confirmation
filter, not used standalone. These are well-established, unambiguous
patterns (unlike supply/demand zones or trendlines), so they're worth
testing; "3-bar reversal/continuation" and "shrinking candles" from the
video weren't implemented — no verifiable definition or backing data was
shown for those beyond the presenter's own claim.
"""

import pandas as pd


def is_bullish_engulfing(bars: pd.DataFrame) -> bool:
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bearish = prev["close"] < prev["open"]
    last_bullish = last["close"] > last["open"]
    engulfs = last["open"] <= prev["close"] and last["close"] >= prev["open"]
    return bool(prev_bearish and last_bullish and engulfs)


def is_bearish_engulfing(bars: pd.DataFrame) -> bool:
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bullish = prev["close"] > prev["open"]
    last_bearish = last["close"] < last["open"]
    engulfs = last["open"] >= prev["close"] and last["close"] <= prev["open"]
    return bool(prev_bullish and last_bearish and engulfs)


def is_bullish_pin_bar(bars: pd.DataFrame, wick_ratio: float = 2.0) -> bool:
    if len(bars) < 1:
        return False
    last = bars.iloc[-1]
    body = abs(last["close"] - last["open"])
    if body <= 0:
        return False
    lower_wick = min(last["open"], last["close"]) - last["low"]
    upper_wick = last["high"] - max(last["open"], last["close"])
    return bool(lower_wick >= wick_ratio * body and lower_wick > upper_wick)


def is_bearish_pin_bar(bars: pd.DataFrame, wick_ratio: float = 2.0) -> bool:
    if len(bars) < 1:
        return False
    last = bars.iloc[-1]
    body = abs(last["close"] - last["open"])
    if body <= 0:
        return False
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    return bool(upper_wick >= wick_ratio * body and upper_wick > lower_wick)


def confirms_long(bars: pd.DataFrame) -> bool:
    return is_bullish_engulfing(bars) or is_bullish_pin_bar(bars)


def confirms_short(bars: pd.DataFrame) -> bool:
    return is_bearish_engulfing(bars) or is_bearish_pin_bar(bars)
