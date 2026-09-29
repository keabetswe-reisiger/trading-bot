"""Long-only vs both-sides comparison for the daily divergence strategy.
Run: python -m backtest.long_only_test"""
import numpy as np
import pandas as pd

from backtest.gold_position import fetch_daily_bars, simulate_position
from backtest.gold_swing import summarize
from strategy.gold_position import build_daily_timeframes
from strategy.gold_price_action import divergence_signal

bars = fetch_daily_bars("GC=F")
tf = build_daily_timeframes(bars)
long_only = lambda b: (lambda s: s if s == "long" else None)(divergence_signal(b))
BASE = dict(atr_stop_multiplier=2.5, reward_risk_ratio=2.0, max_hold_days=20, max_consecutive_losses=2, spread_cost=1.61)

def R(ts): return [t["pnl"] / t["risk_amount"] for t in ts]
def line(name, ts, curve):
    r = R(ts); s = summarize(ts, curve, 100_000)
    print(f"{name:26s} n={len(ts):3d} win={s['win_rate_pct']:4.1f}% avgR={np.mean(r):5.2f} sumR={sum(r):5.1f} ret={s['return_pct']:6.1f}% maxDD={s['max_drawdown_pct']:4.1f}%")

variants = {"both sides": divergence_signal, "long-only": long_only}
out = {}
for name, fn in variants.items():
    ts, cv, end = simulate_position(bars, tf, entry_signal_fn=fn, **BASE)
    out[name] = (ts, cv)
print("=== full 2000-2026 ===")
for n, (ts, cv) in out.items(): line(n, ts, cv)
print("\n=== train <2018 / test >=2018 (config was chosen on train) ===")
mid = pd.Timestamp("2018-01-01")
for n, (ts, cv) in out.items():
    for lab, sub in (("train", [t for t in ts if t["entry_time"] < mid]), ("test ", [t for t in ts if t["entry_time"] >= mid])):
        cvs = [(t, e) for t, e in cv if (t < mid) == (lab == "train")]
        line(f"{n} {lab}", sub, cvs)
print("\n=== spread sensitivity (long-only) ===")
for sp in (0, 1.61, 3.0):
    ts, cv, _ = simulate_position(bars, tf, entry_signal_fn=long_only, **{**BASE, "spread_cost": sp})
    line(f"spread ${sp}", ts, cv)
print("\n=== robustness: neighbouring params (long-only, full) ===")
for atrm, rr, hold in [(2.0, 2.0, 20), (3.0, 2.0, 20), (2.5, 1.5, 20), (2.5, 3.0, 40), (2.5, 2.0, 10), (2.5, 2.0, 30)]:
    ts, cv, _ = simulate_position(bars, tf, entry_signal_fn=long_only, **{**BASE, "atr_stop_multiplier": atrm, "reward_risk_ratio": rr, "max_hold_days": hold})
    line(f"atr{atrm} rr{rr} hold{hold}", ts, cv)
ts, cv = out["long-only"]
print("\n=== long-only by year ===")
yrs = {}
for y in range(2000, 2027):
    sub = [t for t in ts if t["entry_time"].year == y]
    if sub: yrs[y] = sum(R(sub))
print({y: round(v, 1) for y, v in yrs.items()})
print("losing years:", [y for y, v in yrs.items() if v < 0], f"({len(yrs)} traded years)")
r = pd.Series(R(ts)).cumsum(); print("max R drawdown:", round(float((r.cummax() - r).max()), 1))
days = sum((t["exit_time"] - t["entry_time"]).days for t in ts); span = (bars.index[-1] - bars.index[0]).days
print(f"time in market: {100*days/span:.0f}%")
bh = bars["close"].iloc[-1] / bars["close"].iloc[0] - 1
print(f"gold buy&hold 2000-2026: {100*bh:.0f}%  |  by regime (long-only):")
ret250 = bars["close"].pct_change(250)
for nm, f in (("up", lambda x: x > .1), ("sideways", lambda x: -.1 <= x <= .1), ("down", lambda x: x < -.1)):
    sub = [t for t in ts if pd.notna(x := ret250.loc[:bars.index[max(bars.index.get_loc(t["entry_time"]) - 1, 0)]].iloc[-1]) and f(x)]
    print(f"  {nm:9s} n={len(sub):3d} avgR={np.mean(R(sub)) if sub else float('nan'):5.2f}")
