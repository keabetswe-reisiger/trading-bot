"""Break-and-close continuation trigger — the mirror image of stop-hunt.

Stop-hunt (strategy/gold_price_action.py) is a reversal trigger: price
sweeps past a level, then closes back on the other side. This is a
continuation trigger instead: price closes cleanly beyond a recent swing
high/low (without reversing back), expecting the breakout to continue.
From the "1PercentClub" price-action video breakdown — "break-and-close in
the direction of your bias."
"""

import pandas as pd

from strategy.gold_price_action import confirmed_extrema


def breakout_signal(bars: pd.DataFrame, lookback: int = 40, swing_order: int = 3) -> str | None:
    if len(bars) < lookback:
        return None
    window = bars.tail(lookback)
    last, prev = window.iloc[-1], window.iloc[-2]

    prior_highs = confirmed_extrema(window.iloc[:-1], "high", is_high=True, order=swing_order, max_count=1)
    if prior_highs:
        _, swing_high = prior_highs[0]
        # Fresh break: previous close was still at/below the level, this
        # candle closes clearly above it with a same-direction body.
        if prev["close"] <= swing_high and last["close"] > swing_high and last["close"] > last["open"]:
            return "long"

    prior_lows = confirmed_extrema(window.iloc[:-1], "low", is_high=False, order=swing_order, max_count=1)
    if prior_lows:
        _, swing_low = prior_lows[0]
        if prev["close"] >= swing_low and last["close"] < swing_low and last["close"] < last["open"]:
            return "short"

    return None
