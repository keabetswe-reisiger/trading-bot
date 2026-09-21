"""Fair Value Gap (FVG) detection — a 3-candle price imbalance: the middle
candle's momentum leaves a gap between candle[i-2]'s high/low and
candle[i]'s low/high that price never traded through. Unlike supply/demand
zones or trendlines, this has an unambiguous, arithmetic definition — no
subjective drawing involved.

Used here as an extra directional confirmation on top of an existing entry
signal (a recent unfilled gap in the trade's direction suggests real
momentum was behind the move), not as a standalone trigger.
"""

import pandas as pd


def has_recent_bullish_fvg(bars: pd.DataFrame, lookback: int = 20) -> bool:
    """An unfilled bullish gap: candle[i-2].high < candle[i].low, and no
    later low has traded back down into that gap."""
    window = bars.tail(lookback).reset_index(drop=True)
    n = len(window)
    for i in range(2, n):
        gap_bottom = window["high"].iloc[i - 2]
        gap_top = window["low"].iloc[i]
        if gap_bottom >= gap_top:
            continue
        later_lows = window["low"].iloc[i + 1 :]
        filled = bool((later_lows <= gap_top).any())
        if not filled:
            return True
    return False


def has_recent_bearish_fvg(bars: pd.DataFrame, lookback: int = 20) -> bool:
    """An unfilled bearish gap: candle[i-2].low > candle[i].high, and no
    later high has traded back up into that gap."""
    window = bars.tail(lookback).reset_index(drop=True)
    n = len(window)
    for i in range(2, n):
        gap_top = window["low"].iloc[i - 2]
        gap_bottom = window["high"].iloc[i]
        if gap_bottom >= gap_top:
            continue
        later_highs = window["high"].iloc[i + 1 :]
        filled = bool((later_highs >= gap_bottom).any())
        if not filled:
            return True
    return False


def confirms_long(bars: pd.DataFrame, lookback: int = 20) -> bool:
    return has_recent_bullish_fvg(bars, lookback)


def confirms_short(bars: pd.DataFrame, lookback: int = 20) -> bool:
    return has_recent_bearish_fvg(bars, lookback)
