"""Genuine multi-day swing/position trading for gold — daily bars, holds of
days to weeks, not the hours-long "swing" in strategy/gold_swing.py (which,
despite the name, is actually intraday: 5-minute entries, max 8h hold, never
overnight). This is the real thing: entries on daily bars, confirmed by
weekly/monthly trend, holds measured in days.

The advantage over every other timeframe tested in this project: Yahoo
gives 25+ years of daily gold futures history (vs. ~7-8 days at 1-minute or
~60 days at 5-minute), so this is the first timeframe where a genuine
train/test split by calendar period is possible — discover parameters on
one era, validate on a separate, later, never-touched era. Every other
"out of sample" check in this project has been a same-window split at best.

Entry signal is deliberately not reinvented: strategy.gold_price_action's
stophunt_signal/divergence_signal and strategy.breakout's breakout_signal
already take a generic bars DataFrame and a lookback/swing_order — same
functions, just handed daily bars with day-scale parameters instead of
minute-scale ones.
"""

import pandas as pd

_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
_RULES = {"1w": "W", "1mo": "ME"}
TREND_TIMEFRAMES = ["1w", "1mo"]
ENTRY_TIMEFRAME = "1d"


def build_daily_timeframes(bars_1d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {"1d": bars_1d}
    for label, rule in _RULES.items():
        out[label] = bars_1d.resample(rule, label="right", closed="right").agg(_AGG).dropna(how="any")
    return out


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def trend_bias(bars: pd.DataFrame, fast: int = 9, slow: int = 21) -> str | None:
    """Which way is this timeframe leaning right now — no crossover required."""
    if len(bars) < slow + 1:
        return None
    close = bars["close"]
    f, s = _ema(close, fast), _ema(close, slow)
    if f.iloc[-1] > s.iloc[-1]:
        return "long"
    if f.iloc[-1] < s.iloc[-1]:
        return "short"
    return None


def aligned_signal(
    bars_by_tf: dict[str, pd.DataFrame],
    entry_signal_fn,
    min_trend_agree: int = 1,
) -> str | None:
    """entry_signal_fn: bars -> "long"/"short"/None, applied to the daily
    entry timeframe. min_trend_agree defaults to 1 (of 2: weekly, monthly)
    since requiring both to agree is a much stricter bar than the 3-of-4 or
    3-of-6 votes used at the other timeframes, given there are only 2 here."""
    signal = entry_signal_fn(bars_by_tf.get(ENTRY_TIMEFRAME, pd.DataFrame()))
    if signal is None:
        return None
    votes = [trend_bias(bars_by_tf[tf]) for tf in TREND_TIMEFRAMES if tf in bars_by_tf]
    agree = sum(1 for v in votes if v == signal)
    return signal if agree >= min_trend_agree else None
