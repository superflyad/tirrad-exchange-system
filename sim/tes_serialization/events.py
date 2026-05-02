from __future__ import annotations

import json
from dataclasses import asdict

from sim.tes_models.events import TesEvent


def event_to_dict(event: TesEvent) -> dict[str, object]:
    return {
        "type": event.type,
        "data": asdict(event.data),
    }


def events_to_dicts(events: list[TesEvent]) -> list[dict[str, object]]:
    return [event_to_dict(event) for event in events]


def event_to_json_line(event: TesEvent) -> str:
    return json.dumps(event_to_dict(event), separators=(",", ":"), sort_keys=True)


def events_to_json_lines(events: list[TesEvent]) -> list[str]:
    return [event_to_json_line(event) for event in events]
