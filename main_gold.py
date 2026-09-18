"""Entry point: run this to paper-trade XAU_USD (gold) on OANDA.

Loop, once per POLL_INTERVAL_SECONDS:
  1. Skip if gold isn't currently tradeable (OANDA reports this directly —
     forex/metals trade ~23/5, roughly Fri 17:00 ET to Sun 17:00 ET closed).
  2. If a position is open past MAX_HOLD_MINUTES, force-close it.
  3. Otherwise, fetch 1-minute candles, derive every other timeframe by
     resampling, and if the multi-timeframe-confirmed signal fires, submit
     a bracket order (entry + take-profit + stop-loss in one shot).

Only one position at a time — this bot focuses on a single instrument.
"""

import time
from datetime import datetime, timezone

import config_gold as config
from execution.oanda_broker import OandaBroker
from logs.pause_flag import is_paused
from logs.status_writer import write_status
from logs.trade_logger import log_trade
from risk.risk_manager import RiskManager
from strategy.exits import compute_exit_levels
from strategy.gold_entry import pullback_signal
from strategy.gold_price_action import divergence_signal, stophunt_signal
from strategy.multi_timeframe import aligned_signal
from strategy.scalp_strategy import generate_signal
from strategy.resample import build_multi_timeframe

_state = {"open_since": None}


def _entry_signal_fn(bars):
    if config.ENTRY_MODE == "stophunt":
        return stophunt_signal(bars)
    if config.ENTRY_MODE == "divergence":
        return divergence_signal(bars)
    if config.ENTRY_MODE == "pullback":
        return pullback_signal(bars, restrict_session=config.RESTRICT_SESSION)
    return generate_signal(bars)


def run_once(broker: OandaBroker, risk: RiskManager) -> dict:
    status = {"instrument": config.INSTRUMENT, "entry_mode": config.ENTRY_MODE, "environment": config.OANDA_ENVIRONMENT}

    if not broker.is_tradeable(config.INSTRUMENT):
        status["message"] = f"{config.INSTRUMENT} not tradeable right now (market closed?)"
        status["tradeable"] = False
        return status
    status["tradeable"] = True

    has_position = broker.has_open_position(config.INSTRUMENT)

    if has_position:
        if _state["open_since"] is not None:
            held_minutes = (datetime.now(timezone.utc) - _state["open_since"]).total_seconds() / 60
            if held_minutes >= config.MAX_HOLD_MINUTES:
                broker.close_position(config.INSTRUMENT)
                _state["open_since"] = None
                has_position = False
                status["message"] = f"Closed {config.INSTRUMENT} after {held_minutes:.1f}m (max hold time)"
        if has_position:
            status["message"] = f"Holding open {config.INSTRUMENT} position"
        status["has_position"] = has_position
        status["equity"] = broker.get_equity()
        return status
    else:
        _state["open_since"] = None

    status["has_position"] = False
    status["paused"] = is_paused()

    if status["paused"]:
        status["message"] = "Paused — not opening new trades (existing positions still managed)"
        status["equity"] = broker.get_equity()
        return status

    if risk.daily_loss_limit_hit():
        status["message"] = "Daily loss limit hit — no new positions today"
        status["equity"] = broker.get_equity()
        return status

    bars_1m = broker.get_recent_1m_bars(config.INSTRUMENT)
    if bars_1m.empty or len(bars_1m) < 60:
        status["message"] = "Waiting for enough price history"
        return status

    tf_data = build_multi_timeframe(bars_1m)
    signal = aligned_signal(tf_data, min_avg_volume=config.MIN_AVG_VOLUME, entry_signal_fn=_entry_signal_fn)
    if signal is None:
        status["message"] = "No signal this check"
        status["equity"] = broker.get_equity()
        return status

    entry_price = float(bars_1m["close"].iloc[-1])
    take_profit, stop_loss = compute_exit_levels(
        signal,
        entry_price,
        bars_1m,
        mode=config.STOP_MODE,
        take_profit_pct=config.TAKE_PROFIT_PCT,
        stop_loss_pct=config.STOP_LOSS_PCT,
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
    log_trade(config.INSTRUMENT, signal, qty, entry_price, take_profit, stop_loss)
    _state["open_since"] = datetime.now(timezone.utc)
    status["message"] = f"Opened {signal} {qty}x{config.INSTRUMENT} @ {entry_price:.2f} (TP {take_profit:.2f} / SL {stop_loss:.2f})"
    status["equity"] = broker.get_equity()
    status["has_position"] = True
    return status


def main() -> None:
    broker = OandaBroker()
    risk = RiskManager(
        starting_equity=broker.get_equity(),
        risk_per_trade_pct=config.RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
        max_open_positions=config.MAX_OPEN_POSITIONS,
    )
    print(f"Starting gold scalp bot on {config.INSTRUMENT} (environment={config.OANDA_ENVIRONMENT})")

    while True:
        try:
            status = run_once(broker, risk)
            print(status.get("message", ""))
            write_status(**status, error=None)
        except Exception as exc:  # keep the loop alive across transient API errors
            print(f"Error in loop: {exc}")
            write_status(instrument=config.INSTRUMENT, entry_mode=config.ENTRY_MODE, error=str(exc))
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
