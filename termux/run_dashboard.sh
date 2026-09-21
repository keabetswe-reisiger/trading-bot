#!/data/data/com.termux/files/usr/bin/bash
# Run this from the Termux host to (re)start the status dashboard in its own
# detached tmux session. Then open http://127.0.0.1:8765 in your phone's
# browser (works alongside run_gold_bot.sh — separate tmux sessions).
set -e

SESSION=golddash

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Dashboard already running at http://127.0.0.1:8765"
  exit 0
fi

# Kill any stray dashboard.py not managed by tmux (e.g. left over from a
# manual foreground test) — otherwise the new one fails silently with
# "Address already in use" and this tmux session dies instantly, which
# has caused real confusion before.
proot-distro login debian -- pkill -f "python dashboard.py" 2>/dev/null || true
sleep 1

tmux new-session -d -s "$SESSION" \
  "proot-distro login debian -- bash -lc 'cd trading-bot && source venv/bin/activate && python dashboard.py'"

sleep 1
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Dashboard started: http://127.0.0.1:8765"
else
  echo "Dashboard failed to start. Run this to see the actual error:"
  echo "  proot-distro login debian"
  echo "  cd trading-bot && source venv/bin/activate && python dashboard.py"
fi
