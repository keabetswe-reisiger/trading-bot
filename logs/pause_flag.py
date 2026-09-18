import os

PAUSE_FLAG_PATH = os.path.join(os.path.dirname(__file__), "pause.flag")


def is_paused() -> bool:
    return os.path.exists(PAUSE_FLAG_PATH)


def pause() -> None:
    with open(PAUSE_FLAG_PATH, "w") as f:
        f.write("paused")


def resume() -> None:
    if os.path.exists(PAUSE_FLAG_PATH):
        os.remove(PAUSE_FLAG_PATH)
