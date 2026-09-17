"""Multi-timeframe confirmation for the scalp strategy.

Higher timeframes (1h/30m/20m/15m) establish the underlying trend direction.
The 1-minute timeframe still generates the actual entry trigger
(strategy.scalp_strategy.generate_signal). A 1-minute entry only fires if
enough of the higher timeframes already agree with its direction — this
trades fewer, better-confirmed setups instead of every 1-minute wiggle.
"""

import pandas as pd
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from strategy.scalp_strategy import compute_indicators, generate_signal

TIMEFRAMES: dict[str, TimeFrame] = {
    "1h": TimeFrame(1, TimeFrameUnit.Hour),
    "30m": TimeFrame(30, TimeFrameUnit.Minute),
    "20m": TimeFrame(20, TimeFrameUnit.Minute),
    "15m": TimeFrame(15, TimeFrameUnit.Minute),
    "5m": TimeFrame(5, TimeFrameUnit.Minute),
    "3m": TimeFrame(3, TimeFrameUnit.Minute),
    "1m": TimeFrame(1, TimeFrameUnit.Minute),
}

TREND_TIMEFRAMES = ["1h", "30m", "20m", "15m"]
CONFIRM_TIMEFRAMES = ["5m", "3m"]  # extra confluence, between trend and entry
ENTRY_TIMEFRAME = "1m"


def trend_bias(bars: pd.DataFrame, fast: int = 9, slow: int = 21) -> str | None:
    """Which way is this timeframe leaning right now? None = no clear lean."""
    if len(bars) < slow + 1:
        return None
    ind = compute_indicators(bars, fast=fast, slow=slow)
    last = ind.iloc[-1]
    if last["ema_fast"] > last["ema_slow"] and last["close"] > last["vwap"]:
        return "long"
    if last["ema_fast"] < last["ema_slow"] and last["close"] < last["vwap"]:
        return "short"
    return None


def aligned_signal(
    bars_by_tf: dict[str, pd.DataFrame],
    min_trend_agree: int = 3,
    min_confirm_agree: int = 1,
    min_avg_volume: int = 0,
) -> str | None:
    """Entry timeframe fires first; higher timeframes must confirm the direction.

    bars_by_tf: {"1h": df, "30m": df, ..., "1m": df} — whichever of TIMEFRAMES
    keys you fetched. Missing keys are treated as "no opinion", not a veto.
    """
    entry_signal = generate_signal(bars_by_tf.get(ENTRY_TIMEFRAME, pd.DataFrame()), min_avg_volume=min_avg_volume)
    if entry_signal is None:
        return None

    trend_votes = [trend_bias(bars_by_tf[tf]) for tf in TREND_TIMEFRAMES if tf in bars_by_tf]
    trend_agree = sum(1 for v in trend_votes if v == entry_signal)

    confirm_votes = [trend_bias(bars_by_tf[tf]) for tf in CONFIRM_TIMEFRAMES if tf in bars_by_tf]
    confirm_agree = sum(1 for v in confirm_votes if v == entry_signal)

    if trend_agree >= min_trend_agree and confirm_agree >= min_confirm_agree:
        return entry_signal
    return None
