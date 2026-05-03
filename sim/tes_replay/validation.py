from __future__ import annotations

from sim.tes_models.events import (
    CancelRejected,
    OrderAccepted,
    OrderCanceled,
    OrderRejected,
    TesEngineEvent,
    TopOfBook,
    TradeExecuted,
)


def validate_replay_events(events: list[TesEngineEvent]) -> list[TesEngineEvent]:
    if not isinstance(events, list):
        raise ValueError("events must be a list")

    for event in events:
        if isinstance(event, dict):
            raise ValueError("events must contain TesEngineEvent objects")

        if not isinstance(
            event,
            (
                OrderAccepted,
                OrderRejected,
                OrderCanceled,
                CancelRejected,
                TradeExecuted,
                TopOfBook,
            ),
        ):
            raise ValueError("events must contain TesEngineEvent objects")

    return events
