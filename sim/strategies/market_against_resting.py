from __future__ import annotations

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEvent
from sim.tes_strategy.strategy import Strategy

from sim.strategies.new_order_support import detect_new_order_api_support, missing_reason


class MarketOrderAgainstRestingLiquidityStrategy(Strategy):
    def on_start(self) -> list[TesCommand]:
        support = detect_new_order_api_support()
        if not support.market_order:
            raise NotImplementedError(missing_reason())

        from sim.tes_models import commands as command_models

        market_order_command = command_models.MarketOrderCommand(side="BUY", qty=3)
        return [
            LimitOrderCommand(side="SELL", price=101, qty=5),
            market_order_command,
        ]

    def on_event(self, event: TesEvent) -> list[TesCommand]:
        _ = event
        return []
