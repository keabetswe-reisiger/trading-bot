# Running the gold bot on your Android phone (Termux)

This lets `main_gold.py` run directly on your phone against your OANDA demo
account, and since the code lives in a private GitHub repo
(`github.com/keabetswe-reisiger/trading-bot`), you can pull the same code
onto any other device too.

**Why not just `pip install` straight in Termux?** pandas has no prebuilt
Termux package and compiling it on-device from source is slow and often
fails. Instead we install a real Debian environment inside Termux via
`proot-distro` — a normal glibc Linux userspace where pip wheels for
pandas/numpy just work, same as on any Linux server.

## One-time setup

1. Install **Termux** from F-Droid (search "Termux" at f-droid.org) — **not**
   the Play Store version, which is outdated and unmaintained.
2. Also install **Termux:API** and **Termux:Boot** from F-Droid (same
   developer/collection) — needed for keeping the bot alive and for
   auto-start on reboot.
3. Open Termux and run:
   ```bash
   pkg install -y git
   git clone https://github.com/keabetswe-reisiger/trading-bot.git
   bash trading-bot/termux/install_debian_env.sh
   ```
4. Log into the Debian environment and finish setup:
   ```bash
   proot-distro login debian
   git clone https://github.com/keabetswe-reisiger/trading-bot.git
   bash trading-bot/termux/setup_bot.sh
   ```
5. Fill in your OANDA practice API token/account ID when prompted (`nano .env`
   inside the Debian shell), then exit back to the Termux host (`exit`).

## Running it

From the **Termux host** (not inside `proot-distro login debian`):
```bash
bash trading-bot/termux/run_gold_bot.sh
```
This grabs a wake-lock and starts `main_gold.py` inside a detached `tmux`
session named `goldbot`, so it keeps running even if you close the Termux
app window.

- Check on it: `tmux attach -t goldbot` (detach again with `Ctrl-b` then `d`
  — don't press Ctrl-C or you'll kill the bot)
- Stop it: attach, then `Ctrl-C`, or `tmux kill-session -t goldbot`

**Also disable Android battery optimization for Termux** (Settings → Apps →
Termux → Battery → Unrestricted). Without this, Android can still kill the
process in the background regardless of the wake-lock.

## Auto-start on reboot (optional)

Copy `termux/boot/start-gold-bot.sh` to `~/.termux/boot/` on the phone (that's
the Termux host's home, not inside Debian):
```bash
mkdir -p ~/.termux/boot
cp trading-bot/termux/boot/start-gold-bot.sh ~/.termux/boot/
chmod +x ~/.termux/boot/start-gold-bot.sh
```
Requires the Termux:Boot app to be installed and opened once.

## Keeping it up to date

Since the code lives on GitHub, pull the latest version instead of re-cloning:
```bash
proot-distro login debian
cd trading-bot && git pull
source venv/bin/activate && pip install -r requirements.txt
```

## Honest caveat

These scripts are written from documented Termux/proot-distro behavior but
haven't been tested on an actual device from this session (no Android phone
available here) — the underlying Python code (`main_gold.py`, strategy,
broker) has been tested independently, but if a step in these scripts
doesn't work exactly as written on your phone, tell me the error and I'll
adjust it.
