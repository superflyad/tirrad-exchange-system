from __future__ import annotations

from dataclasses import dataclass

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEngineEvent


@dataclass(frozen=True)
class StrategyContext:
    """Placeholder context for strategy state and shared simulation metadata."""

    pass


class Strategy:
    """Base interface for TES simulation strategies."""

    def on_start(self) -> list[TesCommand]:
        raise NotImplementedError

    def on_market_data(self, snapshots: dict[str, dict[str, int | str | list[dict[str, int | str]]]]) -> list[TesCommand]:
        _ = snapshots
        return []

    def on_event(self, event: TesEngineEvent) -> list[TesCommand]:
        raise NotImplementedError

    def on_finish(self) -> None:
        return None


class SimpleMarketMaker(Strategy):
    """Simple example strategy that posts one buy and one sell limit order at startup."""

    def __init__(self, bid_price: int = 99, ask_price: int = 101, order_qty: int = 1) -> None:
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.order_qty = order_qty

    def on_start(self) -> list[TesCommand]:
        return [
            LimitOrderCommand(side="BUY", price=self.bid_price, qty=self.order_qty),
            LimitOrderCommand(side="SELL", price=self.ask_price, qty=self.order_qty),
        ]

    def on_event(self, event: TesEngineEvent) -> list[TesCommand]:
        _ = event
        return []
