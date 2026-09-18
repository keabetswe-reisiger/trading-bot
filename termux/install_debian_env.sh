#!/data/data/com.termux/files/usr/bin/bash
# Run this ONCE, directly in Termux (not inside proot-distro).
#
# pandas has no prebuilt Termux package and compiling it from source on-device
# is slow and fragile, so this sets up a real Debian userland via proot-distro
# instead — a normal glibc Linux environment where pip wheels for
# pandas/numpy just work, same as any Linux server.
set -e

pkg update -y && pkg upgrade -y
pkg install -y proot-distro git termux-api tmux jq

if ! proot-distro list | grep -q "debian.*installed"; then
  proot-distro install debian
fi

echo
echo "Debian environment ready. Next, log into it and run setup_bot.sh:"
echo "  proot-distro login debian"
echo "  git clone https://github.com/keabetswe-reisiger/trading-bot.git"
echo "  bash trading-bot/termux/setup_bot.sh"
