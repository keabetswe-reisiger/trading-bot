"""Minimal local status page for the gold bot — no new dependencies, just
Python's built-in web server. Run this alongside main_gold.py, then open
http://127.0.0.1:8765 in your phone's browser.

Run: python dashboard.py
"""

import csv
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from logs.pause_flag import is_paused, pause, resume

STATUS_PATH = os.path.join(os.path.dirname(__file__), "logs", "status.json")
TRADES_PATH = os.path.join(os.path.dirname(__file__), "logs", "trades.csv")
PORT = 8765


def _load_status() -> dict:
    if not os.path.exists(STATUS_PATH):
        return {"message": "No status yet — is main_gold.py running?"}
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"message": "Status file mid-write, refresh in a moment"}


def _load_recent_trades(limit: int = 20) -> list:
    if not os.path.exists(TRADES_PATH):
        return []
    with open(TRADES_PATH) as f:
        rows = list(csv.DictReader(f))
    return list(reversed(rows[-limit:]))


def _render_html() -> str:
    status = _load_status()
    trades = _load_recent_trades()

    error = status.get("error")
    banner = f'<div class="banner error">Last loop error: {error}</div>' if error else ""

    paused = is_paused()
    if paused:
        pause_banner = '<div class="banner paused">PAUSED — not opening new trades. Existing positions are still managed.</div>'
        pause_button = '<a class="button resume" href="/resume">Resume trading</a>'
    else:
        pause_banner = ""
        pause_button = '<a class="button pause" href="/pause">Pause trading</a>'

    rows = "".join(
        f"<tr><td>{t['timestamp_utc']}</td><td>{t['symbol']}</td><td>{t['side']}</td>"
        f"<td>{t['qty']}</td><td>{t['entry_price']}</td><td>{t['take_profit']}</td>"
        f"<td>{t['stop_loss']}</td></tr>"
        for t in trades
    ) or '<tr><td colspan="7" style="opacity:0.6">No trades yet</td></tr>'

    equity = status.get("equity")
    equity_html = f"${equity:,.2f}" if isinstance(equity, (int, float)) else "—"
    position_html = "Yes" if status.get("has_position") else "No"
    tradeable_html = "Yes" if status.get("tradeable") else "No" if "tradeable" in status else "—"

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>Gold Bot Status</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background:#0e0e12; color:#eee; padding:16px; margin:0; }}
  h1 {{ font-size:1.3em; margin-bottom:4px; }}
  .updated {{ opacity:0.6; font-size:0.8em; margin-bottom:16px; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:16px; }}
  .card {{ background:#1a1a22; border-radius:10px; padding:12px 16px; flex:1; min-width:120px; }}
  .card .label {{ opacity:0.6; font-size:0.75em; text-transform:uppercase; }}
  .card .value {{ font-size:1.3em; font-weight:600; margin-top:4px; }}
  .message {{ background:#1a1a22; border-radius:10px; padding:12px 16px; margin-bottom:16px; }}
  .banner.error {{ background:#3a1a1a; border:1px solid #a33; border-radius:10px; padding:10px 14px; margin-bottom:16px; }}
  .banner.paused {{ background:#3a2f1a; border:1px solid #a83; border-radius:10px; padding:10px 14px; margin-bottom:16px; }}
  .button {{ display:inline-block; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:600; margin-bottom:16px; }}
  .button.pause {{ background:#a83; color:#111; }}
  .button.resume {{ background:#3a3; color:#111; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.82em; background:#1a1a22; border-radius:10px; overflow:hidden; }}
  td, th {{ border-bottom:1px solid #2a2a32; padding:8px; text-align:left; }}
  th {{ opacity:0.6; font-weight:600; font-size:0.8em; text-transform:uppercase; }}
  .footer {{ opacity:0.5; font-size:0.75em; margin-top:16px; }}
</style></head>
<body>
<h1>Gold Bot — {status.get('instrument', '?')}</h1>
<div class="updated">Updated: {status.get('updated_utc', '?')} &middot; mode: {status.get('entry_mode', '?')} &middot; {status.get('environment', '?')}</div>
{banner}
{pause_banner}
<div class="cards">
  <div class="card"><div class="label">Equity</div><div class="value">{equity_html}</div></div>
  <div class="card"><div class="label">Open Position</div><div class="value">{position_html}</div></div>
  <div class="card"><div class="label">Market Tradeable</div><div class="value">{tradeable_html}</div></div>
</div>
{pause_button}
<div class="message">{status.get('message', '—')}</div>
<h2>Recent trades</h2>
<table><tr><th>Time (UTC)</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>TP</th><th>SL</th></tr>
{rows}
</table>
<div class="footer">Auto-refreshes every 15s. This is a demo/practice account — see the repo README for validated strategy status before trusting these numbers.</div>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/pause":
            pause()
            self._redirect_home()
            return
        if self.path == "/resume":
            resume()
            self._redirect_home()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_render_html().encode("utf-8"))

    def _redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"Dashboard running — open http://127.0.0.1:{PORT} in your phone's browser")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
