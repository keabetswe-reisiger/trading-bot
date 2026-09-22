"""OANDA v20 REST API wrapper for gold (XAU_USD) trading.

Unlike Alpaca, OANDA has no separate "bars per timeframe" endpoint story we
need to special-case: we pull 1-minute candles once and let
strategy.resample.build_multi_timeframe derive every other timeframe locally
(OANDA doesn't even offer native M3/M20 granularities, so this is required,
not just convenient).
"""

import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
import pandas as pd
from oandapyV20.contrib.requests import MarketOrderRequest, StopLossDetails, TakeProfitDetails
from oandapyV20.exceptions import V20Error

MAX_CANDLES_PER_REQUEST = 5000  # OANDA's hard limit per call


class OandaBroker:
    def __init__(self, api_token: str, account_id: str, environment: str = "practice") -> None:
        """Takes credentials explicitly (not read from a specific config
        module) so multiple bots can each use their own separate OANDA
        account — e.g. main_gold.py (1-minute, config_gold) and
        main_gold_position.py (daily, config_position) never share state."""
        self.client = oandapyV20.API(access_token=api_token, environment=environment)
        self.account_id = account_id

    def is_tradeable(self, instrument: str) -> bool:
        r = pricing.PricingInfo(self.account_id, params={"instruments": instrument})
        self.client.request(r)
        prices = r.response.get("prices", [])
        return bool(prices) and prices[0].get("status") == "tradeable"

    def get_current_spread(self, instrument: str) -> float | None:
        """Current bid/ask spread in price units, or None if unavailable."""
        r = pricing.PricingInfo(self.account_id, params={"instruments": instrument})
        self.client.request(r)
        prices = r.response.get("prices", [])
        if not prices:
            return None
        bid, ask = prices[0].get("closeoutBid"), prices[0].get("closeoutAsk")
        if bid is None or ask is None:
            return None
        return float(ask) - float(bid)

    def get_equity(self) -> float:
        r = accounts.AccountSummary(self.account_id)
        self.client.request(r)
        return float(r.response["account"]["NAV"])

    def get_open_position_units(self, instrument: str) -> float:
        r = positions.PositionDetails(self.account_id, instrument)
        try:
            self.client.request(r)
        except V20Error as exc:
            # OANDA errors (rather than returning zero) when a position has
            # never existed for this instrument on the account — normal on
            # a fresh account before its first trade.
            if "NO_SUCH_POSITION" in str(exc):
                return 0.0
            raise
        pos = r.response["position"]
        return float(pos["long"]["units"]) + float(pos["short"]["units"])

    def has_open_position(self, instrument: str) -> bool:
        return self.get_open_position_units(instrument) != 0

    def get_recent_1m_bars(self, instrument: str, count: int = MAX_CANDLES_PER_REQUEST) -> pd.DataFrame:
        r = instruments.InstrumentsCandles(
            instrument, params={"granularity": "M1", "count": min(count, MAX_CANDLES_PER_REQUEST), "price": "M"}
        )
        self.client.request(r)
        rows = [
            {
                "time": c["time"],
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
                "volume": int(c["volume"]),
            }
            for c in r.response["candles"]
            if c["complete"]  # drop the still-forming current candle
        ]
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df.set_index("time")[["open", "high", "low", "close", "volume"]]

    def get_recent_daily_bars(self, instrument: str, count: int = 1500) -> pd.DataFrame:
        """~6 years of daily candles by default — enough for weekly/monthly
        trend confirmation to warm up (a 21-period monthly EMA alone needs
        22+ months) with real margin, while staying well under OANDA's
        5000-candle per-request cap."""
        r = instruments.InstrumentsCandles(
            instrument, params={"granularity": "D", "count": min(count, MAX_CANDLES_PER_REQUEST), "price": "M"}
        )
        self.client.request(r)
        rows = [
            {
                "time": c["time"],
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
                "volume": int(c["volume"]),
            }
            for c in r.response["candles"]
            if c["complete"]
        ]
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df.set_index("time")[["open", "high", "low", "close", "volume"]]

    def submit_bracket_order(self, instrument: str, units: int, take_profit_price: float, stop_loss_price: float):
        """units: positive = buy/long, negative = sell/short."""
        order = MarketOrderRequest(
            instrument=instrument,
            units=units,
            takeProfitOnFill=TakeProfitDetails(price=round(take_profit_price, 2)).data,
            stopLossOnFill=StopLossDetails(price=round(stop_loss_price, 2)).data,
        )
        r = orders.OrderCreate(self.account_id, data=order.data)
        self.client.request(r)
        return r.response

    def close_position(self, instrument: str):
        units = self.get_open_position_units(instrument)
        if units == 0:
            return None
        data = {"longUnits": "ALL"} if units > 0 else {"shortUnits": "ALL"}
        r = positions.PositionClose(self.account_id, instrument, data=data)
        self.client.request(r)
        return r.response

    def get_last_closed_trade_pnl(self, instrument: str) -> float | None:
        """Realized P&L of the most recently closed trade for this instrument,
        or None if there isn't one. Used to feed the risk manager's daily
        loss limit — otherwise it never learns whether a trade actually lost."""
        r = trades.TradesList(self.account_id, params={"instrument": instrument, "state": "CLOSED", "count": 1})
        self.client.request(r)
        closed = r.response.get("trades", [])
        if not closed:
            return None
        return float(closed[0]["realizedPL"])
