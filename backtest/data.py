"""Real historical OHLCV bars from Yahoo Finance (no API key needed).

Yahoo only keeps 1-minute bars for the last ~8 days, which caps how far back
this backtest can look — long enough to sanity-check the strategy's logic
against real price action, not a multi-year statistical study.
"""

import pandas as pd
import yfinance as yf


def fetch_1m_bars(symbol: str, period: str = "7d") -> pd.DataFrame:
    raw = yf.download(symbol, period=period, interval="1m", progress=False, auto_adjust=True)
    if raw.empty:
        return raw
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.lower)
    return raw[["open", "high", "low", "close", "volume"]].dropna()
