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
import pandas as pd
from oandapyV20.contrib.requests import MarketOrderRequest, StopLossDetails, TakeProfitDetails
from oandapyV20.exceptions import V20Error

import config_gold as config

MAX_CANDLES_PER_REQUEST = 5000  # OANDA's hard limit per call


class OandaBroker:
    def __init__(self) -> None:
        self.client = oandapyV20.API(access_token=config.OANDA_API_TOKEN, environment=config.OANDA_ENVIRONMENT)
        self.account_id = config.OANDA_ACCOUNT_ID

    def is_tradeable(self, instrument: str) -> bool:
        r = pricing.PricingInfo(self.account_id, params={"instruments": instrument})
        self.client.request(r)
        prices = r.response.get("prices", [])
        return bool(prices) and prices[0].get("status") == "tradeable"

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
