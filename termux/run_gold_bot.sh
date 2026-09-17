#!/data/data/com.termux/files/usr/bin/bash
# Run this from the Termux host (not inside proot-distro) to (re)start the
# gold bot in a detached tmux session that survives closing the Termux app.
#
# Also enable in Android settings: Settings -> Apps -> Termux -> Battery ->
# Unrestricted. Without that, Android can still kill the process regardless
# of termux-wake-lock.
set -e

SESSION=goldbot

termux-wake-lock

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already running. Attach with: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" \
  "proot-distro login debian -- bash -lc 'cd trading-bot && source venv/bin/activate && python main_gold.py'"

echo "Started in tmux session '$SESSION'."
echo "Attach to watch it:   tmux attach -t $SESSION"
echo "Detach without killing it: press Ctrl-b then d"
