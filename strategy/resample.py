"""Build every timeframe the strategy needs from a single 1-minute series.

label='right', closed='right' means a bar stamped 10:15 only contains data
through 10:15 — i.e. what would actually have been known at that moment.
Deriving every timeframe from the same 1-minute source (instead of fetching
each one separately) guarantees they line up on the same clock.
"""

import pandas as pd

_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}

_RULES = {
    "1m": "1min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "20m": "20min",
    "30m": "30min",
    "1h": "1h",
}


def build_multi_timeframe(bars_1m: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    for label, rule in _RULES.items():
        if label == "1m":
            out[label] = bars_1m
            continue
        resampled = bars_1m.resample(rule, label="right", closed="right").agg(_AGG)
        out[label] = resampled.dropna(how="any")
    return out
