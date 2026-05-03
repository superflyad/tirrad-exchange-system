from __future__ import annotations

import pytest

from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand, parse_command, parse_commands


def test_parse_limit_order_command() -> None:
    command = parse_command({"type": "LimitOrder", "data": {"side": "BUY", "price": 100, "qty": 10, "time_in_force": "GTC"}})
    assert command == LimitOrderCommand(side="BUY", price=100, qty=10, time_in_force="GTC")


def test_parse_cancel_order_command() -> None:
    command = parse_command({"type": "CancelOrder", "data": {"order_id": 1}})
    assert command == CancelOrderCommand(order_id=1)


def test_parse_commands_multiple() -> None:
    commands = parse_commands([
        {"type": "LimitOrder", "data": {"side": "SELL", "price": 101, "qty": 3, "time_in_force": "GTC"}},
        {"type": "CancelOrder", "data": {"order_id": 1}},
    ])
    assert len(commands) == 2


@pytest.mark.parametrize(
    "raw",
    [
        "not-a-dict",
        {"data": {}},
        {"type": "LimitOrder"},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": 100, "qty": 1}, "extra": 1},
        {"type": "Unknown", "data": {}},
        {"type": "LimitOrder", "data": "bad"},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": 100}},
        {"type": "CancelOrder", "data": {"order_id": 1, "extra": 2}},
        {"type": "LimitOrder", "data": {"side": "BID", "price": 100, "qty": 1}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": "100", "qty": 1}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": True, "qty": 1}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": 0, "qty": 1}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": -1, "qty": 1}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": 1, "qty": 0}},
        {"type": "LimitOrder", "data": {"side": "BUY", "price": 1, "qty": -1}},
        {"type": "CancelOrder", "data": {"order_id": 0}},
        {"type": "CancelOrder", "data": {"order_id": -1}},
    ],
)
def test_parse_command_rejections(raw: object) -> None:
    with pytest.raises(ValueError):
        parse_command(raw)  # type: ignore[arg-type]
