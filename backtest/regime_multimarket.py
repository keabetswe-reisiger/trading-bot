"""Stress tests for the daily divergence strategy (config_position.py defaults):
  A) gold performance split by market regime + calendar year (all 2000-2026)
  B) same untuned parameters on other markets, correlation, combined portfolio

Run: python -m backtest.regime_multimarket
"""
import numpy as np
import pandas as pd

from backtest.gold_position import fetch_daily_bars, simulate_position
from backtest.gold_swing import summarize
from strategy.gold_position import build_daily_timeframes
from strategy.gold_price_action import divergence_signal

PARAMS = dict(atr_stop_multiplier=2.5, reward_risk_ratio=2.0, max_hold_days=20,
              entry_signal_fn=divergence_signal, max_consecutive_losses=2)


def run(symbol, spread_cost):
    bars = fetch_daily_bars(symbol)
    tf = build_daily_timeframes(bars)
    trades, curve, end = simulate_position(bars, tf, spread_cost=spread_cost, **PARAMS)
    return bars, trades, curve


def avg_r(ts):
    r = [t["pnl"] / t["risk_amount"] for t in ts if t["risk_amount"] > 0]
    return round(float(np.mean(r)), 2) if r else float("nan")


def stats(ts):
    n = len(ts)
    w = sum(t["pnl"] > 0 for t in ts)
    return f"n={n:3d}  win={100*w/n if n else 0:4.1f}%  avgR={avg_r(ts):5.2f}  sumR={sum(t['pnl']/t['risk_amount'] for t in ts):6.1f}"


print("=== A) GOLD by regime (GC=F, $1.61 spread, 2000-2026) ===")
bars, trades, curve = run("GC=F", 1.61)
print("ALL      ", stats(trades))
ret250 = bars["close"].pct_change(250)
def regime(t):
    r = ret250.loc[:t].iloc[-1]
    if pd.isna(r): return "warmup"
    return "UP (250d>+10%)" if r > .10 else "DOWN (250d<-10%)" if r < -.10 else "SIDEWAYS (+-10%)"
# entry_time is the bar AFTER the signal; regime judged at signal time (previous bar)
for name in ["UP (250d>+10%)", "SIDEWAYS (+-10%)", "DOWN (250d<-10%)"]:
    sub = [t for t in trades if regime(bars.index[max(bars.index.get_loc(t["entry_time"]) - 1, 0)]) == name]
    print(f"{name:18s}", stats(sub))
    for side in ("long", "short"):
        print(f"   {side:5s}          ", stats([t for t in sub if t["side"] == side]))
print("-- named eras --")
eras = {"2000-2010 bull start": ("2000", "2010"), "2011-09..2015-12 gold bear": ("2011-09-06", "2015-12-17"),
        "2013 crash yr": ("2013", "2013"), "2022 rate-hike yr": ("2022", "2022"), "2016-2019 range/recovery": ("2016", "2019")}
for k, (a, b) in eras.items():
    sub = [t for t in trades if pd.Timestamp(a) <= t["entry_time"] <= pd.Timestamp(b) + pd.Timedelta(days=364 if len(b) == 4 else 0)]
    print(f"{k:28s}", stats(sub), f" gold move {100*(bars['close'].loc[a:b].iloc[-1]/bars['close'].loc[a:b].iloc[0]-1):+.0f}%")
print("-- by year --")
for y in range(2000, 2027):
    sub = [t for t in trades if t["entry_time"].year == y]
    if sub:
        yr = bars["close"][bars.index.year == y]
        print(y, stats(sub), f" gold {100*(yr.iloc[-1]/yr.iloc[0]-1):+.0f}%")
yrs = {y: sum(t["pnl"] / t["risk_amount"] for t in trades if t["entry_time"].year == y) for y in range(2000, 2027)}
print("losing years (sumR<0):", [y for y, v in yrs.items() if v < 0])
# worst rolling drawdown in R
r = pd.Series([t["pnl"] / t["risk_amount"] for t in trades]).cumsum()
print("max R drawdown:", round(float((r.cummax() - r).max()), 1), "R;  longest losing streak:",
      max((len(list(g)) for k, g in __import__('itertools').groupby([t["pnl"] <= 0 for t in trades]) if k), default=0))

print("\n=== B) same UNTUNED params on other markets ===")
markets = {"GC=F": 1.61, "SI=F": 0.03, "HG=F": 0.001, "CL=F": 0.03, "^GSPC": 0.5, "TLT": 0.02, "EURUSD=X": 0.0002, "USDJPY=X": 0.02}
res, daily = {}, {}
for sym, sp in markets.items():
    try:
        b, ts, cv = run(sym, sp)
    except Exception as e:
        print(sym, "failed", e); continue
    if len(ts) < 5: print(sym, "too few trades", len(ts)); continue
    res[sym] = (b, ts)
    mid = pd.Timestamp("2018-01-01")
    print(f"{sym:9s} {b.index[0].date()}  ALL {stats(ts)} | <2018 avgR {avg_r([t for t in ts if t['entry_time']<mid])}  >=2018 avgR {avg_r([t for t in ts if t['entry_time']>=mid])}")
    s = pd.Series({t["exit_time"]: t["pnl"] / 100_000 for t in ts}).groupby(level=0).sum()
    daily[sym] = s.reindex(b.index, fill_value=0.0)
d = pd.DataFrame(daily).dropna()
print("\ndaily strategy-P&L correlation matrix (mostly zeros between trades, so read as rough):")
print(d.corr().round(2).to_string())
wk = d.resample("ME").sum()
print("\nmonthly P&L correlation:"); print(wk.corr().round(2).to_string())
port = d.sum(axis=1)
eq = (1 + port).cumprod()
print(f"\nCombined equal-risk portfolio ({len(d.columns)} mkts, 1% risk each): total {100*(eq.iloc[-1]-1):.1f}%  maxDD {100*(1-eq/eq.cummax()).max():.1f}%  "
      f"gold-only: total {100*((1+d['GC=F']).cumprod().iloc[-1]-1):.1f}%  maxDD {100*(1-(1+d['GC=F']).cumprod()/(1+d['GC=F']).cumprod().cummax()).max():.1f}%")
ann = port.groupby(port.index.year).sum()
print("portfolio yearly return %:", (100*ann).round(1).to_dict())
