import json
import os
import tempfile
from datetime import datetime, timezone

STATUS_PATH = os.path.join(os.path.dirname(__file__), "status.json")


def write_status(**fields) -> None:
    payload = {"updated_utc": datetime.now(timezone.utc).isoformat(), **fields}
    # Write to a temp file then rename, so a concurrent reader (the dashboard)
    # never sees a half-written file.
    dir_ = os.path.dirname(STATUS_PATH)
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, STATUS_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
