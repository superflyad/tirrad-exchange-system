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
from sim.tes_serialization import serialize_event, serialize_events


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


def test_serialize_event_serializes_each_known_event_type() -> None:
    serialized = [serialize_event(event) for event in _sample_events()]

    assert serialized == [
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100, "qty": 10}},
        {"type": "OrderCanceled", "data": {"order_id": 1}},
        {"type": "TradeExecuted", "data": {"price": 100, "qty": 5, "maker_order_id": 1, "taker_order_id": 2}},
        {"type": "TopOfBook", "data": {"best_bid": 99, "best_ask": 101}},
    ]


def test_serialize_events_batch_serialization() -> None:
    events = _sample_events()
    assert serialize_events(events) == [serialize_event(event) for event in events]


def test_serialization_contains_no_class_or_module_leakage() -> None:
    for event in _sample_events():
        serialized_dict = serialize_event(event)
        serialized_as_text = str(serialized_dict)

        assert "sim.tes_models" not in serialized_as_text
        assert event.__class__.__name__ not in serialized_as_text
        assert event.data.__class__.__name__ not in serialized_as_text
        assert set(serialized_dict.keys()) == {"type", "data"}


def test_public_api_only_exports_expected_names() -> None:
    import sim.tes_serialization as mod

    assert hasattr(mod, "serialize_event")
    assert hasattr(mod, "serialize_events")


def test_serialized_event_shape_is_exact() -> None:
    event = OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=10))
    result = serialize_event(event)

    assert set(result.keys()) == {"type", "data"}
