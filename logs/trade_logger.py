import csv
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "trades.csv")
_FIELDS = ["timestamp_utc", "symbol", "side", "qty", "entry_price", "take_profit", "stop_loss", "note"]


def log_trade(symbol: str, side: str, qty: int, entry_price: float, take_profit: float, stop_loss: float, note: str = "") -> None:
    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "note": note,
            }
        )
