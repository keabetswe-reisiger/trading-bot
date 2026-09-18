#!/data/data/com.termux/files/usr/bin/bash
# Run this from the Termux host. There are two separate copies of this
# repo on the phone — one on the Termux host (used by the scripts in
# termux/), one inside the Debian environment (used to actually run the
# bot/dashboard, since that's where pandas/numpy are installed). They don't
# auto-sync, which caused real confusion during setup — this updates both
# in one command.
set -e

echo "Updating Termux-host copy..."
cd "$HOME/trading-bot"
git pull

echo
echo "Updating Debian copy (and its Python dependencies)..."
proot-distro login debian -- bash -lc \
  'cd trading-bot && git pull && source venv/bin/activate && pip install -q -r requirements.txt'

echo
echo "Both copies updated. Restart to pick up the changes:"
echo "  tmux kill-session -t goldbot 2>/dev/null; tmux kill-session -t golddash 2>/dev/null"
echo "  bash trading-bot/termux/run_gold_bot.sh"
echo "  bash trading-bot/termux/run_dashboard.sh"
