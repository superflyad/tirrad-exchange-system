from __future__ import annotations

from dataclasses import dataclass

from sim.tes_models.events import TesEvent


@dataclass(frozen=True)
class SimulationSummary:
    total_commands: int
    total_events: int
    total_trades: int
    total_order_accepted: int
    total_order_canceled: int


@dataclass(frozen=True)
class SimulationRunRecord:
    run_id: str
    summary: SimulationSummary
    events: list[TesEvent]


def build_simulation_summary(events: list[TesEvent], total_commands: int) -> SimulationSummary:
    if total_commands < 0:
        raise ValueError("total_commands must be >= 0")

    total_trades = sum(1 for event in events if event.type == "TradeExecuted")
    total_order_accepted = sum(1 for event in events if event.type == "OrderAccepted")
    total_order_canceled = sum(1 for event in events if event.type == "OrderCanceled")

    return SimulationSummary(
        total_commands=total_commands,
        total_events=len(events),
        total_trades=total_trades,
        total_order_accepted=total_order_accepted,
        total_order_canceled=total_order_canceled,
    )


def build_run_record(run_id: str, events: list[TesEvent], total_commands: int) -> SimulationRunRecord:
    if run_id == "":
        raise ValueError("run_id must be a non-empty string")

    return SimulationRunRecord(
        run_id=run_id,
        summary=build_simulation_summary(events=events, total_commands=total_commands),
        events=events,
    )
