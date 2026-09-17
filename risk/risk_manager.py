"""Guardrails around the strategy: how much to risk, and when to stop trading.

Nothing here decides *what* to trade — that's the strategy's job. This only
decides *how much* and *whether it's still allowed to trade today*.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskManager:
    starting_equity: float
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    max_open_positions: int

    trading_day: date = field(default_factory=date.today)
    realized_pnl_today: float = 0.0
    day_trade_count_today: int = 0

    def _roll_day_if_needed(self) -> None:
        today = date.today()
        if today != self.trading_day:
            self.trading_day = today
            self.realized_pnl_today = 0.0
            self.day_trade_count_today = 0

    def record_closed_trade(self, pnl: float) -> None:
        self._roll_day_if_needed()
        self.realized_pnl_today += pnl
        self.day_trade_count_today += 1

    def daily_loss_limit_hit(self) -> bool:
        self._roll_day_if_needed()
        limit = -abs(self.starting_equity * self.daily_loss_limit_pct / 100)
        return self.realized_pnl_today <= limit

    def can_open_new_position(self, current_open_positions: int) -> bool:
        self._roll_day_if_needed()
        if self.daily_loss_limit_hit():
            return False
        return current_open_positions < self.max_open_positions

    def position_size(self, equity: float, entry_price: float, stop_loss_price: float) -> int:
        """Size the position so a hit stop only loses risk_per_trade_pct of equity."""
        risk_amount = equity * (self.risk_per_trade_pct / 100)
        per_share_risk = abs(entry_price - stop_loss_price)
        if per_share_risk <= 0:
            return 0
        qty = int(risk_amount / per_share_risk)
        return max(qty, 0)
