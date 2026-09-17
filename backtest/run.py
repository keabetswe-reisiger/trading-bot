"""Run: python -m backtest.run [SYMBOL ...]  (defaults to AAPL MSFT NVDA)

Uses free Yahoo Finance data — no Alpaca keys needed for this.
"""

import sys

from backtest.data import fetch_1m_bars
from backtest.engine import simulate
from backtest.metrics import summarize
from strategy.resample import build_multi_timeframe

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA"]


def run(symbols: list[str]) -> None:
    header = f"{'Mode':<5}{'Symbol':<8}{'Trades':>8}{'Win%':>8}{'PnL':>12}{'Return%':>10}{'AvgR':>8}{'MaxDD%':>9}"
    print(header)
    print("-" * len(header))

    for symbol in symbols:
        bars_1m = fetch_1m_bars(symbol)
        if bars_1m.empty or len(bars_1m) < 200:
            print(f"{symbol:<8}  not enough 1-minute history from Yahoo, skipping")
            continue

        tf_data = build_multi_timeframe(bars_1m)

        for mode in ("pct", "atr"):
            result = simulate(symbol, bars_1m, tf_data, stop_mode=mode)
            m = summarize(result, starting_equity=100_000.0)
            print(
                f"{mode:<5}{m['symbol']:<8}{m['total_trades']:>8}{m['win_rate_pct']:>8}"
                f"{m['total_pnl']:>12}{m['return_pct']:>10}{m['avg_r_multiple']:>8}{m['max_drawdown_pct']:>9}"
            )


if __name__ == "__main__":
    symbols = [s.upper() for s in sys.argv[1:]] or DEFAULT_SYMBOLS
    run(symbols)
