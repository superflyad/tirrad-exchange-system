from __future__ import annotations

from dataclasses import asdict

from sim.tes_models.events import TesEngineEvent


def _event_to_dict(event: TesEngineEvent) -> dict[str, object]:
    return {
        "type": event.type,
        "data": asdict(event.data),
    }


def _events_to_dicts(events: list[TesEngineEvent]) -> list[dict[str, object]]:
    return [_event_to_dict(event) for event in events]


def serialize_event(event: TesEngineEvent) -> dict[str, object]:
    return _event_to_dict(event)


def serialize_events(events: list[TesEngineEvent]) -> list[dict[str, object]]:
    return _events_to_dicts(events)
