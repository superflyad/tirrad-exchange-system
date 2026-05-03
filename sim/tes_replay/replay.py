from __future__ import annotations

from dataclasses import dataclass

from sim.tes_models.events import TesEngineEvent


@dataclass(frozen=True)
class ReplayResult:
    events: list[TesEngineEvent]
    total_events: int
    total_trades: int


def replay_events(events: list[TesEngineEvent]) -> ReplayResult:
    replayed_events = list(events)
    total_trades = sum(1 for event in replayed_events if event.type == "TradeExecuted")
    return ReplayResult(events=replayed_events, total_events=len(replayed_events), total_trades=total_trades)
