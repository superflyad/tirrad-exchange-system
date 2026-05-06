from __future__ import annotations

import tes_engine

from sim.session.models import MarketSessionConfig
from sim.session.runner import MarketSessionRunner
from sim.tes_models.events import parse_event


def test_halt_resume_api_smoke() -> None:
    engine = tes_engine.MatchingEngine()
    halted = engine.halt_symbol("AAA", "news")
    assert halted == [{"type": "SymbolHalted", "data": {"symbol": "AAA", "reason": "news"}}]
    assert engine.symbol_status("AAA")["halted"] is True
    rejected = engine.place_limit_order("Bid", 100, 1, "GTC", "AAA")
    assert rejected[0]["data"]["reason"] == "SymbolHalted"
    resumed = engine.resume_symbol("AAA")
    assert resumed == [{"type": "SymbolResumed", "data": {"symbol": "AAA"}}]
    assert engine.symbol_status("AAA")["halted"] is False


def test_price_band_api_smoke() -> None:
    engine = tes_engine.MatchingEngine()
    updated = engine.set_price_bands("AAA", 95, 105)
    assert updated[0]["type"] == "PriceBandUpdated"
    assert engine.symbol_status("AAA")["lower_price"] == 95
    rejected = engine.place_limit_order("Bid", 106, 1, "GTC", "AAA")
    assert rejected[0]["data"]["reason"] == "PriceBandViolation"
    cleared = engine.clear_price_bands("AAA")
    assert cleared[0]["data"]["lower_price"] is None


def test_market_control_events_parse() -> None:
    rejected = parse_event(
        {"type": "OrderRejected", "data": {"side": "BUY", "price": 100, "qty": 1, "reason": "SymbolHalted", "symbol": "AAA"}}
    )
    assert rejected.data.reason == "SymbolHalted"
    halted = parse_event({"type": "SymbolHalted", "data": {"symbol": "AAA", "reason": "news"}})
    assert halted.data.symbol == "AAA"
    band = parse_event({"type": "PriceBandUpdated", "data": {"symbol": "AAA", "lower_price": 95, "upper_price": 105}})
    assert band.data.upper_price == 105


def test_session_report_includes_halt_count() -> None:
    result = MarketSessionRunner(
        MarketSessionConfig(
            scenario="volatile_market",
            steps=5,
            symbols=("AAA",),
            seed=42,
            initial_price=100,
            volatility=1.0,
            spread_width=1,
            min_order_size=1,
            max_order_size=2,
            probability_market_order=0.8,
            probability_cancel_replace=0.0,
            participant_count=3,
            depth_levels=2,
        )
    ).run()
    assert result.report.halt_count >= 0
    assert isinstance(result.report.halted_symbols, tuple)
