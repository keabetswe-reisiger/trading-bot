"""Swing/trend-following entry for gold — hours-long holds, not a scalp.

Backtesting showed three different scalp-style entries (crossover, pullback,
mean-reversion fade) all losing money on real gold data over both a 1-week
and a 60-day window. Over that same 60-day window gold itself trended up
7.4%. A tight scalp gets chopped by the noise *within* a trend; letting the
same underlying EMA-crossover signal run for hours instead of minutes
actually captured the trend (+10.6% in testing).

This formalizes that as a proper symmetric (long AND short) entry, confirmed
across multiple timeframes the same way the scalp strategy is — 5-minute
entry trigger, 15m/30m/1h/4h required to agree on direction. Important
caveat: the positive backtest is from an uptrending window, so it validates
the long side much more than the short side; a real downtrend sample would
be needed to trust the short side the same way.
"""

import pandas as pd

_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
_RULES = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h"}
TREND_TIMEFRAMES = ["15m", "30m", "1h", "4h"]
ENTRY_TIMEFRAME = "5m"


def build_swing_timeframes(bars_5m: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    for label, rule in _RULES.items():
        if label == "5m":
            out[label] = bars_5m
            continue
        out[label] = bars_5m.resample(rule, label="right", closed="right").agg(_AGG).dropna(how="any")
    return out


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def entry_signal(bars: pd.DataFrame, fast: int = 9, slow: int = 21) -> str | None:
    """Fresh crossover on the entry timeframe — the actual trigger bar."""
    if len(bars) < slow + 2:
        return None
    close = bars["close"]
    f, s = _ema(close, fast), _ema(close, slow)
    if f.iloc[-2] <= s.iloc[-2] and f.iloc[-1] > s.iloc[-1]:
        return "long"
    if f.iloc[-2] >= s.iloc[-2] and f.iloc[-1] < s.iloc[-1]:
        return "short"
    return None


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


def aligned_signal(bars_by_tf: dict[str, pd.DataFrame], min_trend_agree: int = 3) -> str | None:
    signal = entry_signal(bars_by_tf.get(ENTRY_TIMEFRAME, pd.DataFrame()))
    if signal is None:
        return None
    votes = [trend_bias(bars_by_tf[tf]) for tf in TREND_TIMEFRAMES if tf in bars_by_tf]
    agree = sum(1 for v in votes if v == signal)
    return signal if agree >= min_trend_agree else None
