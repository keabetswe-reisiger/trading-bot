"""Persists the daily-bar position bot's open-trade state to disk. Unlike
the scalp bots' in-memory-only tracking (fine for a 10-minute hold — if the
process restarts, the bracket order's TP/SL still protects the position,
it just forgets when it was opened), a 10-40 *day* hold on a phone that
reboots occasionally needs this to survive a restart."""

import json
import os
import tempfile

STATE_PATH = os.path.join(os.path.dirname(__file__), "position_state.json")


def load_state() -> dict | None:
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state: dict | None) -> None:
    dir_ = os.path.dirname(STATE_PATH)
    if state is None:
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
        return
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
