from __future__ import annotations

import importlib
from typing import Any

from sim.tes_models.commands import LimitOrderCommand
from sim.tes_simulation.runner import run_simulation


def _find_total_traded_qty(analytics_result: Any) -> int | float | None:
    if isinstance(analytics_result, dict):
        value = analytics_result.get("total_traded_qty")
        if isinstance(value, (int, float)):
            return value
    value = getattr(analytics_result, "total_traded_qty", None)
    if isinstance(value, (int, float)):
        return value
    return None


def _serialize_events_with_module(module: Any, events: list[Any]) -> list[dict[str, Any]]:
    for fn_name in ("serialize_events", "events_to_jsonable", "to_jsonable_events"):
        fn = getattr(module, fn_name, None)
        if callable(fn):
            serialized = fn(events)
            if isinstance(serialized, list):
                return serialized

    event_fn = getattr(module, "serialize_event", None)
    if callable(event_fn):
        serialized = [event_fn(event) for event in events]
        if isinstance(serialized, list):
            return serialized

    raise AssertionError("Serialization module found but no supported serializer entrypoint")


def test_tes_full_python_integration_smoke() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]

    result = run_simulation(engine, commands)

    assert result.total_commands == 2
    assert result.total_events > 0
    assert any(event.type == "TradeExecuted" for event in result.events)

    analytics_module = importlib.import_module("sim.tes_analytics") if importlib.util.find_spec("sim.tes_analytics") else None
    if analytics_module is not None:
        analyze_fn = getattr(analytics_module, "analyze_events", None)
        if callable(analyze_fn):
            analytics_result = analyze_fn(result.events)
            total_traded_qty = _find_total_traded_qty(analytics_result)
            assert total_traded_qty is not None
            assert total_traded_qty > 0

    serialization_module = importlib.import_module("sim.tes_serialization") if importlib.util.find_spec("sim.tes_serialization") else None
    if serialization_module is not None:
        serialized_events = _serialize_events_with_module(serialization_module, result.events)
        assert serialized_events
        for raw_event in serialized_events:
            assert isinstance(raw_event, dict)
            assert set(raw_event.keys()) == {"type", "data"}
