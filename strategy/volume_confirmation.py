"""Volume Spread Analysis (VSA) style confirmation — "Stopping Volume":
a reversal is more credible when the trigger bar shows unusually high
volume (real participation behind the move), not just a low-conviction
wiggle. From Tom Williams' VSA methodology (Wyckoff tradition).

Caveat: OANDA reports tick volume (price-update count) for gold, not real
traded volume — this is validated here against Yahoo's futures data, which
has real volume, so a live-data result may not transfer identically.
"""

import pandas as pd


def has_stopping_volume(bars: pd.DataFrame, lookback: int = 20, multiplier: float = 1.5) -> bool:
    """True if the last bar's volume is at least `multiplier`x the average
    of the preceding `lookback` bars."""
    if len(bars) < lookback + 1:
        return False
    recent = bars["volume"].iloc[-(lookback + 1) : -1]
    avg_volume = recent.mean()
    if avg_volume <= 0:
        return False
    return bool(bars["volume"].iloc[-1] >= multiplier * avg_volume)
