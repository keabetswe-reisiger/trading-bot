"""Entry point: run this to paper-trade genuine multi-day swing/position
gold trades on a SEPARATE OANDA account from main_gold.py's 1-minute bot
(see config_position.py's docstring for why — the same XAU_USD position
slot would otherwise be fought over by both bots).

Loop, once per POLL_INTERVAL_SECONDS (default every 6 hours — a daily
strategy has nothing new to see between checks the way a 1-minute scalp
does):
  1. Skip if gold isn't currently tradeable.
  2. If a position is open past MAX_HOLD_DAYS, force-close it.
  3. Otherwise, fetch daily candles, derive weekly/monthly timeframes, and
     if the trend-confirmed signal fires, submit a bracket order.

Unlike main_gold.py/main.py, open-trade state is persisted to disk
(logs/position_state.py), not just kept in memory — a 10-40 day hold is far
more likely to outlive a process restart than a 10-minute scalp is.
"""

import os
import time
from datetime import datetime, timezone

import config_position as config
from execution.oanda_broker import OandaBroker
from logs.activity_log import log_activity
from logs.pause_flag import is_paused
from logs.position_state import load_state, save_state
from logs.status_writer import write_status
from logs.trade_logger import log_trade
from risk.risk_manager import RiskManager
from strategy.breakout import breakout_signal
from strategy.exits import compute_exit_levels
from strategy.gold_position import aligned_signal, build_daily_timeframes
from strategy.gold_price_action import divergence_signal

_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
STATUS_PATH = os.path.join(_LOGS_DIR, "position_status.json")
ACTIVITY_PATH = os.path.join(_LOGS_DIR, "position_activity.jsonl")


def _entry_signal_fn(bars):
    if config.ENTRY_MODE == "breakout":
        return breakout_signal(bars)
    return divergence_signal(bars)


def _record_last_trade_pnl(broker: OandaBroker, risk: RiskManager, at: datetime) -> None:
    pnl = broker.get_last_closed_trade_pnl(config.INSTRUMENT)
    if pnl is not None:
        risk.record_closed_trade(pnl, at=at)


def run_once(broker: OandaBroker, risk: RiskManager) -> dict:
    status = {"instrument": config.INSTRUMENT, "entry_mode": config.ENTRY_MODE, "environment": config.OANDA_ENVIRONMENT}

    if not broker.is_tradeable(config.INSTRUMENT):
        status["message"] = f"{config.INSTRUMENT} not tradeable right now (market closed?)"
        status["tradeable"] = False
        return status
    status["tradeable"] = True

    has_position = broker.has_open_position(config.INSTRUMENT)
    now = datetime.now(timezone.utc)
    state = load_state()

    if has_position:
        if state is not None:
            opened_at = datetime.fromisoformat(state["opened_at"])
            held_days = (now - opened_at).days
            if held_days >= config.MAX_HOLD_DAYS:
                broker.close_position(config.INSTRUMENT)
                _record_last_trade_pnl(broker, risk, now)
                save_state(None)
                has_position = False
                status["message"] = f"Closed {config.INSTRUMENT} after {held_days}d (max hold time)"
        if has_position:
            status["message"] = "Holding open position"
        status["has_position"] = has_position
        status["equity"] = broker.get_equity()
        return status
    else:
        if state is not None:
            # We had a position tracked as open; it's gone now without us
            # closing it, meaning the broker's TP/SL bracket order closed it.
            _record_last_trade_pnl(broker, risk, now)
            save_state(None)

    status["has_position"] = False
    status["paused"] = is_paused()

    if status["paused"]:
        status["message"] = "Paused — not opening new trades (existing positions still managed)"
        status["equity"] = broker.get_equity()
        return status

    if risk.daily_loss_limit_hit(at=now):
        status["message"] = "Daily loss limit hit — no new positions today"
        status["equity"] = broker.get_equity()
        return status

    bars_1d = broker.get_recent_daily_bars(config.INSTRUMENT)
    if bars_1d.empty or len(bars_1d) < 200:
        status["message"] = "Waiting for enough daily price history"
        return status

    tf_data = build_daily_timeframes(bars_1d)
    signal = aligned_signal(tf_data, entry_signal_fn=_entry_signal_fn)
    if signal is None:
        status["message"] = "No signal this check"
        status["equity"] = broker.get_equity()
        return status

    entry_price = float(bars_1d["close"].iloc[-1])
    take_profit, stop_loss = compute_exit_levels(
        signal,
        entry_price,
        bars_1d,
        mode=config.STOP_MODE,
        atr_period=config.ATR_PERIOD,
        atr_stop_multiplier=config.ATR_STOP_MULTIPLIER,
        reward_risk_ratio=config.REWARD_RISK_RATIO,
    )

    equity = broker.get_equity()
    qty = risk.position_size(equity, entry_price, stop_loss)
    if qty <= 0:
        status["message"] = "Signal fired but position size rounded to 0"
        status["equity"] = equity
        return status

    units = qty if signal == "long" else -qty
    broker.submit_bracket_order(config.INSTRUMENT, units, take_profit, stop_loss)
    log_trade(config.INSTRUMENT, signal, qty, entry_price, take_profit, stop_loss, note="position")
    save_state({"opened_at": now.isoformat(), "entry_price": entry_price, "qty": qty, "side": signal})
    status["message"] = f"Opened {signal} {qty}x{config.INSTRUMENT} @ {entry_price:.2f} (TP {take_profit:.2f} / SL {stop_loss:.2f})"
    status["equity"] = broker.get_equity()
    status["has_position"] = True
    return status


def main() -> None:
    broker = OandaBroker(config.OANDA_API_TOKEN, config.OANDA_ACCOUNT_ID, config.OANDA_ENVIRONMENT)
    risk = RiskManager(
        starting_equity=broker.get_equity(),
        risk_per_trade_pct=config.RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
        max_open_positions=config.MAX_OPEN_POSITIONS,
        max_consecutive_losses=config.MAX_CONSECUTIVE_LOSSES,
        max_position_value_pct=config.MAX_POSITION_VALUE_PCT,
    )
    print(f"Starting gold position bot on {config.INSTRUMENT} (environment={config.OANDA_ENVIRONMENT}, mode={config.ENTRY_MODE})")

    while True:
        try:
            status = run_once(broker, risk)
            print(status.get("message", ""))
            write_status(path=STATUS_PATH, **status, error=None)
            log_activity(status.get("message", ""), path=ACTIVITY_PATH)
        except Exception as exc:  # keep the loop alive across transient API errors
            print(f"Error in loop: {exc}")
            write_status(path=STATUS_PATH, instrument=config.INSTRUMENT, entry_mode=config.ENTRY_MODE, error=str(exc))
            log_activity(f"Error: {exc}", path=ACTIVITY_PATH)
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
