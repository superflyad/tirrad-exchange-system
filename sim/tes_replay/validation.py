from __future__ import annotations

from sim.tes_models.events import OrderAcceptedEvent, OrderCanceledEvent, TesEvent, TopOfBookEvent, TradeExecutedEvent


def validate_replay_events(events: list[TesEvent]) -> list[TesEvent]:
    if not isinstance(events, list):
        raise ValueError("events must be a list")

    for event in events:
        if isinstance(event, dict):
            raise ValueError("events must contain TesEvent objects")

        if not isinstance(event, (OrderAcceptedEvent, OrderCanceledEvent, TradeExecutedEvent, TopOfBookEvent)):
            raise ValueError("events must contain TesEvent objects")

    return events
