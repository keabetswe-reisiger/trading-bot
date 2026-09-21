"""0.886 Fibonacci retracement filter, from the Chris Creamer gold-trading
video breakdown: a pullback is only "valid" if it hasn't retraced past the
0.886 level of the prior swing — beyond that, the setup is considered
invalidated rather than a legitimate discount/premium entry.

Reuses the same causal swing-point detection as strategy/gold_price_action.py.
"""

import pandas as pd

from strategy.gold_price_action import confirmed_extrema


def holds_long(bars: pd.DataFrame, swing_order: int = 3) -> bool:
    """For a long: current price must still be above the 0.886 retracement
    of the most recent swing-low-to-swing-high move."""
    highs = confirmed_extrema(bars, "high", is_high=True, order=swing_order, max_count=1)
    lows = confirmed_extrema(bars, "low", is_high=False, order=swing_order, max_count=1)
    if not highs or not lows:
        return False
    _, swing_high = highs[0]
    _, swing_low = lows[0]
    if swing_high <= swing_low:
        return False
    level_886 = swing_high - 0.886 * (swing_high - swing_low)
    return bars["close"].iloc[-1] >= level_886


def holds_short(bars: pd.DataFrame, swing_order: int = 3) -> bool:
    """Mirror of holds_long for shorts."""
    highs = confirmed_extrema(bars, "high", is_high=True, order=swing_order, max_count=1)
    lows = confirmed_extrema(bars, "low", is_high=False, order=swing_order, max_count=1)
    if not highs or not lows:
        return False
    _, swing_high = highs[0]
    _, swing_low = lows[0]
    if swing_high <= swing_low:
        return False
    level_886 = swing_low + 0.886 * (swing_high - swing_low)
    return bars["close"].iloc[-1] <= level_886
