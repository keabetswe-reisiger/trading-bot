"""Where to put the stop and target once a signal fires.

Fixed-percent stops treat every stock the same, which is why MSFT/TSLA
(more volatile names) kept getting stopped out in early backtests while a
tighter-natured name like AAPL didn't: a 0.15% stop is "tight" for AAPL and
"inside the normal noise" for TSLA. ATR (Average True Range) sizes the stop
to each symbol's own recent volatility instead of a single percentage for
everything, and the take-profit is kept at a fixed reward:risk multiple of
whatever that stop distance turns out to be.
"""

import pandas as pd


def atr(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = bars["close"].shift(1)
    true_range = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(span=period, adjust=False).mean()


def compute_exit_levels(
    side: str,
    entry_price: float,
    recent_bars: pd.DataFrame,
    *,
    mode: str = "atr",
    take_profit_pct: float = 0.3,
    stop_loss_pct: float = 0.15,
    atr_period: int = 14,
    atr_stop_multiplier: float = 1.5,
    reward_risk_ratio: float = 2.0,
) -> tuple[float, float]:
    """Returns (take_profit_price, stop_loss_price).

    mode="pct": fixed take_profit_pct / stop_loss_pct off entry_price.
    mode="atr": stop = atr_stop_multiplier * ATR(recent_bars), target = reward_risk_ratio * that stop distance.
    """
    if mode == "pct":
        if side == "long":
            return entry_price * (1 + take_profit_pct / 100), entry_price * (1 - stop_loss_pct / 100)
        return entry_price * (1 - take_profit_pct / 100), entry_price * (1 + stop_loss_pct / 100)

    atr_series = atr(recent_bars, atr_period)
    atr_value = float(atr_series.iloc[-1]) if len(atr_series) and pd.notna(atr_series.iloc[-1]) else None
    if not atr_value or atr_value <= 0:
        # Not enough history for a real ATR yet — fall back to the percent method.
        return compute_exit_levels(
            side, entry_price, recent_bars, mode="pct",
            take_profit_pct=take_profit_pct, stop_loss_pct=stop_loss_pct,
        )

    stop_distance = atr_stop_multiplier * atr_value
    take_profit_distance = reward_risk_ratio * stop_distance
    if side == "long":
        return entry_price + take_profit_distance, entry_price - stop_distance
    return entry_price - take_profit_distance, entry_price + stop_distance
