"""Guardrails around the strategy: how much to risk, and when to stop trading.

Nothing here decides *what* to trade — that's the strategy's job. This only
decides *how much* and *whether it's still allowed to trade today*.

Day-rollover is driven by an explicit `at` timestamp passed by the caller,
not the real wall-clock date — a backtest replays days far faster than real
time, so relying on the system clock meant "today" never actually rolled
over during a backtest, and a tripped daily limit stayed tripped for the
rest of the run instead of resetting each simulated day.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass
class RiskManager:
    starting_equity: float
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    max_open_positions: int
    max_consecutive_losses: int = 0  # 0 = disabled
    max_position_value_pct: float = 500.0  # cap notional exposure as % of equity (500% ≈ 5x leverage); 0 = disabled

    trading_day: date | None = None
    realized_pnl_today: float = 0.0
    day_trade_count_today: int = 0
    consecutive_losses: int = 0

    def _roll_day_if_needed(self, at: datetime) -> None:
        today = at.date()
        if today != self.trading_day:
            self.trading_day = today
            self.realized_pnl_today = 0.0
            self.day_trade_count_today = 0
            self.consecutive_losses = 0

    def record_closed_trade(self, pnl: float, at: datetime) -> None:
        self._roll_day_if_needed(at)
        self.realized_pnl_today += pnl
        self.day_trade_count_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def daily_loss_limit_hit(self, at: datetime = None) -> bool:
        at = at or datetime.now(timezone.utc)
        self._roll_day_if_needed(at)
        limit = -abs(self.starting_equity * self.daily_loss_limit_pct / 100)
        if self.realized_pnl_today <= limit:
            return True
        if self.max_consecutive_losses and self.consecutive_losses >= self.max_consecutive_losses:
            return True
        return False

    def can_open_new_position(self, current_open_positions: int, at: datetime = None) -> bool:
        at = at or datetime.now(timezone.utc)
        self._roll_day_if_needed(at)
        if self.daily_loss_limit_hit(at):
            return False
        return current_open_positions < self.max_open_positions

    def position_size(self, equity: float, entry_price: float, stop_loss_price: float) -> int:
        """Size the position so a hit stop only loses risk_per_trade_pct of equity,
        capped so the position's notional value can't exceed max_position_value_pct
        of equity — a backstop against a freak edge case (e.g. an unusually tiny
        stop distance, from a near-zero ATR reading) sizing an unreasonably large
        position that risk_per_trade_pct alone wouldn't catch."""
        risk_amount = equity * (self.risk_per_trade_pct / 100)
        per_share_risk = abs(entry_price - stop_loss_price)
        if per_share_risk <= 0 or entry_price <= 0:
            return 0
        qty = int(risk_amount / per_share_risk)
        if self.max_position_value_pct:
            max_notional = equity * (self.max_position_value_pct / 100)
            qty = min(qty, int(max_notional / entry_price))
        return max(qty, 0)
