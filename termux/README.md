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

## Home-screen shortcuts + status dashboard

Instead of typing commands each time, you can get a home-screen widget with
one-tap buttons, plus a status page in your browser.

**1. Status dashboard** — a simple page showing whether the bot is running,
open positions, equity, and recent trades. Runs locally on the phone, no
internet needed beyond what the bot already uses:
```bash
bash trading-bot/termux/run_dashboard.sh
```
Then open `http://127.0.0.1:8765` in your phone's browser and bookmark it.
It auto-refreshes every 15 seconds.

**2. Home-screen widget** — requires the Termux:Widget app (install from
F-Droid, same collection as Termux:API/Termux:Boot). Copy the shortcut
scripts into place:
```bash
mkdir -p ~/.shortcuts
cp trading-bot/termux/shortcuts/*.sh ~/.shortcuts/
chmod +x ~/.shortcuts/*.sh
```
Then, on your phone's home screen: long-press an empty area → Widgets →
find "Termux:Widget" → drag it onto the home screen. It'll show three
buttons: **Start Gold Bot**, **Stop Gold Bot**, **Gold Bot Status** — each
one taps to run without opening Termux manually. "Start" launches the bot
and dashboard together and opens the dashboard in your browser
automatically.

**3. Notifications + auto-restart watchdog** — a background process on the
Termux host that (a) restarts the bot or dashboard if either dies
unexpectedly, and (b) sends a phone notification (via Termux:API) when a
trade opens/closes, the daily loss limit hits, or a loop error occurs. It's
started automatically by the "Start Gold Bot" widget button, or manually:
```bash
tmux new-session -d -s goldwatch "bash trading-bot/termux/watchdog.sh"
```

**4. Pause/Resume** — the dashboard has a button to pause the bot (stops it
from opening new trades; any position already open is still managed to its
take-profit/stop-loss/max-hold-time) without needing to touch Termux at all.

## Keeping it up to date

**There are two separate copies of this code on the phone** — one on the
Termux host (used by the scripts in `termux/`), one inside the Debian
environment (used to actually run the bot/dashboard, since that's where
pandas/numpy live). They don't auto-sync with each other, which is a real
source of confusion (hit repeatedly during initial setup — "site can't be
reached" turned out to mean the Debian copy was out of date). One command
updates both:
```bash
bash trading-bot/termux/update_all.sh
```

## Honest caveat

These scripts are written from documented Termux/proot-distro behavior. The
core bot logic (`main_gold.py`, strategy, broker) has been tested
independently and confirmed working against a real OANDA demo account
during setup — including catching and fixing a real bug
(`NO_SUCH_POSITION` on a fresh account's first check). The dashboard and
pause/resume feature have been tested end-to-end locally (a real HTTP
server, real requests). The notification/watchdog script
(`watchdog.sh`) has not been tested on an actual device — if
`termux-notification` doesn't fire or the auto-restart doesn't work as
described, tell me the exact behavior and I'll adjust it.
