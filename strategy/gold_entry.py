"""Gold-specific entry trigger.

The plain EMA-crossover trigger (strategy.scalp_strategy.generate_signal)
was built and tuned against stock behavior. Backtesting it on real gold
1-minute data showed a specific failure mode: with tight ATR-based stops,
most trades got stopped out within 0-2 minutes of entry, and with looser
percent-based stops most just timed out flat. Both point at the same cause —
the crossover fires right as a short-lived 1-minute move is already
exhausting itself (it's a lagging trigger by construction), so it's often
chasing a spike that immediately reverts rather than catching a real
continuation.

This trigger instead requires a *pullback*: price must retreat toward the
fast EMA (within a small ATR-scaled band) and then close back through it in
the trend direction, on a same-direction candle. That's "buy the dip within
an uptrend," not "buy because two lines just crossed."

It also restricts entries to the London/New York trading window, since
24-hour tick volume on gold is heavily concentrated there — the overnight
Asian-session hours are thin and choppy, which is exactly the kind of noise
a lagging crossover trigger is most likely to misfire on.
"""

import pandas as pd

from strategy.exits import atr
from strategy.scalp_strategy import compute_indicators

ACTIVE_HOURS_UTC = (7, 20)  # [start, end) — roughly London open through NY close


def in_active_session(timestamp, restrict: bool = True) -> bool:
    if not restrict:
        return True
    start, end = ACTIVE_HOURS_UTC
    return start <= timestamp.hour < end


def pullback_signal(
    bars: pd.DataFrame,
    *,
    fast: int = 9,
    slow: int = 21,
    rsi_period: int = 14,
    atr_period: int = 14,
    pullback_atr_mult: float = 0.5,
    restrict_session: bool = True,
) -> str | None:
    min_len = max(slow, rsi_period, atr_period) + 2
    if len(bars) < min_len:
        return None
    if not in_active_session(bars.index[-1], restrict_session):
        return None

    ind = compute_indicators(bars, fast=fast, slow=slow, rsi_period=rsi_period)
    atr_series = atr(bars, atr_period)
    atr_value = atr_series.iloc[-1]
    if pd.isna(atr_value) or atr_value <= 0:
        return None

    prev, last = ind.iloc[-2], ind.iloc[-1]
    band = pullback_atr_mult * atr_value

    uptrend = last["ema_fast"] > last["ema_slow"]
    downtrend = last["ema_fast"] < last["ema_slow"]

    pulled_back_to_ema_from_above = prev["low"] <= prev["ema_fast"] + band
    closed_back_above = last["close"] > last["ema_fast"] and last["close"] > last["open"]

    pulled_back_to_ema_from_below = prev["high"] >= prev["ema_fast"] - band
    closed_back_below = last["close"] < last["ema_fast"] and last["close"] < last["open"]

    # RSI is checked on the pullback bar (prev), not the confirmation candle
    # (last) — a strong breakout bar naturally pushes RSI up on its own, so
    # gating on last's RSI would reject exactly the candles this is meant to
    # catch. Checking prev confirms the pullback actually cooled momentum
    # first, rather than buying into an already-overextended run.
    if uptrend and pulled_back_to_ema_from_above and closed_back_above and prev["rsi"] < 75 and last["close"] > last["vwap"]:
        return "long"
    if downtrend and pulled_back_to_ema_from_below and closed_back_below and prev["rsi"] > 25 and last["close"] < last["vwap"]:
        return "short"
    return None
