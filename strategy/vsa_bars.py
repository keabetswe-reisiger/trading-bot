"""Single-bar Volume Spread Analysis (VSA) reads, from Tom Williams' "Master
the Markets" (Wyckoff tradition) — distinct from strategy/volume_confirmation.py's
"Stopping Volume" (a climax-style high-volume reversal bar). These two read
the *opposite* case: a bar that looks directionally fine on price alone, but
whose volume gives away that professional money isn't behind the move.

No Demand: an up-bar with volume less than the previous two bars' — weak
buying, a bearish tell despite the up close. No Supply: a down-bar with
volume less than the previous two bars' and closing in the middle or high
of its range — no real selling pressure, a bullish tell despite the down
close. Both are defined in the book as "especially" when the bar's spread
is narrow relative to recent bars, so narrow spread is required here, not
optional — a wide-spread low-volume bar is a different (weaker) read.
"""

import pandas as pd


def _spread(bar: pd.Series) -> float:
    return float(bar["high"] - bar["low"])


def _is_narrow_spread(bars: pd.DataFrame, lookback: int = 10) -> bool:
    if len(bars) < lookback + 1:
        return False
    recent_spreads = (bars["high"] - bars["low"]).iloc[-(lookback + 1) : -1]
    avg_spread = recent_spreads.mean()
    if avg_spread <= 0:
        return False
    return _spread(bars.iloc[-1]) < avg_spread


def no_demand(bars: pd.DataFrame, lookback: int = 10) -> bool:
    """Up-bar, narrow spread, volume below the previous two bars'."""
    if len(bars) < 3:
        return False
    last = bars.iloc[-1]
    if last["close"] <= last["open"]:
        return False
    if not _is_narrow_spread(bars, lookback):
        return False
    prev_vols = bars["volume"].iloc[-3:-1]
    return bool(last["volume"] < prev_vols.min())


def no_supply(bars: pd.DataFrame, lookback: int = 10) -> bool:
    """Down-bar, narrow spread, volume below the previous two bars', closing
    in the middle or high of its own range (not on the low)."""
    if len(bars) < 3:
        return False
    last = bars.iloc[-1]
    if last["close"] >= last["open"]:
        return False
    if not _is_narrow_spread(bars, lookback):
        return False
    prev_vols = bars["volume"].iloc[-3:-1]
    if not bool(last["volume"] < prev_vols.min()):
        return False
    bar_range = last["high"] - last["low"]
    if bar_range <= 0:
        return True
    close_position = (last["close"] - last["low"]) / bar_range
    return bool(close_position >= 0.5)
