#!/data/data/com.termux/files/usr/bin/bash
# Run this from the Termux host. Restarts the bot/dashboard tmux sessions if
# either dies unexpectedly, and sends a phone notification (via Termux:API)
# when something notable happens: a trade opens/closes, the daily loss limit
# hits, or a loop error occurs.
set -u

STATUS_FILE="$PREFIX/var/lib/proot-distro/containers/debian/root/trading-bot/logs/status.json"
CHECK_INTERVAL=30

last_message=""
last_error=""

echo "Watchdog running. Reading status from: $STATUS_FILE"

while true; do
  if ! tmux has-session -t goldbot 2>/dev/null; then
    termux-notification --title "Gold Bot" --content "Bot session died, restarting..." 2>/dev/null
    bash "$HOME/trading-bot/termux/run_gold_bot.sh"
  fi
  if ! tmux has-session -t golddash 2>/dev/null; then
    bash "$HOME/trading-bot/termux/run_dashboard.sh"
  fi

  if [ -f "$STATUS_FILE" ]; then
    message=$(jq -r '.message // empty' "$STATUS_FILE" 2>/dev/null)
    error=$(jq -r '.error // empty' "$STATUS_FILE" 2>/dev/null)

    if [ -n "$error" ] && [ "$error" != "$last_error" ]; then
      termux-notification --title "Gold Bot: error" --content "$error" 2>/dev/null
      last_error="$error"
    fi

    if [ -n "$message" ] && [ "$message" != "$last_message" ]; then
      case "$message" in
        Opened*|Closed*|*"loss limit"*)
          termux-notification --title "Gold Bot" --content "$message" 2>/dev/null
          ;;
      esac
      last_message="$message"
    fi
  fi

  sleep "$CHECK_INTERVAL"
done
