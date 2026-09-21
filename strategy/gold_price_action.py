"""Two price-action ideas from a gold trading education video, made concrete
and testable (the video's other two ideas — supply/demand zones and
trendline breakouts — were left out because they require subjective manual
judgment to draw, which can't be turned into an unambiguous, backtestable
rule without just inventing an arbitrary version of them).

1. Liquidity sweep at support/resistance ("stop hunt"): price wicks past a
   recent swing high/low — where stop-losses commonly cluster — then closes
   back on the other side. The wick is read as the reversal trigger.

2. RSI divergence: price makes a new swing high/low but RSI doesn't confirm
   it (a lower RSI peak on a higher price peak, or vice versa) — read as
   fading momentum ahead of a reversal.

Swing points are detected causally: a bar only counts as a confirmed swing
high/low once `order` bars have passed after it (you can't know a bar was a
local extreme until you've seen what came after it), so neither signal here
uses information from the future relative to when it fires.
"""

import pandas as pd

from strategy.scalp_strategy import compute_indicators


def confirmed_extrema(bars: pd.DataFrame, column: str, is_high: bool, order: int = 3, max_count: int = 2, min_gap: int | None = None):
    """Most recent confirmed swing points in `column`, newest first.
    Returns list of (positional_index, price) tuples.

    min_gap enforces a minimum bar distance between accepted points so two
    adjacent bars on the same rounded peak/trough aren't both counted as
    separate "swings" (which would make a two-swing divergence comparison
    meaningless — it needs two genuinely distinct moves, not two samples of
    the same one). Defaults to 3x order.
    """
    if min_gap is None:
        min_gap = order * 3
    series = bars[column]
    n = len(series)
    found = []
    last_i = None
    # Start at n-1-order: the most recent bar with `order` bars fully after it.
    for i in range(n - 1 - order, order - 1, -1):
        if last_i is not None and last_i - i < min_gap:
            continue
        window = series.iloc[i - order : i + order + 1]
        extreme = window.max() if is_high else window.min()
        if series.iloc[i] == extreme:
            found.append((i, series.iloc[i]))
            last_i = i
            if len(found) >= max_count:
                break
    return found


def stophunt_signal(bars: pd.DataFrame, lookback: int = 40, swing_order: int = 3) -> str | None:
    """Wick sweeps a recent swing high/low, then closes back on the other side."""
    if len(bars) < lookback:
        return None
    window = bars.tail(lookback)
    last = window.iloc[-1]

    prior_highs = confirmed_extrema(window.iloc[:-1], "high", is_high=True, order=swing_order, max_count=1)
    prior_lows = confirmed_extrema(window.iloc[:-1], "low", is_high=False, order=swing_order, max_count=1)

    if prior_highs:
        _, swing_high = prior_highs[0]
        if last["high"] > swing_high and last["close"] < swing_high and last["close"] < last["open"]:
            return "short"

    if prior_lows:
        _, swing_low = prior_lows[0]
        if last["low"] < swing_low and last["close"] > swing_low and last["close"] > last["open"]:
            return "long"

    return None


def divergence_signal(bars: pd.DataFrame, lookback: int = 60, swing_order: int = 3, rsi_period: int = 14) -> str | None:
    """Price makes a new swing extreme that RSI doesn't confirm, then the
    current bar shows the actual reversal (a same-direction candle)."""
    if len(bars) < lookback:
        return None
    window = bars.tail(lookback).reset_index(drop=True)
    ind = compute_indicators(window, rsi_period=rsi_period)
    last = window.iloc[-1]

    highs = confirmed_extrema(window.iloc[:-1], "high", is_high=True, order=swing_order, max_count=2)
    if len(highs) == 2:
        (i1, p1), (i2, p2) = highs  # i1/p1 = more recent, i2/p2 = prior
        rsi1, rsi2 = ind["rsi"].iloc[i1], ind["rsi"].iloc[i2]
        if p1 > p2 and rsi1 < rsi2 and last["close"] < last["open"]:
            return "short"

    lows = confirmed_extrema(window.iloc[:-1], "low", is_high=False, order=swing_order, max_count=2)
    if len(lows) == 2:
        (i1, p1), (i2, p2) = lows
        rsi1, rsi2 = ind["rsi"].iloc[i1], ind["rsi"].iloc[i2]
        if p1 < p2 and rsi1 > rsi2 and last["close"] > last["open"]:
            return "long"

    return None
