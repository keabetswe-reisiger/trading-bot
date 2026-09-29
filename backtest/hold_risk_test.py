"""Drawdown / time-in-market / spread / skipped-signal check for hold lengths.
Run: python -m backtest.hold_risk_test"""
import numpy as np, pandas as pd
from backtest.gold_position import fetch_daily_bars, simulate_position
from backtest.gold_swing import summarize
from strategy.gold_position import build_daily_timeframes
from strategy.gold_price_action import divergence_signal

bars = fetch_daily_bars("GC=F"); tf = build_daily_timeframes(bars)
mid = pd.Timestamp("2018-01-01"); span = (bars.index[-1] - bars.index[0]).days
def run(hold, sp=1.61, mcl=2):
    return simulate_position(bars, tf, entry_signal_fn=divergence_signal, atr_stop_multiplier=2.5, reward_risk_ratio=2.0,
                             max_hold_days=hold, max_consecutive_losses=mcl, spread_cost=sp)
print("hold | trades  avgR  ret%  maxDD% | maxR-DD  streak  inMkt% | longest flat(yrs) | test avgR/ret%/DD% | avgR @ spread 0/1.61/3/5")
for hold in (20, 30, 40, 60):
    ts, cv, _ = run(hold); s = summarize(ts, cv, 100_000)
    r = [t["pnl"]/t["risk_amount"] for t in ts]; c = pd.Series(r).cumsum()
    streak = max((len(list(g)) for k, g in __import__("itertools").groupby([x <= 0 for x in r]) if k), default=0)
    inmkt = 100 * sum((t["exit_time"] - t["entry_time"]).days for t in ts) / span
    eq = pd.Series({t: e for t, e in cv}); peak = eq.cummax(); uw = (eq < peak)
    grp = (uw != uw.shift()).cumsum(); longest = max((( g.index[-1] - g.index[0]).days for _, g in eq[uw].groupby(grp[uw])), default=0) / 365
    te = [t for t in ts if t["entry_time"] >= mid]; cte = [(t, e) for t, e in cv if t >= mid]; ste = summarize(te, cte, cte[0][1])
    spr = " / ".join(f"{np.mean([t['pnl']/t['risk_amount'] for t in run(hold, sp)[0]]):.2f}" for sp in (0, 1.61, 3, 5))
    print(f"{hold:3d}d | {len(ts):3d}  {np.mean(r):5.2f} {s['return_pct']:5.1f} {s['max_drawdown_pct']:5.1f} | {float((c.cummax()-c).max()):5.1f}  {streak:3d}  {inmkt:4.0f} | {longest:4.1f} | {np.mean([t['pnl']/t['risk_amount'] for t in te]):.2f}/{ste['return_pct']:.1f}/{ste['max_drawdown_pct']:.1f} | {spr}")
# skipped signals: signals fired while flat is unaffected; count opportunities lost = trades of 20d not in longer runs
print("\nAnnual return % (compounded equity, 1% risk) by year — 20d vs 40d:")
for hold in (20, 40):
    ts, cv, _ = run(hold); eq = pd.Series({t: e for t, e in cv}); ye = eq.groupby(eq.index.year).last(); yr = ye.pct_change().fillna(ye.iloc[0]/100_000-1)
    print(hold, {y: round(100*v, 1) for y, v in yr.items()})
