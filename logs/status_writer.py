import json
import os
import tempfile
from datetime import datetime, timezone

STATUS_PATH = os.path.join(os.path.dirname(__file__), "status.json")


def write_status(*, path: str = STATUS_PATH, **fields) -> None:
    """path: override for a second bot sharing this logs/ dir (e.g. the
    daily position bot) so it doesn't collide with another bot's status."""
    payload = {"updated_utc": datetime.now(timezone.utc).isoformat(), **fields}
    # Write to a temp file then rename, so a concurrent reader (the dashboard)
    # never sees a half-written file.
    dir_ = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
