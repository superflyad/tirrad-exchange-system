from __future__ import annotations

import json


def test_market_data_recorder_basic_and_bounded_history() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    recorder = tes_engine.MarketDataRecorder(max_records_per_symbol=2)

    for price in (100, 101, 102):
        engine.place_limit_order(side="Bid", price_ticks=price, qty=1, symbol="AAA")
        recorder.record_snapshot(engine.snapshot(5, "AAA"))

    assert recorder.size("AAA") == 2
    latest = recorder.latest("AAA")
    assert latest is not None
    assert latest.sequence_number == 3
    assert recorder.sequence_series("AAA") == [2, 3]


def test_market_data_recorder_analytics_and_json() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    recorder = tes_engine.MarketDataRecorder()

    engine.place_limit_order(side="Bid", price_ticks=100, qty=10, symbol="AAA")
    engine.place_limit_order(side="Ask", price_ticks=104, qty=15, symbol="AAA")
    recorder.record_snapshot(engine.snapshot(5, "AAA"))

    summary = recorder.summary("AAA")
    assert summary.best_bid == 100
    assert summary.best_ask == 104
    assert summary.spread == 4
    assert summary.total_bid_qty == 10
    assert summary.total_ask_qty == 15

    payload = json.loads(recorder.history_to_json("AAA"))
    assert payload[0]["symbol"] == "AAA"
    assert payload[0]["summary"]["spread"] == 4


def test_market_data_symbol_isolation() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    recorder = tes_engine.MarketDataRecorder()
    engine.place_limit_order(side="Bid", price_ticks=100, qty=1, symbol="AAA")
    recorder.record_snapshot(engine.snapshot(5, "AAA"))
    engine.place_limit_order(side="Ask", price_ticks=200, qty=1, symbol="BBB")
    recorder.record_snapshot(engine.snapshot(5, "BBB"))

    assert sorted(recorder.symbols()) == ["AAA", "BBB"]
    assert recorder.size("AAA") == 1
    assert recorder.size("BBB") == 1
