"""Append-only CSV of every MetaTrader screenshot read, so the practice-
account comparison against the OANDA bot (see `mt_screenshot_reader.py`)
has a paper trail instead of relying on memory of what fired when."""

import csv
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "screenshot_signals.csv")
_FIELDS = ["timestamp_utc", "source_file", "price", "rsi", "signal", "note"]


def log_screenshot_signal(source_file: str, price: float | None, rsi: float | None, signal: str | None, note: str = "") -> None:
    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_file": source_file,
                "price": price,
                "rsi": rsi,
                "signal": signal or "none",
                "note": note,
            }
        )
