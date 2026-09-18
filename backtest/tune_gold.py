"""Small grid search over ATR stop multiplier / reward:risk / max-hold-time,
against real GC=F (COMEX gold futures, close proxy for spot XAU_USD) history.

This is calibration against ~1 week of data, not a statistically significant
optimization — with single-digit trade counts per cell, individual "best"
results can easily be noise. Look for settings that are stable across nearby
values, not a single spike.
"""

from functools import partial

from backtest.data import fetch_1m_bars
from backtest.engine import simulate
from backtest.metrics import summarize
from strategy.gold_entry import pullback_signal
from strategy.resample import build_multi_timeframe

ATR_MULTIPLIERS = [1.0, 1.5, 2.0]
REWARD_RISK_RATIOS = [1.5, 2.0]
MAX_HOLDS = [15, 30]


def run(symbol: str = "GC=F", entry_signal_fn=None) -> None:
    bars = fetch_1m_bars(symbol)
    tf_data = build_multi_timeframe(bars)

    header = f"{'ATRx':>6}{'R:R':>6}{'Hold':>6}{'Trades':>8}{'Win%':>8}{'Return%':>10}{'AvgR':>8}{'MaxDD%':>9}"
    print(header)
    print("-" * len(header))

    rows = []
    for atr_mult in ATR_MULTIPLIERS:
        for rr in REWARD_RISK_RATIOS:
            for hold in MAX_HOLDS:
                result = simulate(
                    symbol, bars, tf_data,
                    stop_mode="atr",
                    atr_stop_multiplier=atr_mult,
                    reward_risk_ratio=rr,
                    max_hold_minutes=hold,
                    min_avg_volume=0,
                    entry_signal_fn=entry_signal_fn,
                )
                m = summarize(result, starting_equity=100_000.0)
                rows.append((atr_mult, rr, hold, m))

    rows.sort(key=lambda r: r[3]["return_pct"], reverse=True)
    for atr_mult, rr, hold, m in rows:
        print(
            f"{atr_mult:>6}{rr:>6}{hold:>6}{m['total_trades']:>8}{m['win_rate_pct']:>8}"
            f"{m['return_pct']:>10}{m['avg_r_multiple']:>8}{m['max_drawdown_pct']:>9}"
        )


if __name__ == "__main__":
    run(entry_signal_fn=partial(pullback_signal, restrict_session=True))
