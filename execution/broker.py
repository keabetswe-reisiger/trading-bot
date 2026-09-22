"""Thin wrapper around Alpaca's trading + market data clients.

Keeps all third-party SDK calls in one place so the rest of the bot
doesn't need to know the Alpaca API shape.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.common.enums import Sort
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest, StopLossRequest, TakeProfitRequest

import config


class AlpacaBroker:
    def __init__(self) -> None:
        self.trading = TradingClient(
            config.ALPACA_API_KEY_ID,
            config.ALPACA_API_SECRET_KEY,
            paper=config.ALPACA_PAPER,
        )
        self.data = StockHistoricalDataClient(
            config.ALPACA_API_KEY_ID,
            config.ALPACA_API_SECRET_KEY,
        )

    def is_market_open(self) -> bool:
        return bool(self.trading.get_clock().is_open)

    def get_equity(self) -> float:
        return float(self.trading.get_account().equity)

    def get_open_positions(self) -> dict:
        """symbol -> position object"""
        return {p.symbol: p for p in self.trading.get_all_positions()}

    def get_recent_bars(self, symbol: str, minutes: int = 60, timeframe: TimeFrame = TimeFrame.Minute) -> pd.DataFrame:
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=datetime.now(timezone.utc) - timedelta(minutes=minutes),
        )
        bars = self.data.get_stock_bars(req).df
        if bars.empty:
            return bars
        bars = bars.loc[symbol] if symbol in bars.index.get_level_values(0) else bars
        return bars[["open", "high", "low", "close", "volume"]]

    def get_multi_timeframe_bars(self, symbol: str, timeframes: dict, bars_needed: int = 30) -> dict:
        """timeframes: {"1h": TimeFrame(...), "15m": TimeFrame(...), ...}"""
        unit_minutes = {TimeFrameUnit.Minute: 1, TimeFrameUnit.Hour: 60, TimeFrameUnit.Day: 60 * 24}
        result = {}
        for label, tf in timeframes.items():
            minutes_per_bar = tf.amount_value * unit_minutes.get(tf.unit_value, 1)
            lookback_minutes = minutes_per_bar * bars_needed * 3  # buffer for closed-market gaps
            result[label] = self.get_recent_bars(symbol, minutes=lookback_minutes, timeframe=tf)
        return result

    def submit_bracket_order(
        self,
        symbol: str,
        qty: int,
        side: OrderSide,
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float,
    ):
        order = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
            stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 2)),
        )
        return self.trading.submit_order(order)

    def close_position(self, symbol: str):
        return self.trading.close_position(symbol)

    def get_last_closed_fill_price(self, symbol: str) -> float | None:
        """Fill price of the most recently closed order (or bracket leg) for
        this symbol, or None if there isn't one. Alpaca doesn't report
        realized P&L per closed position directly — the caller combines this
        with its own locally-tracked entry price/qty to compute it, the same
        way main_gold.py does with OANDA's closed-trade P&L."""
        r = GetOrdersRequest(status=QueryOrderStatus.CLOSED, symbols=[symbol], limit=5, direction=Sort.DESC, nested=True)
        orders = self.trading.get_orders(r)
        for order in orders:
            candidates = order.legs if order.legs else [order]
            for leg in candidates:
                if leg.filled_avg_price is not None:
                    return float(leg.filled_avg_price)
        return None
