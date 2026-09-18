"""Replays the live strategy bar-by-bar over historical data.

No lookahead: a signal decided using data available through bar i is only
acted on at bar i+1's open (the earliest price you could actually have
traded at). Exits are simulated the same way live trading works — a bracket
order's take-profit/stop-loss, or a forced exit at MAX_HOLD_MINUTES.
"""

from dataclasses import dataclass, field

import pandas as pd

from risk.risk_manager import RiskManager
from strategy.exits import compute_exit_levels
from strategy.multi_timeframe import aligned_signal


def _check_exit(open_trade: dict, bar: pd.Series, t, max_hold_minutes: float):
    held_minutes = (t - open_trade["entry_time"]).total_seconds() / 60
    if open_trade["side"] == "long":
        if bar["low"] <= open_trade["sl"]:
            return open_trade["sl"], "stop"
        if bar["high"] >= open_trade["tp"]:
            return open_trade["tp"], "target"
    else:
        if bar["high"] >= open_trade["sl"]:
            return open_trade["sl"], "stop"
        if bar["low"] <= open_trade["tp"]:
            return open_trade["tp"], "target"
    if held_minutes >= max_hold_minutes:
        return float(bar["close"]), "time"
    return None, None


@dataclass
class BacktestResult:
    symbol: str
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)  # [(timestamp, equity)]
    ending_equity: float = 0.0


def simulate(
    symbol: str,
    bars_1m: pd.DataFrame,
    tf_data: dict[str, pd.DataFrame],
    *,
    starting_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    daily_loss_limit_pct: float = 3.0,
    stop_mode: str = "atr",
    take_profit_pct: float = 0.3,
    stop_loss_pct: float = 0.15,
    atr_period: int = 14,
    atr_stop_multiplier: float = 1.5,
    reward_risk_ratio: float = 2.0,
    max_hold_minutes: float = 10,
    min_avg_volume: int = 2000,
    entry_window: int = 60,
    trend_window: int = 30,
    entry_signal_fn=None,
) -> BacktestResult:
    risk = RiskManager(starting_equity, risk_per_trade_pct, daily_loss_limit_pct, max_open_positions=1)
    equity = starting_equity
    result = BacktestResult(symbol=symbol)
    open_trade = None
    times = bars_1m.index

    for i in range(len(times) - 1):
        t = times[i]
        result.equity_curve.append((t, equity))

        if open_trade is not None:
            bar = bars_1m.iloc[i]
            exit_price, reason = _check_exit(open_trade, bar, t, max_hold_minutes)
            if exit_price is not None:
                direction = 1 if open_trade["side"] == "long" else -1
                pnl = (exit_price - open_trade["entry_price"]) * open_trade["qty"] * direction
                equity += pnl
                risk.record_closed_trade(pnl)
                result.trades.append(
                    {
                        "symbol": symbol,
                        "side": open_trade["side"],
                        "qty": open_trade["qty"],
                        "entry_time": open_trade["entry_time"],
                        "exit_time": t,
                        "entry_price": open_trade["entry_price"],
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "risk_amount": open_trade["risk_amount"],
                        "reason": reason,
                    }
                )
                open_trade = None
            continue

        if risk.daily_loss_limit_hit():
            continue

        window_1m = bars_1m.loc[:t].tail(entry_window)
        bars_by_tf = {"1m": window_1m}
        for label, df in tf_data.items():
            if label == "1m":
                continue
            bars_by_tf[label] = df.loc[:t].tail(trend_window)

        kwargs = {"min_avg_volume": min_avg_volume}
        if entry_signal_fn is not None:
            kwargs["entry_signal_fn"] = entry_signal_fn
        signal = aligned_signal(bars_by_tf, **kwargs)
        if signal is None:
            continue

        entry_time = times[i + 1]
        entry_price = float(bars_1m["open"].iloc[i + 1])
        take_profit, stop_loss = compute_exit_levels(
            signal,
            entry_price,
            window_1m,
            mode=stop_mode,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            atr_period=atr_period,
            atr_stop_multiplier=atr_stop_multiplier,
            reward_risk_ratio=reward_risk_ratio,
        )
        qty = risk.position_size(equity, entry_price, stop_loss)
        if qty <= 0:
            continue

        open_trade = {
            "side": signal,
            "qty": qty,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "tp": take_profit,
            "sl": stop_loss,
            "risk_amount": qty * abs(entry_price - stop_loss),
        }

    if open_trade is not None:
        last_bar = bars_1m.iloc[-1]
        exit_price = float(last_bar["close"])
        direction = 1 if open_trade["side"] == "long" else -1
        pnl = (exit_price - open_trade["entry_price"]) * open_trade["qty"] * direction
        equity += pnl
        result.trades.append(
            {
                "symbol": symbol,
                "side": open_trade["side"],
                "qty": open_trade["qty"],
                "entry_time": open_trade["entry_time"],
                "exit_time": times[-1],
                "entry_price": open_trade["entry_price"],
                "exit_price": exit_price,
                "pnl": pnl,
                "risk_amount": open_trade["risk_amount"],
                "reason": "end_of_data",
            }
        )

    result.equity_curve.append((times[-1], equity))
    result.ending_equity = equity
    return result
