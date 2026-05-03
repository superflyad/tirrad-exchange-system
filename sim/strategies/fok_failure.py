from __future__ import annotations

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEvent
from sim.tes_strategy.strategy import Strategy

from sim.strategies.new_order_support import detect_new_order_api_support, missing_reason


class FokFailureStrategy(Strategy):
    def on_start(self) -> list[TesCommand]:
        support = detect_new_order_api_support()
        if not support.fok:
            raise NotImplementedError(missing_reason())

        from sim.tes_models import commands as command_models

        fok_command = command_models.FillOrKillOrderCommand(side="BUY", price=101, qty=5)
        return [
            LimitOrderCommand(side="SELL", price=101, qty=2),
            fok_command,
        ]

    def on_event(self, event: TesEvent) -> list[TesCommand]:
        _ = event
        return []
