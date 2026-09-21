"""Standard candlestick confirmation patterns — meant to be combined with
an existing entry signal as an extra confirmation filter, not used
standalone. These are well-established, unambiguous patterns (unlike
supply/demand zones or trendlines), so they're worth testing; "3-bar
reversal/continuation" and "shrinking candles" from an earlier video
weren't implemented — no verifiable definition or backing data was shown
for those beyond the presenter's own claim.

Dragonfly/Gravestone Doji, Harami, and Tweezers Top/Bottom added after
reviewing a candlestick-pattern reference PDF — standard, textbook-defined
patterns, same category as engulfing/pin bar.
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


def is_dragonfly_doji(bars: pd.DataFrame, body_ratio: float = 0.1, wick_ratio: float = 2.0) -> bool:
    """Tiny body near the top of the range, long lower wick, ~no upper wick."""
    if len(bars) < 1:
        return False
    last = bars.iloc[-1]
    full_range = last["high"] - last["low"]
    if full_range <= 0:
        return False
    body = abs(last["close"] - last["open"])
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    return bool(body <= body_ratio * full_range and lower_wick >= wick_ratio * max(body, full_range * 0.01) and upper_wick <= 0.1 * full_range)


def is_gravestone_doji(bars: pd.DataFrame, body_ratio: float = 0.1, wick_ratio: float = 2.0) -> bool:
    """Tiny body near the bottom of the range, long upper wick, ~no lower wick."""
    if len(bars) < 1:
        return False
    last = bars.iloc[-1]
    full_range = last["high"] - last["low"]
    if full_range <= 0:
        return False
    body = abs(last["close"] - last["open"])
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    return bool(body <= body_ratio * full_range and upper_wick >= wick_ratio * max(body, full_range * 0.01) and lower_wick <= 0.1 * full_range)


def is_bullish_harami(bars: pd.DataFrame) -> bool:
    """Large bearish candle followed by a smaller bullish candle fully
    contained within the first candle's body — momentum stalling."""
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bearish = prev["close"] < prev["open"]
    last_bullish = last["close"] > last["open"]
    contained = last["open"] >= prev["close"] and last["close"] <= prev["open"]
    return bool(prev_bearish and last_bullish and contained)


def is_bearish_harami(bars: pd.DataFrame) -> bool:
    """Mirror of is_bullish_harami."""
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bullish = prev["close"] > prev["open"]
    last_bearish = last["close"] < last["open"]
    contained = last["open"] <= prev["close"] and last["close"] >= prev["open"]
    return bool(prev_bullish and last_bearish and contained)


def is_tweezer_bottom(bars: pd.DataFrame, tolerance_pct: float = 0.05) -> bool:
    """Two candles with matching lows (within tolerance), bearish then
    bullish — a rejected level."""
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bearish = prev["close"] < prev["open"]
    last_bullish = last["close"] > last["open"]
    avg_range = ((prev["high"] - prev["low"]) + (last["high"] - last["low"])) / 2
    if avg_range <= 0:
        return False
    lows_match = abs(prev["low"] - last["low"]) <= tolerance_pct * avg_range
    return bool(prev_bearish and last_bullish and lows_match)


def is_tweezer_top(bars: pd.DataFrame, tolerance_pct: float = 0.05) -> bool:
    """Mirror of is_tweezer_bottom."""
    if len(bars) < 2:
        return False
    prev, last = bars.iloc[-2], bars.iloc[-1]
    prev_bullish = prev["close"] > prev["open"]
    last_bearish = last["close"] < last["open"]
    avg_range = ((prev["high"] - prev["low"]) + (last["high"] - last["low"])) / 2
    if avg_range <= 0:
        return False
    highs_match = abs(prev["high"] - last["high"]) <= tolerance_pct * avg_range
    return bool(prev_bullish and last_bearish and highs_match)


def confirms_long(bars: pd.DataFrame) -> bool:
    """Narrow set (engulfing + pin bar only) — used by stop-hunt. Backtested:
    broadening this diluted stop-hunt's result badly (avg R 0.30 -> 0.03),
    so it stays narrow here even though the broader set below helps breakout."""
    return is_bullish_engulfing(bars) or is_bullish_pin_bar(bars)


def confirms_short(bars: pd.DataFrame) -> bool:
    return is_bearish_engulfing(bars) or is_bearish_pin_bar(bars)


def confirms_long_broad(bars: pd.DataFrame) -> bool:
    """Broader set, adding doji variants/harami/tweezers — backtested to help
    breakout (17->21 trades, same avg R +0.48) but hurt stop-hunt, so this is
    only used by the breakout entry mode, not the default."""
    return (
        is_bullish_engulfing(bars)
        or is_bullish_pin_bar(bars)
        or is_dragonfly_doji(bars)
        or is_bullish_harami(bars)
        or is_tweezer_bottom(bars)
    )


def confirms_short_broad(bars: pd.DataFrame) -> bool:
    return (
        is_bearish_engulfing(bars)
        or is_bearish_pin_bar(bars)
        or is_gravestone_doji(bars)
        or is_bearish_harami(bars)
        or is_tweezer_top(bars)
    )
