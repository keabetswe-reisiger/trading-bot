"""Does a longer max-hold beat 20d out of sample? Choose on train (<2018) only.
Run: python -m backtest.hold_days_test"""
import numpy as np, pandas as pd
from backtest.gold_position import fetch_daily_bars, simulate_position
from strategy.gold_position import build_daily_timeframes
from strategy.gold_price_action import divergence_signal

bars = fetch_daily_bars("GC=F"); tf = build_daily_timeframes(bars)
mid = pd.Timestamp("2018-01-01")
lo = lambda b: (lambda s: s if s == "long" else None)(divergence_signal(b))
def st(ts):
    r = [t["pnl"] / t["risk_amount"] for t in ts if t["risk_amount"] > 0]
    return f"n={len(r):3d} win={100*np.mean([x>0 for x in r]) if r else 0:4.1f}% avgR={np.mean(r) if r else float('nan'):5.2f} sumR={sum(r):5.1f}"
for label, fn in (("both sides", divergence_signal), ("long-only", lo)):
    print(f"=== {label} ===")
    for hold in (10, 15, 20, 25, 30, 40, 60):
        ts, _, _ = simulate_position(bars, tf, entry_signal_fn=fn, atr_stop_multiplier=2.5, reward_risk_ratio=2.0,
                                     max_hold_days=hold, max_consecutive_losses=2, spread_cost=1.61)
        tr = [t for t in ts if t["entry_time"] < mid]; te = [t for t in ts if t["entry_time"] >= mid]
        reasons = pd.Series([t["reason"] for t in ts]).value_counts().to_dict()
        print(f"hold {hold:2d}d | TRAIN {st(tr)} | TEST {st(te)} | exits {reasons}")
