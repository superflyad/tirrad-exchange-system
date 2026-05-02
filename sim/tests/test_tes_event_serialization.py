import json

from sim.tes_models.events import (
    OrderAcceptedData,
    OrderAcceptedEvent,
    OrderCanceledData,
    OrderCanceledEvent,
    TesEvent,
    TopOfBookData,
    TopOfBookEvent,
    TradeExecutedData,
    TradeExecutedEvent,
)
from sim.tes_serialization import event_to_dict, event_to_json_line, events_to_dicts, events_to_json_lines


def _sample_events() -> list[TesEvent]:
    return [
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=10)),
        OrderCanceledEvent(type="OrderCanceled", data=OrderCanceledData(order_id=1)),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=1, taker_order_id=2),
        ),
        TopOfBookEvent(type="TopOfBook", data=TopOfBookData(best_bid=99, best_ask=101)),
    ]


def test_event_to_dict_serializes_each_known_event_type() -> None:
    serialized = [event_to_dict(event) for event in _sample_events()]

    assert serialized == [
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100, "qty": 10}},
        {"type": "OrderCanceled", "data": {"order_id": 1}},
        {"type": "TradeExecuted", "data": {"price": 100, "qty": 5, "maker_order_id": 1, "taker_order_id": 2}},
        {"type": "TopOfBook", "data": {"best_bid": 99, "best_ask": 101}},
    ]



def test_event_to_json_line_roundtrip_and_top_level_shape() -> None:
    for event in _sample_events():
        line = event_to_json_line(event)
        parsed = json.loads(line)

        assert set(parsed.keys()) == {"type", "data"}
        assert parsed == event_to_dict(event)



def test_batch_serialization_helpers() -> None:
    events = _sample_events()

    assert events_to_dicts(events) == [event_to_dict(event) for event in events]

    lines = events_to_json_lines(events)
    assert lines == [event_to_json_line(event) for event in events]
    assert [json.loads(line) for line in lines] == events_to_dicts(events)



def test_serialization_contains_no_class_or_module_leakage() -> None:
    for event in _sample_events():
        serialized_dict = event_to_dict(event)
        serialized_line = event_to_json_line(event)

        assert "__" not in serialized_line
        assert "sim.tes_models" not in serialized_line
        assert event.__class__.__name__ not in serialized_line
        assert event.data.__class__.__name__ not in serialized_line

        assert set(serialized_dict.keys()) == {"type", "data"}
        assert "__dict__" not in serialized_dict
