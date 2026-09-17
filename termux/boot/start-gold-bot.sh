#!/data/data/com.termux/files/usr/bin/bash
# Copy this file to ~/.termux/boot/start-gold-bot.sh on the phone (requires the
# Termux:Boot app installed from F-Droid) to auto-start the bot when the
# phone reboots.
termux-wake-lock
bash ~/trading-bot/termux/run_gold_bot.sh
