"""RSI-extreme rule for a single price+RSI snapshot (no bar history).

Every other signal in `strategy/` (stophunt, breakout, divergence, the BB
mean-reversion RSI filter, the scalp crossover RSI filter) works off a
candle series and can't run on a single screenshot read. The one piece of
existing logic that *does* reduce to "one RSI number, one decision" is the
overbought/oversold threshold already used as a filter in
`gold_meanrev.py::bb_signal` (prev_rsi > 70 / < 30) and referenced in
`scalp_strategy.py`'s docstring (RSI < 70 / > 30) — this module lifts that
same threshold out so the screenshot reader can apply it standalone. It is
deliberately not a port of stophunt/breakout/divergence: those need OHLC
history a single screenshot doesn't have.
"""


def rsi_threshold_signal(rsi: float, overbought: float = 70.0, oversold: float = 30.0) -> str | None:
    """Classic RSI mean-reversion read: fade an extreme back toward 50.

    Returns "short" at/above `overbought`, "long" at/below `oversold`,
    otherwise None (no signal). Matches the 70/30 thresholds already used
    elsewhere in this project rather than inventing new ones.
    """
    if rsi >= overbought:
        return "short"
    if rsi <= oversold:
        return "long"
    return None
