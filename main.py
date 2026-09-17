"""Entry point: run this while the market is open to paper-trade the scalp strategy.

Loop, once per POLL_INTERVAL_SECONDS:
  1. Skip if market closed or the daily loss limit has been hit.
  2. Force-close any position held past MAX_HOLD_MINUTES (a scalp that
     didn't hit its target/stop in time is no longer a scalp).
  3. For symbols with no open position, check for a fresh signal and,
     if risk allows, submit a bracket order (entry + take-profit + stop-loss
     in one shot, so exits are handled by the broker even if this process
     is down).
"""

import time
from datetime import datetime, timezone

import pandas as pd
from alpaca.trading.enums import OrderSide

import config
from execution.broker import AlpacaBroker
from logs.trade_logger import log_trade
from risk.risk_manager import RiskManager
from strategy.exits import compute_exit_levels
from strategy.multi_timeframe import TIMEFRAMES, aligned_signal

_open_since: dict[str, datetime] = {}  # symbol -> when we opened it (in-memory only)


def run_once(broker: AlpacaBroker, risk: RiskManager) -> None:
    if not broker.is_market_open():
        print("Market closed, sleeping...")
        return

    positions = broker.get_open_positions()

    for symbol, entered_at in list(_open_since.items()):
        if symbol not in positions:
            _open_since.pop(symbol, None)
            continue
        held_minutes = (datetime.now(timezone.utc) - entered_at).total_seconds() / 60
        if held_minutes >= config.MAX_HOLD_MINUTES:
            print(f"{symbol}: max hold time reached ({held_minutes:.1f}m), closing.")
            broker.close_position(symbol)
            _open_since.pop(symbol, None)

    if risk.daily_loss_limit_hit():
        print("Daily loss limit hit — no new positions today.")
        return

    for symbol in config.SYMBOLS:
        if symbol in positions:
            continue
        if not risk.can_open_new_position(len(positions)):
            break

        bars_by_tf = broker.get_multi_timeframe_bars(symbol, TIMEFRAMES)
        if bars_by_tf.get("1m", pd.DataFrame()).empty:
            continue

        signal = aligned_signal(bars_by_tf, min_avg_volume=config.MIN_AVG_VOLUME)
        if signal is None:
            continue

        entry_price = float(bars_by_tf["1m"]["close"].iloc[-1])
        take_profit, stop_loss = compute_exit_levels(
            signal,
            entry_price,
            bars_by_tf["1m"],
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
            continue

        side = OrderSide.BUY if signal == "long" else OrderSide.SELL
        broker.submit_bracket_order(symbol, qty, side, entry_price, take_profit, stop_loss)
        log_trade(symbol, signal, qty, entry_price, take_profit, stop_loss)
        _open_since[symbol] = datetime.now(timezone.utc)
        positions[symbol] = True
        print(f"Opened {signal} {qty}x{symbol} @ {entry_price:.2f} (TP {take_profit:.2f} / SL {stop_loss:.2f})")


def main() -> None:
    broker = AlpacaBroker()
    risk = RiskManager(
        starting_equity=broker.get_equity(),
        risk_per_trade_pct=config.RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
        max_open_positions=config.MAX_OPEN_POSITIONS,
    )
    print(f"Starting scalp bot on {config.SYMBOLS} (paper={config.ALPACA_PAPER})")

    while True:
        try:
            run_once(broker, risk)
        except Exception as exc:  # keep the loop alive across transient API errors
            print(f"Error in loop: {exc}")
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
