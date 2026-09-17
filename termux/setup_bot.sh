#!/bin/bash
# Run this ONCE, inside the Debian environment (after `proot-distro login debian`).
set -e

apt update && apt install -y python3 python3-venv python3-pip git nano

cd "$(dirname "$0")/.."   # repo root (this script lives in trading-bot/termux/)

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "Created .env — edit it now with your OANDA practice API token/account ID:"
  echo "  nano .env"
fi

echo
echo "Setup done. To run the gold bot:"
echo "  source venv/bin/activate && python main_gold.py"
echo "Or use termux/run_gold_bot.sh from the Termux host to run it persistently in tmux."
