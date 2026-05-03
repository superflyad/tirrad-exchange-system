from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


@dataclass(frozen=True)
class LimitOrderCommand:
    side: Literal["BUY", "SELL"]
    price: int
    qty: int
    time_in_force: Literal["GTC", "IOC", "FOK"] = "GTC"


@dataclass(frozen=True)
class MarketOrderCommand:
    side: Literal["BUY", "SELL"]
    qty: int


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: int


TesCommand: TypeAlias = LimitOrderCommand | MarketOrderCommand | CancelOrderCommand


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


def _require_time_in_force(value: Any) -> Literal["GTC", "IOC", "FOK"]:
    if value not in {"GTC", "IOC", "FOK"}:
        raise ValueError("time_in_force must be one of: GTC, IOC, FOK")
    return value


def parse_command(raw: dict[str, Any]) -> TesCommand:
    command = _require_dict(raw, "command")
    _require_exact_keys(command, {"type", "data"}, "command")

    command_type = command["type"]
    if not isinstance(command_type, str):
        raise ValueError("type must be a string")

    data = _require_dict(command["data"], "command.data")

    if command_type == "LimitOrder":
        _require_exact_keys(data, {"side", "price", "qty", "time_in_force"}, "LimitOrder.data")
        return LimitOrderCommand(
            side=_require_side(data["side"]),
            price=_require_positive_int(data["price"], "price"),
            qty=_require_positive_int(data["qty"], "qty"),
            time_in_force=_require_time_in_force(data["time_in_force"]),
        )

    if command_type == "MarketOrder":
        _require_exact_keys(data, {"side", "qty"}, "MarketOrder.data")
        return MarketOrderCommand(
            side=_require_side(data["side"]),
            qty=_require_positive_int(data["qty"], "qty"),
        )

    if command_type == "CancelOrder":
        _require_exact_keys(data, {"order_id"}, "CancelOrder.data")
        return CancelOrderCommand(order_id=_require_positive_int(data["order_id"], "order_id"))

    raise ValueError(f"unknown command type: {command_type}")


def parse_commands(raw_commands: list[dict[str, Any]]) -> list[TesCommand]:
    if not isinstance(raw_commands, list):
        raise ValueError("raw_commands must be a list")
    return [parse_command(raw) for raw in raw_commands]
