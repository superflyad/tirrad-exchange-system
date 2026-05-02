from __future__ import annotations

import pytest

from sim.tes_models.events import OrderAcceptedData, OrderAcceptedEvent
from sim.tes_replay.validation import validate_replay_events


def test_validate_replay_events_rejects_non_list() -> None:
    with pytest.raises(ValueError, match="events must be a list"):
        validate_replay_events("not-a-list")  # type: ignore[arg-type]


def test_validate_replay_events_rejects_raw_dict_event() -> None:
    with pytest.raises(ValueError, match="events must contain TesEvent objects"):
        validate_replay_events([{"type": "OrderAccepted", "data": {}}])  # type: ignore[list-item]


def test_validate_replay_events_rejects_unknown_object() -> None:
    with pytest.raises(ValueError, match="events must contain TesEvent objects"):
        validate_replay_events([object()])  # type: ignore[list-item]


def test_validate_replay_events_returns_original_list() -> None:
    event = OrderAcceptedEvent(
        type="OrderAccepted",
        data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=5),
    )
    events = [event]

    validated = validate_replay_events(events)

    assert validated is events
