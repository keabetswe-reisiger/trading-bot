#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget shortcut — copy this whole folder's contents into ~/.shortcuts/
# (see termux/README.md). Tapping the widget icon runs this.
cd ~/trading-bot || exit 1
bash termux/run_gold_bot.sh
bash termux/run_dashboard.sh
if ! tmux has-session -t goldwatch 2>/dev/null; then
  tmux new-session -d -s goldwatch "bash $HOME/trading-bot/termux/watchdog.sh"
fi
termux-open-url http://127.0.0.1:8765
