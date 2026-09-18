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

tmux new-session -d -s "$SESSION" \
  "proot-distro login debian -- bash -lc 'cd trading-bot && source venv/bin/activate && python dashboard.py'"

sleep 1
echo "Dashboard started: http://127.0.0.1:8765"
