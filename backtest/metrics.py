from .engine import BacktestResult


def summarize(result: BacktestResult, starting_equity: float) -> dict:
    trades = result.trades
    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)

    r_multiples = [t["pnl"] / t["risk_amount"] for t in trades if t["risk_amount"] > 0]
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

    peak = starting_equity
    max_dd = 0.0
    for _, equity in result.equity_curve:
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)

    return {
        "symbol": result.symbol,
        "total_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / n, 1) if n else 0.0,
        "total_pnl": round(total_pnl, 2),
        "return_pct": round(100 * total_pnl / starting_equity, 2),
        "avg_r_multiple": round(avg_r, 2),
        "max_drawdown_pct": round(100 * max_dd, 2),
        "ending_equity": round(result.ending_equity, 2),
    }
