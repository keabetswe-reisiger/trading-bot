#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget shortcut — opens the status dashboard (starts it first if
# it isn't already running).
cd ~/trading-bot || exit 1
bash termux/run_dashboard.sh
termux-open-url http://127.0.0.1:8765
