from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sim.tes_models.events import TesEngineEvent
from sim.tes_simulation.runner import run_commands
from sim.tes_strategy.strategy import Strategy


@dataclass(frozen=True)
class StrategySimulationResult:
    events: list[TesEngineEvent]
    total_commands: int
    total_events: int
    total_steps: int


def run_strategy_simulation(
    engine: Any,
    strategy: Strategy,
    max_steps: int = 100,
) -> StrategySimulationResult:
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")

    all_events: list[TesEngineEvent] = []
    total_commands = 0
    total_steps = 0

    pending_commands = strategy.on_start()

    while pending_commands and total_steps < max_steps:
        total_steps += 1
        total_commands += len(pending_commands)

        step_events = run_commands(engine, pending_commands)
        all_events.extend(step_events)

        next_commands = []
        for event in step_events:
            next_commands.extend(strategy.on_event(event))
        pending_commands = next_commands

    return StrategySimulationResult(
        events=all_events,
        total_commands=total_commands,
        total_events=len(all_events),
        total_steps=total_steps,
    )
