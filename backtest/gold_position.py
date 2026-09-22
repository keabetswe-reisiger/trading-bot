"""Backtest for genuine multi-day swing/position trading (strategy.gold_position)
— daily bars, holds of days to weeks. Same no-lookahead design as every
other backtest engine in this project: a signal decided from data through
bar i only acts at bar i+1's open.

Run: python -m backtest.gold_position
"""

import time

import pandas as pd
import yfinance as yf

from backtest.gold_swing import summarize  # reused as-is, same trade/equity_curve shape
from risk.risk_manager import RiskManager
from strategy.exits import atr
from strategy.gold_position import ENTRY_TIMEFRAME, TREND_TIMEFRAMES, aligned_signal, build_daily_timeframes


def fetch_daily_bars(symbol: str = "GC=F", period: str = "max", retries: int = 3) -> pd.DataFrame:
    for attempt in range(retries):
        raw = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
        if not raw.empty:
            break
        time.sleep(5)
    else:
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        empty.index = pd.DatetimeIndex([], name="time")
        return empty
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()


def simulate_position(
    bars_1d: pd.DataFrame,
    tf_data: dict[str, pd.DataFrame],
    *,
    starting_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    daily_loss_limit_pct: float = 3.0,
    atr_period: int = 14,
    atr_stop_multiplier: float = 2.5,
    reward_risk_ratio: float = 3.0,
    max_hold_days: int = 20,
    entry_window: int = 60,
    trend_window: int = 30,
    max_consecutive_losses: int = 0,
    entry_signal_fn=None,
    min_trend_agree: int = 1,
    spread_cost: float = 0.0,  # round-trip bid-ask cost per unit, deducted from each trade's pnl
):
    risk = RiskManager(starting_equity, risk_per_trade_pct, daily_loss_limit_pct, max_open_positions=1,
                        max_consecutive_losses=max_consecutive_losses)
    equity = starting_equity
    trades = []
    equity_curve = []
    open_trade = None
    times = bars_1d.index
    a = atr(bars_1d, atr_period)

    for i in range(len(times) - 1):
        t = times[i]
        equity_curve.append((t, equity))

        if open_trade is not None:
            bar = bars_1d.iloc[i]
            held_days = i - open_trade["entry_idx"]
            exit_price, reason = None, None
            if open_trade["side"] == "long":
                if bar["low"] <= open_trade["sl"]:
                    exit_price, reason = open_trade["sl"], "stop"
                elif bar["high"] >= open_trade["tp"]:
                    exit_price, reason = open_trade["tp"], "target"
            else:
                if bar["high"] >= open_trade["sl"]:
                    exit_price, reason = open_trade["sl"], "stop"
                elif bar["low"] <= open_trade["tp"]:
                    exit_price, reason = open_trade["tp"], "target"
            if exit_price is None and held_days >= max_hold_days:
                exit_price, reason = float(bar["close"]), "time"
            if exit_price is not None:
                direction = 1 if open_trade["side"] == "long" else -1
                pnl = (exit_price - open_trade["entry_price"]) * open_trade["qty"] * direction
                pnl -= open_trade["qty"] * spread_cost
                equity += pnl
                risk.record_closed_trade(pnl, at=t)
                trades.append(
                    {
                        "side": open_trade["side"],
                        "entry_time": open_trade["entry_time"],
                        "exit_time": t,
                        "pnl": pnl,
                        "risk_amount": open_trade["risk_amount"],
                        "reason": reason,
                    }
                )
                open_trade = None
            continue

        if risk.daily_loss_limit_hit(at=t):
            continue

        bars_by_tf = {ENTRY_TIMEFRAME: bars_1d.loc[:t].tail(entry_window)}
        for tf in TREND_TIMEFRAMES:
            bars_by_tf[tf] = tf_data[tf].loc[:t].tail(trend_window)

        signal = aligned_signal(bars_by_tf, entry_signal_fn=entry_signal_fn, min_trend_agree=min_trend_agree)
        if signal is None:
            continue

        entry_idx = i + 1
        entry_time = times[entry_idx]
        entry_price = float(bars_1d["open"].iloc[entry_idx])
        atr_val = a.loc[:t].iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            continue
        stop_dist = atr_stop_multiplier * atr_val
        target_dist = reward_risk_ratio * stop_dist
        if signal == "long":
            sl, tp = entry_price - stop_dist, entry_price + target_dist
        else:
            sl, tp = entry_price + stop_dist, entry_price - target_dist

        qty = risk.position_size(equity, entry_price, sl)
        if qty <= 0:
            continue

        open_trade = {
            "side": signal,
            "qty": qty,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "entry_idx": entry_idx,
            "sl": sl,
            "tp": tp,
            "risk_amount": qty * stop_dist,
        }

    if open_trade is not None:
        last_bar = bars_1d.iloc[-1]
        exit_price = float(last_bar["close"])
        direction = 1 if open_trade["side"] == "long" else -1
        pnl = (exit_price - open_trade["entry_price"]) * open_trade["qty"] * direction
        pnl -= open_trade["qty"] * spread_cost
        equity += pnl
        trades.append(
            {
                "side": open_trade["side"],
                "entry_time": open_trade["entry_time"],
                "exit_time": times[-1],
                "pnl": pnl,
                "risk_amount": open_trade["risk_amount"],
                "reason": "end_of_data",
            }
        )

    equity_curve.append((times[-1], equity))
    return trades, equity_curve, equity
