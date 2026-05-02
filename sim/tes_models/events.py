from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


@dataclass(frozen=True)
class OrderAcceptedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    price: int
    qty: int


@dataclass(frozen=True)
class OrderCanceledData:
    order_id: int


@dataclass(frozen=True)
class TradeExecutedData:
    price: int
    qty: int
    maker_order_id: int
    taker_order_id: int


@dataclass(frozen=True)
class TopOfBookData:
    best_bid: int | None
    best_ask: int | None


@dataclass(frozen=True)
class OrderAcceptedEvent:
    type: Literal["OrderAccepted"]
    data: OrderAcceptedData


@dataclass(frozen=True)
class OrderCanceledEvent:
    type: Literal["OrderCanceled"]
    data: OrderCanceledData


@dataclass(frozen=True)
class TradeExecutedEvent:
    type: Literal["TradeExecuted"]
    data: TradeExecutedData


@dataclass(frozen=True)
class TopOfBookEvent:
    type: Literal["TopOfBook"]
    data: TopOfBookData


TesEvent: TypeAlias = OrderAcceptedEvent | OrderCanceledEvent | TradeExecutedEvent | TopOfBookEvent


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a dict")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    keys = set(value.keys())
    if keys != expected:
        raise ValueError(f"{name} keys must be exactly {sorted(expected)}, got {sorted(keys)}")


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an int")
    return value


def _require_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, field_name)


def _require_side(value: Any) -> Literal["BUY", "SELL"]:
    if value not in {"BUY", "SELL"}:
        raise ValueError("side must be either 'BUY' or 'SELL'")
    return value


def parse_event(raw: dict[str, Any]) -> TesEvent:
    event = _require_dict(raw, "event")
    _require_exact_keys(event, {"type", "data"}, "event")

    event_type = event["type"]
    if not isinstance(event_type, str):
        raise ValueError("type must be a string")

    data = _require_dict(event["data"], "event.data")

    if event_type == "OrderAccepted":
        _require_exact_keys(data, {"order_id", "side", "price", "qty"}, "OrderAccepted.data")
        return OrderAcceptedEvent(
            type="OrderAccepted",
            data=OrderAcceptedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
            ),
        )

    if event_type == "OrderCanceled":
        _require_exact_keys(data, {"order_id"}, "OrderCanceled.data")
        return OrderCanceledEvent(
            type="OrderCanceled",
            data=OrderCanceledData(order_id=_require_int(data["order_id"], "order_id")),
        )

    if event_type == "TradeExecuted":
        _require_exact_keys(data, {"price", "qty", "maker_order_id", "taker_order_id"}, "TradeExecuted.data")
        return TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                maker_order_id=_require_int(data["maker_order_id"], "maker_order_id"),
                taker_order_id=_require_int(data["taker_order_id"], "taker_order_id"),
            ),
        )

    if event_type == "TopOfBook":
        _require_exact_keys(data, {"best_bid", "best_ask"}, "TopOfBook.data")
        return TopOfBookEvent(
            type="TopOfBook",
            data=TopOfBookData(
                best_bid=_require_optional_int(data["best_bid"], "best_bid"),
                best_ask=_require_optional_int(data["best_ask"], "best_ask"),
            ),
        )

    raise ValueError(f"unknown event type: {event_type}")


def parse_events(raw_events: list[dict[str, Any]]) -> list[TesEvent]:
    if not isinstance(raw_events, list):
        raise ValueError("raw_events must be a list")
    return [parse_event(raw) for raw in raw_events]
