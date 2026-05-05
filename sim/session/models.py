from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MarketSessionConfig:
    scenario: str
    steps: int
    symbols: tuple[str, ...]
    seed: int
    initial_price: int
    volatility: float
    spread_width: int
    min_order_size: int
    max_order_size: int
    probability_market_order: float
    probability_cancel_replace: float
    participant_count: int
    depth_levels: int


@dataclass(frozen=True)
class MarketSessionReport:
    total_steps: int
    total_orders: int
    total_trades: int
    total_volume: int
    traded_notional: int
    final_mid_price: dict[str, float]
    price_change_pct: dict[str, float]
    average_spread: dict[str, float]
    max_spread: dict[str, int]
    average_book_imbalance: dict[str, float]
    per_symbol_volume: dict[str, int]
    rejected_orders: int
    per_participant_pnl: dict[str, int]
    final_equity: float
    per_symbol_pnl: dict[str, float]
    realized_pnl: float
    unrealized_pnl: float
    total_fees: int


@dataclass(frozen=True)
class MarketSessionResult:
    config: MarketSessionConfig
    step_summaries: list[dict[str, object]]
    trades: list[dict[str, object]]
    snapshots: list[dict[str, object]]
    report: MarketSessionReport
    per_symbol_analytics: dict[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "config": asdict(self.config),
            "steps": self.step_summaries,
            "trades": self.trades,
            "snapshots": self.snapshots,
            "report": asdict(self.report),
            "per_symbol_analytics": self.per_symbol_analytics,
        }
