from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tes_engine
from sim.tes_models.commands import LimitOrderCommand
from sim.tes_models.events import TesEngineEvent, parse_events
from sim.tes_serialization import serialize_events
from sim.tes_simulation.runner import run_simulation


def _save_run_fallback(path: Path, events: list[TesEngineEvent]) -> None:
    payload = {"events": serialize_events(events)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_run_fallback(path: Path) -> list[TesEngineEvent]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("saved payload must be a dict")
    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("saved payload events must be a list")
    return parse_events(raw_events)


def _resolve_save_load() -> tuple[Any, Any]:
    try:
        from sim.tes_run import load_run, save_run  # type: ignore[attr-defined]

        return save_run, load_run
    except (ImportError, AttributeError):
        return _save_run_fallback, _load_run_fallback


def main() -> None:
    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]

    result = run_simulation(engine, commands)

    save_run, load_run = _resolve_save_load()
    output_path = Path("out") / "saved_run.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_run(output_path, result.events)
    reloaded_events = load_run(output_path)

    print(f"Saved {len(result.events)} events to {output_path}")
    print(f"Reloaded {len(reloaded_events)} events")


if __name__ == "__main__":
    main()
