from __future__ import annotations

from dataclasses import dataclass

import tes_engine
from sim.tes_engine_adapter import execute_command
from sim.tes_models.commands import *
from sim.tes_models.events import *


@dataclass(frozen=True)
class SimulationResult:
    events: list[TesEvent]
    total_commands: int
    total_events: int


def run_commands(engine: tes_engine.MatchingEngine, commands: list[TesCommand]) -> list[TesEvent]:
    events: list[TesEvent] = []
    for command in commands:
        events.extend(execute_command(engine, command))
    return events


def run_simulation(
    engine: tes_engine.MatchingEngine,
    commands: list[TesCommand],
) -> SimulationResult:
    events = run_commands(engine, commands)
    return SimulationResult(
        events=events,
        total_commands=len(commands),
        total_events=len(events),
    )
