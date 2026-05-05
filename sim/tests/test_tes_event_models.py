from __future__ import annotations

import pytest

from sim.tes_models.events import parse_event, parse_events


def test_parse_order_accepted() -> None:
    event = parse_event({"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100, "qty": 10}})
    assert event.type == "OrderAccepted"




def test_parse_order_rejected() -> None:
    event = parse_event(
        {"type": "OrderRejected", "data": {"side": "BUY", "price": -1, "qty": 10, "reason": "InvalidPrice"}}
    )
    assert event.type == "OrderRejected"


def test_parse_cancel_rejected() -> None:
    event = parse_event({"type": "CancelRejected", "data": {"order_id": 999, "reason": "UnknownOrderId"}})
    assert event.type == "CancelRejected"

def test_parse_order_canceled() -> None:
    event = parse_event({"type": "OrderCanceled", "data": {"order_id": 1}})
    assert event.type == "OrderCanceled"


def test_parse_trade_executed() -> None:
    event = parse_event(
        {"type": "TradeExecuted", "data": {"price": 100, "qty": 5, "maker_order_id": 10, "taker_order_id": 11}}
    )
    assert event.type == "TradeExecuted"


def test_parse_order_partially_filled() -> None:
    event = parse_event({"type": "OrderPartiallyFilled", "data": {"order_id": 11, "last_fill_qty": 3, "remaining_qty": 2}})
    assert event.type == "OrderPartiallyFilled"


def test_parse_order_filled() -> None:
    event = parse_event({"type": "OrderFilled", "data": {"order_id": 11, "last_fill_qty": 2}})
    assert event.type == "OrderFilled"


def test_parse_order_expired() -> None:
    event = parse_event({"type": "OrderExpired", "data": {"order_id": 11}})
    assert event.type == "OrderExpired"


def test_parse_top_of_book_with_prices() -> None:
    event = parse_event({"type": "TopOfBook", "data": {"best_bid": 99, "best_ask": 101}})
    assert event.data.best_bid == 99
    assert event.data.best_ask == 101


def test_parse_top_of_book_with_none_sides() -> None:
    event = parse_event({"type": "TopOfBook", "data": {"best_bid": None, "best_ask": None}})
    assert event.data.best_bid is None
    assert event.data.best_ask is None


def test_parse_events_multiple() -> None:
    events = parse_events([
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100, "qty": 10}},
        {"type": "OrderCanceled", "data": {"order_id": 1}},
    ])
    assert len(events) == 2


@pytest.mark.parametrize(
    "raw",
    [
        "not-a-dict",
        {"data": {}},
        {"type": "OrderAccepted"},
        {"type": "OrderAccepted", "data": {}, "extra": 1},
        {"type": "Unknown", "data": {}},
        {"type": "OrderAccepted", "data": "bad"},
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100}},
        {"type": "OrderCanceled", "data": {"order_id": 1, "extra": 2}},
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BID", "price": 100, "qty": 1}},
        {"type": "OrderAccepted", "data": {"order_id": "1", "side": "BUY", "price": 100, "qty": 1}},
        {"type": "OrderAccepted", "data": {"order_id": True, "side": "BUY", "price": 100, "qty": 1}},
        {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": None, "qty": 1}},
        {"type": "TopOfBook", "data": {"best_bid": "x", "best_ask": None}},
    ],
)
def test_parse_event_rejections(raw: object) -> None:
    with pytest.raises(ValueError):
        parse_event(raw)  # type: ignore[arg-type]


def test_parse_event_accepts_optional_symbol() -> None:
    event = parse_event(
        {"type": "TradeExecuted", "data": {"price": 100, "qty": 5, "maker_order_id": 10, "taker_order_id": 11, "symbol": "AAA"}}
    )

    assert event.type == "TradeExecuted"
    assert event.data.symbol == "AAA"
