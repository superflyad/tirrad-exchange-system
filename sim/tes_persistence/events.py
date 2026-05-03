from __future__ import annotations

import json
from pathlib import Path

from sim.tes_models.events import TesEngineEvent, parse_events
from sim.tes_serialization import serialize_events


def write_events_jsonl(path: Path, events: list[TesEngineEvent]) -> None:
    serialized_events = serialize_events(events)
    with path.open("w", encoding="utf-8") as handle:
        for serialized_event in serialized_events:
            handle.write(json.dumps(serialized_event, separators=(",", ":")))
            handle.write("\n")


def read_events_jsonl(path: Path) -> list[TesEngineEvent]:
    raw_events: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped == "":
                raise ValueError(f"malformed JSONL at line {line_number}: empty line")

            try:
                raw_event = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"malformed JSONL at line {line_number}: invalid JSON") from error

            if not isinstance(raw_event, dict):
                raise ValueError(f"malformed JSONL at line {line_number}: event must be a JSON object")

            raw_events.append(raw_event)

    return parse_events(raw_events)
