#!/data/data/com.termux/files/usr/bin/bash
# Run this from the Termux host (not inside proot-distro) to (re)start the
# daily-bar gold position bot (main_gold_position.py) in a detached tmux
# session that survives closing the Termux app. Separate session from
# run_gold_bot.sh's "goldbot" on purpose: it trades a different OANDA
# practice account (OANDA_POSITION_* in .env).
set -e

SESSION=goldpos

termux-wake-lock

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already running. Attach with: tmux attach -t $SESSION"
  exit 0
fi

# Kill any stray main_gold_position.py not managed by tmux (e.g. left over
# from a manual foreground run) — two instances against one account is messy.
proot-distro login debian -- pkill -f "python main_gold_position.py" 2>/dev/null || true
sleep 1

tmux new-session -d -s "$SESSION" \
  "proot-distro login debian -- bash -lc 'cd trading-bot && source venv/bin/activate && python main_gold_position.py'"

sleep 1
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Started in tmux session '$SESSION'."
  echo "Attach to watch it:   tmux attach -t $SESSION"
  echo "Detach without killing it: press Ctrl-b then d"
else
  echo "Position bot failed to start. Run this to see the actual error:"
  echo "  proot-distro login debian"
  echo "  cd trading-bot && source venv/bin/activate && python main_gold_position.py"
fi
