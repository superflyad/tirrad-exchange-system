from __future__ import annotations

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEvent
from sim.tes_strategy.strategy import Strategy

from sim.strategies.new_order_support import detect_new_order_api_support, missing_reason


class IocPartialFillStrategy(Strategy):
    def on_start(self) -> list[TesCommand]:
        support = detect_new_order_api_support()
        if not support.ioc:
            raise NotImplementedError(missing_reason())

        from sim.tes_models import commands as command_models

        ioc_command = command_models.ImmediateOrCancelOrderCommand(
            side="BUY", price=101, qty=5
        )
        return [
            LimitOrderCommand(side="SELL", price=101, qty=2),
            ioc_command,
        ]

    def on_event(self, event: TesEvent) -> list[TesCommand]:
        _ = event
        return []
