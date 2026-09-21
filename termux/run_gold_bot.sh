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

# Kill any stray main_gold.py not managed by tmux (e.g. left over from a
# manual foreground test) — running two instances at once against the same
# account is messy and wasteful even if not outright dangerous.
proot-distro login debian -- pkill -f "python main_gold.py" 2>/dev/null || true
sleep 1

tmux new-session -d -s "$SESSION" \
  "proot-distro login debian -- bash -lc 'cd trading-bot && source venv/bin/activate && python main_gold.py'"

sleep 1
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Started in tmux session '$SESSION'."
  echo "Attach to watch it:   tmux attach -t $SESSION"
  echo "Detach without killing it: press Ctrl-b then d"
else
  echo "Bot failed to start. Run this to see the actual error:"
  echo "  proot-distro login debian"
  echo "  cd trading-bot && source venv/bin/activate && python main_gold.py"
fi
