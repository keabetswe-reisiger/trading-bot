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
from logs.trade_logger import log_trade
from risk.risk_manager import RiskManager
from strategy.exits import compute_exit_levels
from strategy.gold_entry import pullback_signal
from strategy.multi_timeframe import aligned_signal
from strategy.scalp_strategy import generate_signal
from strategy.resample import build_multi_timeframe

_state = {"open_since": None}


def _entry_signal_fn(bars):
    if config.ENTRY_MODE == "pullback":
        return pullback_signal(bars, restrict_session=config.RESTRICT_SESSION)
    return generate_signal(bars)


def run_once(broker: OandaBroker, risk: RiskManager) -> None:
    if not broker.is_tradeable(config.INSTRUMENT):
        print(f"{config.INSTRUMENT} not tradeable right now, sleeping...")
        return

    has_position = broker.has_open_position(config.INSTRUMENT)

    if has_position:
        if _state["open_since"] is not None:
            held_minutes = (datetime.now(timezone.utc) - _state["open_since"]).total_seconds() / 60
            if held_minutes >= config.MAX_HOLD_MINUTES:
                print(f"{config.INSTRUMENT}: max hold time reached ({held_minutes:.1f}m), closing.")
                broker.close_position(config.INSTRUMENT)
                _state["open_since"] = None
                has_position = False
        return  # bracket TP/SL already protects an open position
    else:
        _state["open_since"] = None

    if risk.daily_loss_limit_hit():
        print("Daily loss limit hit — no new positions today.")
        return

    bars_1m = broker.get_recent_1m_bars(config.INSTRUMENT)
    if bars_1m.empty or len(bars_1m) < 60:
        return

    tf_data = build_multi_timeframe(bars_1m)
    signal = aligned_signal(tf_data, min_avg_volume=config.MIN_AVG_VOLUME, entry_signal_fn=_entry_signal_fn)
    if signal is None:
        return

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
        return

    units = qty if signal == "long" else -qty
    broker.submit_bracket_order(config.INSTRUMENT, units, take_profit, stop_loss)
    log_trade(config.INSTRUMENT, signal, qty, entry_price, take_profit, stop_loss)
    _state["open_since"] = datetime.now(timezone.utc)
    print(f"Opened {signal} {qty}x{config.INSTRUMENT} @ {entry_price:.2f} (TP {take_profit:.2f} / SL {stop_loss:.2f})")


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
            run_once(broker, risk)
        except Exception as exc:  # keep the loop alive across transient API errors
            print(f"Error in loop: {exc}")
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
