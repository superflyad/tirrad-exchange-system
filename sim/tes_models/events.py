from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

DEFAULT_SYMBOL = "DEFAULT"
TradingPhaseLiteral: TypeAlias = Literal["Continuous", "OpeningAuction", "ClosingAuction", "Halted"]
RejectReasonLiteral: TypeAlias = Literal[
    "InvalidPrice",
    "InvalidQuantity",
    "UnknownOrderId",
    "NoLiquidity",
    "InsufficientCash",
    "InsufficientPosition",
    "WrongAccount",
    "InsufficientBuyingPower",
    "ShortSellingDisabled",
    "MarginRequirementFailed",
    "MaintenanceMarginBreached",
    "SymbolHalted",
    "PriceBandViolation",
    "CircuitBreakerViolation",
    "AuctionPriceOutOfBand",
]


@dataclass(frozen=True)
class OrderAcceptedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    price: int
    qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class HiddenOrderAcceptedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    price: int
    total_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class IcebergOrderAcceptedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    price: int
    total_qty: int
    display_qty: int
    reserve_qty: int
    hidden_remaining: int
    current_visible_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class IcebergReplenishedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    price: int
    replenished_qty: int
    reserve_qty: int
    hidden_remaining: int
    total_remaining_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class OrderCanceledData:
    order_id: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class OrderRejectedData:
    side: Literal["BUY", "SELL"]
    price: int
    qty: int
    reason: RejectReasonLiteral
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class CancelRejectedData:
    order_id: int
    reason: RejectReasonLiteral
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class TradeExecutedData:
    price: int
    qty: int
    maker_order_id: int
    taker_order_id: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class OrderPartiallyFilledData:
    order_id: int
    last_fill_qty: int
    remaining_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class OrderFilledData:
    order_id: int
    last_fill_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class OrderExpiredData:
    order_id: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class StopOrderAcceptedData:
    order_id: int
    side: Literal["BUY", "SELL"]
    stop_price: int
    qty: int
    limit_price: int | None
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class StopOrderTriggeredData:
    order_id: int
    resulting_order_id: int
    side: Literal["BUY", "SELL"]
    stop_price: int
    qty: int
    limit_price: int | None
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class TopOfBookData:
    best_bid: int | None
    best_ask: int | None
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class AuctionPhaseData:
    symbol: str
    phase: TradingPhaseLiteral


@dataclass(frozen=True)
class AuctionUncrossData:
    symbol: str
    price: int
    qty: int
    imbalance: int


@dataclass(frozen=True)
class SymbolHaltedData:
    symbol: str
    reason: str


@dataclass(frozen=True)
class SymbolResumedData:
    symbol: str


@dataclass(frozen=True)
class PriceBandUpdatedData:
    symbol: str
    lower_price: int | None
    upper_price: int | None


@dataclass(frozen=True)
class CircuitBreakerTriggeredData:
    symbol: str
    price: int
    reason: str


@dataclass(frozen=True)
class IndicativePriceUpdatedData:
    symbol: str
    price: int | None
    qty: int
    imbalance: int


@dataclass(frozen=True)
class OrderAccepted:
    type: Literal["OrderAccepted"]
    data: OrderAcceptedData


@dataclass(frozen=True)
class HiddenOrderAccepted:
    type: Literal["HiddenOrderAccepted"]
    data: HiddenOrderAcceptedData


@dataclass(frozen=True)
class IcebergOrderAccepted:
    type: Literal["IcebergOrderAccepted"]
    data: IcebergOrderAcceptedData


@dataclass(frozen=True)
class IcebergReplenished:
    type: Literal["IcebergReplenished"]
    data: IcebergReplenishedData


@dataclass(frozen=True)
class OrderCanceled:
    type: Literal["OrderCanceled"]
    data: OrderCanceledData


@dataclass(frozen=True)
class OrderRejected:
    type: Literal["OrderRejected"]
    data: OrderRejectedData


@dataclass(frozen=True)
class CancelRejected:
    type: Literal["CancelRejected"]
    data: CancelRejectedData


@dataclass(frozen=True)
class TradeExecuted:
    type: Literal["TradeExecuted"]
    data: TradeExecutedData


@dataclass(frozen=True)
class OrderPartiallyFilled:
    type: Literal["OrderPartiallyFilled"]
    data: OrderPartiallyFilledData


@dataclass(frozen=True)
class OrderFilled:
    type: Literal["OrderFilled"]
    data: OrderFilledData


@dataclass(frozen=True)
class OrderExpired:
    type: Literal["OrderExpired"]
    data: OrderExpiredData


@dataclass(frozen=True)
class StopOrderAccepted:
    type: Literal["StopOrderAccepted"]
    data: StopOrderAcceptedData


@dataclass(frozen=True)
class StopOrderTriggered:
    type: Literal["StopOrderTriggered"]
    data: StopOrderTriggeredData


@dataclass(frozen=True)
class TopOfBook:
    type: Literal["TopOfBook"]
    data: TopOfBookData


@dataclass(frozen=True)
class AuctionStarted:
    type: Literal["AuctionStarted"]
    data: AuctionPhaseData


@dataclass(frozen=True)
class AuctionEnded:
    type: Literal["AuctionEnded"]
    data: AuctionPhaseData


@dataclass(frozen=True)
class AuctionUncross:
    type: Literal["AuctionUncross"]
    data: AuctionUncrossData


@dataclass(frozen=True)
class SymbolHalted:
    type: Literal["SymbolHalted"]
    data: SymbolHaltedData


@dataclass(frozen=True)
class SymbolResumed:
    type: Literal["SymbolResumed"]
    data: SymbolResumedData


@dataclass(frozen=True)
class PriceBandUpdated:
    type: Literal["PriceBandUpdated"]
    data: PriceBandUpdatedData


@dataclass(frozen=True)
class CircuitBreakerTriggered:
    type: Literal["CircuitBreakerTriggered"]
    data: CircuitBreakerTriggeredData


@dataclass(frozen=True)
class IndicativePriceUpdated:
    type: Literal["IndicativePriceUpdated"]
    data: IndicativePriceUpdatedData


TesEngineEvent: TypeAlias = (
    OrderAccepted
    | HiddenOrderAccepted
    | IcebergOrderAccepted
    | IcebergReplenished
    | OrderRejected
    | OrderCanceled
    | CancelRejected
    | TradeExecuted
    | OrderPartiallyFilled
    | OrderFilled
    | OrderExpired
    | StopOrderAccepted
    | StopOrderTriggered
    | TopOfBook
    | AuctionStarted
    | AuctionEnded
    | AuctionUncross
    | SymbolHalted
    | SymbolResumed
    | PriceBandUpdated
    | CircuitBreakerTriggered
    | IndicativePriceUpdated
)

# Backward-compatible alias for historical naming.
TesEvent: TypeAlias = TesEngineEvent


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a dict")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    keys = set(value.keys())
    if keys != expected:
        raise ValueError(f"{name} keys must be exactly {sorted(expected)}, got {sorted(keys)}")


def _require_event_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    keys = set(value.keys())
    with_symbol = expected | {"symbol"}
    if keys != expected and keys != with_symbol:
        raise ValueError(f"{name} keys must be exactly {sorted(expected)} or {sorted(with_symbol)}, got {sorted(keys)}")


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an int")
    return value


def _require_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, field_name)


def _require_symbol(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("symbol must be a string")
    return value


def _optional_symbol(data: dict[str, Any]) -> str:
    return _require_symbol(data.get("symbol", DEFAULT_SYMBOL))


def _require_side(value: Any) -> Literal["BUY", "SELL"]:
    if value not in {"BUY", "SELL"}:
        raise ValueError("side must be either 'BUY' or 'SELL'")
    return value


def _require_trading_phase(value: Any) -> TradingPhaseLiteral:
    if value not in {"Continuous", "OpeningAuction", "ClosingAuction", "Halted"}:
        raise ValueError("phase must be one of: Continuous, OpeningAuction, ClosingAuction, Halted")
    return value


def _require_reject_reason(value: Any) -> RejectReasonLiteral:
    allowed = {
        "InvalidPrice",
        "InvalidQuantity",
        "UnknownOrderId",
        "NoLiquidity",
        "InsufficientCash",
        "InsufficientPosition",
        "WrongAccount",
        "InsufficientBuyingPower",
        "ShortSellingDisabled",
        "MarginRequirementFailed",
        "MaintenanceMarginBreached",
        "SymbolHalted",
        "PriceBandViolation",
        "CircuitBreakerViolation",
        "AuctionPriceOutOfBand",
    }
    if value not in allowed:
        raise ValueError(f"reason must be one of {', '.join(sorted(allowed))}")
    return value


def parse_event(raw: dict[str, Any]) -> TesEngineEvent:
    event = _require_dict(raw, "event")
    _require_exact_keys(event, {"type", "data"}, "event")

    event_type = event["type"]
    if not isinstance(event_type, str):
        raise ValueError("type must be a string")

    data = _require_dict(event["data"], "event.data")

    if event_type == "OrderAccepted":
        _require_event_keys(data, {"order_id", "side", "price", "qty"}, "OrderAccepted.data")
        return OrderAccepted(
            type="OrderAccepted",
            data=OrderAcceptedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "HiddenOrderAccepted":
        _require_event_keys(data, {"order_id", "side", "price", "total_qty"}, "HiddenOrderAccepted.data")
        return HiddenOrderAccepted(
            type="HiddenOrderAccepted",
            data=HiddenOrderAcceptedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                total_qty=_require_int(data["total_qty"], "total_qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "IcebergOrderAccepted":
        _require_event_keys(
            data,
            {"order_id", "side", "price", "total_qty", "display_qty", "reserve_qty", "hidden_remaining", "current_visible_qty"},
            "IcebergOrderAccepted.data",
        )
        return IcebergOrderAccepted(
            type="IcebergOrderAccepted",
            data=IcebergOrderAcceptedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                total_qty=_require_int(data["total_qty"], "total_qty"),
                display_qty=_require_int(data["display_qty"], "display_qty"),
                reserve_qty=_require_int(data["reserve_qty"], "reserve_qty"),
                hidden_remaining=_require_int(data["hidden_remaining"], "hidden_remaining"),
                current_visible_qty=_require_int(data["current_visible_qty"], "current_visible_qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "IcebergReplenished":
        _require_event_keys(
            data,
            {"order_id", "side", "price", "replenished_qty", "reserve_qty", "hidden_remaining", "total_remaining_qty"},
            "IcebergReplenished.data",
        )
        return IcebergReplenished(
            type="IcebergReplenished",
            data=IcebergReplenishedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                replenished_qty=_require_int(data["replenished_qty"], "replenished_qty"),
                reserve_qty=_require_int(data["reserve_qty"], "reserve_qty"),
                hidden_remaining=_require_int(data["hidden_remaining"], "hidden_remaining"),
                total_remaining_qty=_require_int(data["total_remaining_qty"], "total_remaining_qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "OrderRejected":
        _require_event_keys(data, {"side", "price", "qty", "reason"}, "OrderRejected.data")
        return OrderRejected(
            type="OrderRejected",
            data=OrderRejectedData(
                side=_require_side(data["side"]),
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                reason=_require_reject_reason(data["reason"]),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "OrderCanceled":
        _require_event_keys(data, {"order_id"}, "OrderCanceled.data")
        return OrderCanceled(
            type="OrderCanceled",
            data=OrderCanceledData(order_id=_require_int(data["order_id"], "order_id"), symbol=_optional_symbol(data)),
        )

    if event_type == "CancelRejected":
        _require_event_keys(data, {"order_id", "reason"}, "CancelRejected.data")
        return CancelRejected(
            type="CancelRejected",
            data=CancelRejectedData(
                order_id=_require_int(data["order_id"], "order_id"),
                reason=_require_reject_reason(data["reason"]),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "TradeExecuted":
        _require_event_keys(data, {"price", "qty", "maker_order_id", "taker_order_id"}, "TradeExecuted.data")
        return TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                maker_order_id=_require_int(data["maker_order_id"], "maker_order_id"),
                taker_order_id=_require_int(data["taker_order_id"], "taker_order_id"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "StopOrderAccepted":
        _require_event_keys(data, {"order_id", "side", "stop_price", "qty", "limit_price"}, "StopOrderAccepted.data")
        return StopOrderAccepted(
            type="StopOrderAccepted",
            data=StopOrderAcceptedData(
                order_id=_require_int(data["order_id"], "order_id"),
                side=_require_side(data["side"]),
                stop_price=_require_int(data["stop_price"], "stop_price"),
                qty=_require_int(data["qty"], "qty"),
                limit_price=_require_optional_int(data["limit_price"], "limit_price"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "StopOrderTriggered":
        _require_event_keys(
            data,
            {"order_id", "resulting_order_id", "side", "stop_price", "qty", "limit_price"},
            "StopOrderTriggered.data",
        )
        return StopOrderTriggered(
            type="StopOrderTriggered",
            data=StopOrderTriggeredData(
                order_id=_require_int(data["order_id"], "order_id"),
                resulting_order_id=_require_int(data["resulting_order_id"], "resulting_order_id"),
                side=_require_side(data["side"]),
                stop_price=_require_int(data["stop_price"], "stop_price"),
                qty=_require_int(data["qty"], "qty"),
                limit_price=_require_optional_int(data["limit_price"], "limit_price"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "TopOfBook":
        _require_event_keys(data, {"best_bid", "best_ask"}, "TopOfBook.data")
        return TopOfBook(
            type="TopOfBook",
            data=TopOfBookData(
                best_bid=_require_optional_int(data["best_bid"], "best_bid"),
                best_ask=_require_optional_int(data["best_ask"], "best_ask"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "OrderPartiallyFilled":
        _require_event_keys(data, {"order_id", "last_fill_qty", "remaining_qty"}, "OrderPartiallyFilled.data")
        return OrderPartiallyFilled(
            type="OrderPartiallyFilled",
            data=OrderPartiallyFilledData(
                order_id=_require_int(data["order_id"], "order_id"),
                last_fill_qty=_require_int(data["last_fill_qty"], "last_fill_qty"),
                remaining_qty=_require_int(data["remaining_qty"], "remaining_qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "OrderFilled":
        _require_event_keys(data, {"order_id", "last_fill_qty"}, "OrderFilled.data")
        return OrderFilled(
            type="OrderFilled",
            data=OrderFilledData(
                order_id=_require_int(data["order_id"], "order_id"),
                last_fill_qty=_require_int(data["last_fill_qty"], "last_fill_qty"),
                symbol=_optional_symbol(data),
            ),
        )

    if event_type == "OrderExpired":
        _require_event_keys(data, {"order_id"}, "OrderExpired.data")
        return OrderExpired(
            type="OrderExpired",
            data=OrderExpiredData(order_id=_require_int(data["order_id"], "order_id"), symbol=_optional_symbol(data)),
        )


    if event_type == "SymbolHalted":
        _require_exact_keys(data, {"symbol", "reason"}, "SymbolHalted.data")
        reason = data["reason"]
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        return SymbolHalted(type="SymbolHalted", data=SymbolHaltedData(symbol=_require_symbol(data["symbol"]), reason=reason))

    if event_type == "SymbolResumed":
        _require_exact_keys(data, {"symbol"}, "SymbolResumed.data")
        return SymbolResumed(type="SymbolResumed", data=SymbolResumedData(symbol=_require_symbol(data["symbol"])))

    if event_type == "PriceBandUpdated":
        _require_exact_keys(data, {"symbol", "lower_price", "upper_price"}, "PriceBandUpdated.data")
        return PriceBandUpdated(type="PriceBandUpdated", data=PriceBandUpdatedData(symbol=_require_symbol(data["symbol"]), lower_price=_require_optional_int(data["lower_price"], "lower_price"), upper_price=_require_optional_int(data["upper_price"], "upper_price")))

    if event_type == "CircuitBreakerTriggered":
        _require_exact_keys(data, {"symbol", "price", "reason"}, "CircuitBreakerTriggered.data")
        reason = data["reason"]
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        return CircuitBreakerTriggered(type="CircuitBreakerTriggered", data=CircuitBreakerTriggeredData(symbol=_require_symbol(data["symbol"]), price=_require_int(data["price"], "price"), reason=reason))

    if event_type == "AuctionStarted":
        _require_exact_keys(data, {"symbol", "phase"}, "AuctionStarted.data")
        return AuctionStarted(
            type="AuctionStarted",
            data=AuctionPhaseData(symbol=_require_symbol(data["symbol"]), phase=_require_trading_phase(data["phase"])),
        )

    if event_type == "AuctionEnded":
        _require_exact_keys(data, {"symbol", "phase"}, "AuctionEnded.data")
        return AuctionEnded(
            type="AuctionEnded",
            data=AuctionPhaseData(symbol=_require_symbol(data["symbol"]), phase=_require_trading_phase(data["phase"])),
        )

    if event_type == "AuctionUncross":
        _require_exact_keys(data, {"symbol", "price", "qty", "imbalance"}, "AuctionUncross.data")
        return AuctionUncross(
            type="AuctionUncross",
            data=AuctionUncrossData(
                symbol=_require_symbol(data["symbol"]),
                price=_require_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                imbalance=_require_int(data["imbalance"], "imbalance"),
            ),
        )

    if event_type == "IndicativePriceUpdated":
        _require_exact_keys(data, {"symbol", "price", "qty", "imbalance"}, "IndicativePriceUpdated.data")
        return IndicativePriceUpdated(
            type="IndicativePriceUpdated",
            data=IndicativePriceUpdatedData(
                symbol=_require_symbol(data["symbol"]),
                price=_require_optional_int(data["price"], "price"),
                qty=_require_int(data["qty"], "qty"),
                imbalance=_require_int(data["imbalance"], "imbalance"),
            ),
        )

    raise ValueError(f"unknown event type: {event_type}")


def parse_events(raw_events: list[dict[str, Any]]) -> list[TesEngineEvent]:
    if not isinstance(raw_events, list):
        raise ValueError("raw_events must be a list")
    return [parse_event(raw) for raw in raw_events]
