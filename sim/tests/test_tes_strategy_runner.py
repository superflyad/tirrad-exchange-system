from __future__ import annotations

import pytest

from sim.tes_models.commands import LimitOrderCommand
from sim.tes_simulation.strategy_runner import run_strategy_simulation
from sim.tes_strategy.strategy import Strategy


class StartOnlyStrategy(Strategy):
    def on_start(self) -> list[LimitOrderCommand]:
        return [LimitOrderCommand(side="BUY", price=100, qty=2)]

    def on_event(self, event: object) -> list[LimitOrderCommand]:
        _ = event
        return []


class EventRecordingStrategy(Strategy):
    def __init__(self) -> None:
        self.seen_event_types: list[str] = []

    def on_start(self) -> list[LimitOrderCommand]:
        return [LimitOrderCommand(side="BUY", price=101, qty=1)]

    def on_event(self, event: object) -> list[LimitOrderCommand]:
        self.seen_event_types.append(event.type)
        return []


class FollowupCommandStrategy(Strategy):
    def __init__(self) -> None:
        self.issued_followup = False

    def on_start(self) -> list[LimitOrderCommand]:
        return [LimitOrderCommand(side="BUY", price=100, qty=1)]

    def on_event(self, event: object) -> list[LimitOrderCommand]:
        if event.type == "OrderAccepted" and not self.issued_followup:
            self.issued_followup = True
            return [LimitOrderCommand(side="SELL", price=102, qty=1)]
        return []


class RunawayStrategy(Strategy):
    def on_start(self) -> list[LimitOrderCommand]:
        return [LimitOrderCommand(side="BUY", price=100, qty=1)]

    def on_event(self, event: object) -> list[LimitOrderCommand]:
        if event.type == "OrderAccepted":
            return [LimitOrderCommand(side="BUY", price=100, qty=1)]
        return []


def test_on_start_commands_execute() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    result = run_strategy_simulation(engine, StartOnlyStrategy())

    assert result.total_commands == 1
    assert any(event.type == "OrderAccepted" for event in result.events)


def test_strategy_receives_events_via_on_event() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    strategy = EventRecordingStrategy()

    result = run_strategy_simulation(engine, strategy)

    assert result.total_events > 0
    assert "OrderAccepted" in strategy.seen_event_types


def test_commands_returned_from_on_event_execute() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()

    result = run_strategy_simulation(engine, FollowupCommandStrategy())

    assert result.total_commands == 2
    assert result.total_steps == 2


def test_max_steps_stops_runaway_strategy() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()

    result = run_strategy_simulation(engine, RunawayStrategy(), max_steps=3)

    assert result.total_steps == 3
    assert result.total_commands == 3


def test_result_counts_and_max_steps_validation() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    result = run_strategy_simulation(engine, StartOnlyStrategy())

    assert result.total_events == len(result.events)
    assert result.total_steps == 1

    with pytest.raises(ValueError):
        run_strategy_simulation(engine, StartOnlyStrategy(), max_steps=0)
