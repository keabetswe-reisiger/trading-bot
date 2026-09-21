"""Append-only log of every check the bot makes (not just trades), so the
dashboard can show it's actively working every poll cycle even when no
trade fires — visible proof of life without compromising the strategy."""

import json
import os
from datetime import datetime, timezone

ACTIVITY_PATH = os.path.join(os.path.dirname(__file__), "activity.jsonl")
MAX_ENTRIES = 200


def log_activity(message: str) -> None:
    entry = {"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "message": message}
    with open(ACTIVITY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _trim_if_needed()


def _trim_if_needed() -> None:
    if not os.path.exists(ACTIVITY_PATH):
        return
    with open(ACTIVITY_PATH) as f:
        lines = f.readlines()
    if len(lines) > MAX_ENTRIES:
        with open(ACTIVITY_PATH, "w") as f:
            f.writelines(lines[-MAX_ENTRIES:])


def recent_activity(limit: int = 20) -> list:
    if not os.path.exists(ACTIVITY_PATH):
        return []
    with open(ACTIVITY_PATH) as f:
        lines = f.readlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))
