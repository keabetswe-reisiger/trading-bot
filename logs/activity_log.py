"""Append-only log of every check the bot makes (not just trades), so the
dashboard can show it's actively working every poll cycle even when no
trade fires — visible proof of life without compromising the strategy."""

import json
import os
from datetime import datetime, timezone

ACTIVITY_PATH = os.path.join(os.path.dirname(__file__), "activity.jsonl")
MAX_ENTRIES = 200


def log_activity(message: str, *, path: str = ACTIVITY_PATH) -> None:
    """path: override for a second bot sharing this logs/ dir (e.g. the
    daily position bot) so its activity doesn't interleave with another
    bot's in the same file."""
    entry = {"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "message": message}
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _trim_if_needed(path)


def _trim_if_needed(path: str = ACTIVITY_PATH) -> None:
    if not os.path.exists(path):
        return
    with open(path) as f:
        lines = f.readlines()
    if len(lines) > MAX_ENTRIES:
        with open(path, "w") as f:
            f.writelines(lines[-MAX_ENTRIES:])


def recent_activity(limit: int = 20, *, path: str = ACTIVITY_PATH) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = f.readlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))
