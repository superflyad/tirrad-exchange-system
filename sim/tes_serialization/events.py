from __future__ import annotations

from dataclasses import asdict

from sim.tes_models.events import DEFAULT_SYMBOL, TesEngineEvent


def _event_to_dict(event: TesEngineEvent) -> dict[str, object]:
    data = asdict(event.data)
    if data.get("symbol") == DEFAULT_SYMBOL:
        data.pop("symbol")
    return {
        "type": event.type,
        "data": data,
    }


def _events_to_dicts(events: list[TesEngineEvent]) -> list[dict[str, object]]:
    return [_event_to_dict(event) for event in events]


def serialize_event(event: TesEngineEvent) -> dict[str, object]:
    return _event_to_dict(event)


def serialize_events(events: list[TesEngineEvent]) -> list[dict[str, object]]:
    return _events_to_dicts(events)
