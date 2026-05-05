from __future__ import annotations

import pytest

from sim.tes_models.events import parse_events

try:
    import tes_engine

    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_default_cash_only_behavior_unchanged() -> None:
    engine = tes_engine.MatchingEngine()
    engine.set_account_state(1, "TES", 100, 0)

    buy_events = engine.place_limit_order(
        side="Bid", price_ticks=50, qty=3, symbol="TES", account_id=1
    )
    sell_events = engine.place_limit_order(
        side="Ask", price_ticks=10, qty=1, symbol="TES", account_id=1
    )

    assert buy_events[0]["type"] == "OrderRejected"
    assert buy_events[0]["data"]["reason"] == "InsufficientCash"
    assert sell_events[0]["type"] == "OrderRejected"
    assert sell_events[0]["data"]["reason"] == "InsufficientPosition"


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_setting_margin_config_exposes_buying_power_and_snapshot() -> None:
    engine = tes_engine.MatchingEngine()
    engine.set_account_state(1, "TES", 10_000, 0)
    engine.set_account_risk_config(
        1,
        {
            "mode": "Margin",
            "max_leverage": 2.0,
            "initial_margin_requirement": 0.5,
            "maintenance_margin_requirement": 0.25,
        },
    )

    config = engine.account_risk_config(1)
    assert config["mode"] == "Margin"
    assert config["max_leverage"] == 2.0
    assert engine.account_buying_power(1) == pytest.approx(20_000.0)

    events = parse_events(
        engine.place_limit_order(
            side="Bid", price_ticks=100, qty=150, symbol="TES", account_id=1
        )
    )
    assert any(event.type == "OrderAccepted" for event in events)
    snapshot = engine.account_margin_snapshot(1)
    assert snapshot["available_buying_power"] == pytest.approx(5_000.0)
    assert snapshot["margin_call"] is False


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_setting_short_config_allows_negative_position() -> None:
    engine = tes_engine.MatchingEngine()
    engine.set_account_state(1, "TES", 10_000, 0)
    engine.set_account_state(2, "TES", 10_000, 0)
    engine.set_account_risk_config(
        1,
        {
            "mode": "Margin",
            "allow_short_selling": True,
            "max_leverage": 2.0,
            "initial_margin_requirement": 0.5,
            "short_margin_requirement": 0.5,
        },
    )

    resting = engine.place_limit_order(
        side="Ask", price_ticks=100, qty=5, symbol="TES", account_id=1
    )
    assert resting[0]["type"] == "OrderAccepted"
    assert engine.latest_account_snapshot(1)["reserved_short_margin"] == 250

    fill = parse_events(
        engine.place_limit_order(
            side="Bid", price_ticks=100, qty=5, symbol="TES", account_id=2
        )
    )
    assert any(event.type == "TradeExecuted" for event in fill)
    account = engine.latest_account_snapshot(1)
    assert account["positions"]["TES"] == -5
    assert account["reserved_short_margin"] == 0


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_old_sim_strategy_still_runs() -> None:
    from sim.tes_cli.cli import main

    assert main(["sim", "run", "--strategy", "crossing_taker"]) == 0
