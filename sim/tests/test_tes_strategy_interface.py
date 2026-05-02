from __future__ import annotations

from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand
from sim.tes_models.events import TopOfBookData, TopOfBookEvent
from sim.tes_strategy.strategy import SimpleMarketMaker, Strategy


class StubStrategy(Strategy):
    def on_start(self) -> list[LimitOrderCommand | CancelOrderCommand]:
        return [LimitOrderCommand(side="BUY", price=100, qty=2), CancelOrderCommand(order_id=7)]

    def on_event(self, event: TopOfBookEvent) -> list[LimitOrderCommand | CancelOrderCommand]:
        _ = event
        return []


def test_strategy_on_start_returns_commands() -> None:
    strategy = StubStrategy()
    commands = strategy.on_start()

    assert isinstance(commands, list)
    assert len(commands) == 2


def test_strategy_commands_are_valid_types() -> None:
    strategy = StubStrategy()
    commands = strategy.on_start()

    assert all(isinstance(command, (LimitOrderCommand, CancelOrderCommand)) for command in commands)


def test_strategy_on_event_returns_list() -> None:
    strategy = StubStrategy()
    event = TopOfBookEvent(type="TopOfBook", data=TopOfBookData(best_bid=100, best_ask=102))

    commands = strategy.on_event(event)
    assert isinstance(commands, list)
    assert commands == []


def test_simple_market_maker_generates_commands() -> None:
    strategy = SimpleMarketMaker(bid_price=98, ask_price=103, order_qty=5)

    commands = strategy.on_start()

    assert commands == [
        LimitOrderCommand(side="BUY", price=98, qty=5),
        LimitOrderCommand(side="SELL", price=103, qty=5),
    ]
