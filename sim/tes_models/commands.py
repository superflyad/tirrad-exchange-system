from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

DEFAULT_SYMBOL = "DEFAULT"


@dataclass(frozen=True)
class LimitOrderCommand:
    side: Literal["BUY", "SELL"]
    price: int
    qty: int
    time_in_force: Literal["GTC", "IOC", "FOK"] = "GTC"
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class HiddenOrderCommand:
    side: Literal["BUY", "SELL"]
    price: int
    qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class IcebergOrderCommand:
    side: Literal["BUY", "SELL"]
    price: int
    total_qty: int
    display_qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class MarketOrderCommand:
    side: Literal["BUY", "SELL"]
    qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class StopOrderCommand:
    side: Literal["BUY", "SELL"]
    stop_price: int
    qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class StopLimitOrderCommand:
    side: Literal["BUY", "SELL"]
    stop_price: int
    limit_price: int
    qty: int
    symbol: str = DEFAULT_SYMBOL


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: int


@dataclass(frozen=True)
class ReplaceOrderCommand:
    order_id: int
    price: int
    qty: int


@dataclass(frozen=True)
class SetTradingPhaseCommand:
    symbol: str
    phase: Literal["Continuous", "OpeningAuction", "ClosingAuction", "Halted"]


@dataclass(frozen=True)
class UncrossAuctionCommand:
    symbol: str = DEFAULT_SYMBOL


TesCommand: TypeAlias = (
    LimitOrderCommand
    | HiddenOrderCommand
    | IcebergOrderCommand
    | MarketOrderCommand
    | StopOrderCommand
    | StopLimitOrderCommand
    | CancelOrderCommand
    | ReplaceOrderCommand
    | SetTradingPhaseCommand
    | UncrossAuctionCommand
)


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


def _require_positive_int(value: Any, field_name: str) -> int:
    parsed = _require_int(value, field_name)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return parsed


def _require_side(value: Any) -> Literal["BUY", "SELL"]:
    if value not in {"BUY", "SELL"}:
        raise ValueError("side must be either 'BUY' or 'SELL'")
    return value


def _require_trading_phase(value: Any) -> Literal["Continuous", "OpeningAuction", "ClosingAuction", "Halted"]:
    if value not in {"Continuous", "OpeningAuction", "ClosingAuction", "Halted"}:
        raise ValueError("phase must be one of: Continuous, OpeningAuction, ClosingAuction, Halted")
    return value


def _require_time_in_force(value: Any) -> Literal["GTC", "IOC", "FOK"]:
    if value not in {"GTC", "IOC", "FOK"}:
        raise ValueError("time_in_force must be one of: GTC, IOC, FOK")
    return value


def _require_symbol(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("symbol must be a string")
    return value


def _require_command_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    keys = set(value.keys())
    with_symbol = expected | {"symbol"}
    if keys != expected and keys != with_symbol:
        raise ValueError(f"{name} keys must be exactly {sorted(expected)} or {sorted(with_symbol)}, got {sorted(keys)}")


def parse_command(raw: dict[str, Any]) -> TesCommand:
    command = _require_dict(raw, "command")
    _require_exact_keys(command, {"type", "data"}, "command")

    command_type = command["type"]
    if not isinstance(command_type, str):
        raise ValueError("type must be a string")

    data = _require_dict(command["data"], "command.data")

    if command_type == "LimitOrder":
        _require_command_keys(data, {"side", "price", "qty", "time_in_force"}, "LimitOrder.data")
        return LimitOrderCommand(
            side=_require_side(data["side"]),
            price=_require_positive_int(data["price"], "price"),
            qty=_require_positive_int(data["qty"], "qty"),
            time_in_force=_require_time_in_force(data["time_in_force"]),
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "HiddenOrder":
        _require_command_keys(data, {"side", "price", "qty"}, "HiddenOrder.data")
        return HiddenOrderCommand(
            side=_require_side(data["side"]),
            price=_require_positive_int(data["price"], "price"),
            qty=_require_positive_int(data["qty"], "qty"),
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "IcebergOrder":
        _require_command_keys(data, {"side", "price", "total_qty", "display_qty"}, "IcebergOrder.data")
        total_qty = _require_positive_int(data["total_qty"], "total_qty")
        display_qty = _require_positive_int(data["display_qty"], "display_qty")
        if display_qty > total_qty:
            raise ValueError("display_qty must be less than or equal to total_qty")
        return IcebergOrderCommand(
            side=_require_side(data["side"]),
            price=_require_positive_int(data["price"], "price"),
            total_qty=total_qty,
            display_qty=display_qty,
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "MarketOrder":
        _require_command_keys(data, {"side", "qty"}, "MarketOrder.data")
        return MarketOrderCommand(
            side=_require_side(data["side"]),
            qty=_require_positive_int(data["qty"], "qty"),
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "StopMarketOrder":
        _require_command_keys(data, {"side", "stop_price", "qty"}, "StopMarketOrder.data")
        return StopOrderCommand(
            side=_require_side(data["side"]),
            stop_price=_require_positive_int(data["stop_price"], "stop_price"),
            qty=_require_positive_int(data["qty"], "qty"),
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "StopLimitOrder":
        _require_command_keys(data, {"side", "stop_price", "limit_price", "qty"}, "StopLimitOrder.data")
        return StopLimitOrderCommand(
            side=_require_side(data["side"]),
            stop_price=_require_positive_int(data["stop_price"], "stop_price"),
            limit_price=_require_positive_int(data["limit_price"], "limit_price"),
            qty=_require_positive_int(data["qty"], "qty"),
            symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)),
        )

    if command_type == "CancelOrder":
        _require_exact_keys(data, {"order_id"}, "CancelOrder.data")
        return CancelOrderCommand(order_id=_require_positive_int(data["order_id"], "order_id"))

    if command_type == "ReplaceOrder":
        _require_exact_keys(data, {"order_id", "price", "qty"}, "ReplaceOrder.data")
        return ReplaceOrderCommand(
            order_id=_require_positive_int(data["order_id"], "order_id"),
            price=_require_positive_int(data["price"], "price"),
            qty=_require_positive_int(data["qty"], "qty"),
        )

    if command_type == "SetTradingPhase":
        _require_exact_keys(data, {"symbol", "phase"}, "SetTradingPhase.data")
        return SetTradingPhaseCommand(symbol=_require_symbol(data["symbol"]), phase=_require_trading_phase(data["phase"]))

    if command_type == "UncrossAuction":
        _require_command_keys(data, set(), "UncrossAuction.data")
        return UncrossAuctionCommand(symbol=_require_symbol(data.get("symbol", DEFAULT_SYMBOL)))

    raise ValueError(f"unknown command type: {command_type}")


def parse_commands(raw_commands: list[dict[str, Any]]) -> list[TesCommand]:
    if not isinstance(raw_commands, list):
        raise ValueError("raw_commands must be a list")
    return [parse_command(raw) for raw in raw_commands]
