from __future__ import annotations

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEvent
from sim.tes_strategy.strategy import Strategy


class CrossingTakerStrategy(Strategy):
    """Example strategy that intentionally crosses the spread to produce a trade."""

    def on_start(self) -> list[TesCommand]:
        return [
            LimitOrderCommand(side="BUY", price=100, qty=10),
            LimitOrderCommand(side="SELL", price=100, qty=5),
        ]

    def on_event(self, event: TesEvent) -> list[TesCommand]:
        _ = event
        return []
