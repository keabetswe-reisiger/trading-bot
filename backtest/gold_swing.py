"""Backtest for the gold swing (trend-following, hours-long hold) strategy.

Run: python -m backtest.gold_swing

Same no-lookahead design as backtest/engine.py: a signal decided from data
through bar i only acts at bar i+1's open.
"""

import pandas as pd
import yfinance as yf

from risk.risk_manager import RiskManager
from strategy.exits import atr
from strategy.gold_swing import ENTRY_TIMEFRAME, TREND_TIMEFRAMES, aligned_signal, build_swing_timeframes


def fetch_5m_bars(symbol: str = "GC=F", period: str = "60d") -> pd.DataFrame:
    raw = yf.download(symbol, period=period, interval="5m", progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()


def simulate_swing(
    bars_5m: pd.DataFrame,
    tf_data: dict[str, pd.DataFrame],
    *,
    starting_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    daily_loss_limit_pct: float = 3.0,
    atr_period: int = 14,
    atr_stop_multiplier: float = 2.5,
    reward_risk_ratio: float = 3.0,
    max_hold_bars: int = 96,  # 96 * 5min = 8 hours
    entry_window: int = 60,
    trend_window: int = 30,
    max_consecutive_losses: int = 0,
    entry_signal_fn=None,
    min_trend_agree: int = 3,
    spread_cost: float = 0.0,  # round-trip bid-ask cost per unit, deducted from each trade's pnl
):
    risk = RiskManager(starting_equity, risk_per_trade_pct, daily_loss_limit_pct, max_open_positions=1,
                        max_consecutive_losses=max_consecutive_losses)
    equity = starting_equity
    trades = []
    equity_curve = []
    open_trade = None
    times = bars_5m.index
    a = atr(bars_5m, atr_period)

    for i in range(len(times) - 1):
        t = times[i]
        equity_curve.append((t, equity))

        if open_trade is not None:
            bar = bars_5m.iloc[i]
            held_bars = i - open_trade["entry_idx"]
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
            if exit_price is None and held_bars >= max_hold_bars:
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

        bars_by_tf = {ENTRY_TIMEFRAME: bars_5m.loc[:t].tail(entry_window)}
        for tf in TREND_TIMEFRAMES:
            bars_by_tf[tf] = tf_data[tf].loc[:t].tail(trend_window)

        kwargs = {"min_trend_agree": min_trend_agree}
        if entry_signal_fn is not None:
            kwargs["entry_signal_fn"] = entry_signal_fn
        signal = aligned_signal(bars_by_tf, **kwargs)
        if signal is None:
            continue

        entry_idx = i + 1
        entry_time = times[entry_idx]
        entry_price = float(bars_5m["open"].iloc[entry_idx])
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
        last_bar = bars_5m.iloc[-1]
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


def summarize(trades, equity_curve, starting_equity: float) -> dict:
    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)
    r_multiples = [t["pnl"] / t["risk_amount"] for t in trades if t["risk_amount"] > 0]
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
    peak, max_dd = starting_equity, 0.0
    for _, equity in equity_curve:
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)
    long_trades = [t for t in trades if t["side"] == "long"]
    short_trades = [t for t in trades if t["side"] == "short"]
    return {
        "total_trades": n,
        "wins": len(wins),
        "win_rate_pct": round(100 * len(wins) / n, 1) if n else 0.0,
        "total_pnl": round(total_pnl, 2),
        "return_pct": round(100 * total_pnl / starting_equity, 2),
        "avg_r_multiple": round(avg_r, 2),
        "max_drawdown_pct": round(100 * max_dd, 2),
        "long_trades": len(long_trades),
        "long_pnl": round(sum(t["pnl"] for t in long_trades), 2),
        "short_trades": len(short_trades),
        "short_pnl": round(sum(t["pnl"] for t in short_trades), 2),
    }


if __name__ == "__main__":
    bars_5m = fetch_5m_bars()
    tf_data = build_swing_timeframes(bars_5m)

    header = f"{'ATRx':>6}{'R:R':>6}{'HoldH':>7}{'Trades':>8}{'Win%':>8}{'Return%':>10}{'AvgR':>8}{'MaxDD%':>9}{'LongPnL':>10}{'ShortPnL':>10}"
    print(header)
    print("-" * len(header))
    for atr_mult in (1.5, 2.5):
        for rr in (2.0, 3.0):
            for hold_hours in (4, 8):
                trades, curve, end_eq = simulate_swing(
                    bars_5m, tf_data,
                    atr_stop_multiplier=atr_mult,
                    reward_risk_ratio=rr,
                    max_hold_bars=hold_hours * 12,  # 12 five-minute bars per hour
                )
                m = summarize(trades, curve, 100_000.0)
                print(
                    f"{atr_mult:>6}{rr:>6}{hold_hours:>7}{m['total_trades']:>8}{m['win_rate_pct']:>8}"
                    f"{m['return_pct']:>10}{m['avg_r_multiple']:>8}{m['max_drawdown_pct']:>9}"
                    f"{m['long_pnl']:>10}{m['short_pnl']:>10}"
                )
