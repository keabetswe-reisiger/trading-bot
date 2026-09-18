#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget shortcut — stops the bot and dashboard.
# Kill the watchdog first — otherwise it can restart the others before they're gone.
tmux kill-session -t goldwatch 2>/dev/null
tmux kill-session -t goldbot 2>/dev/null
tmux kill-session -t golddash 2>/dev/null
termux-wake-unlock
echo "Stopped."
