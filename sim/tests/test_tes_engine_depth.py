from __future__ import annotations


def test_empty_depth_returns_empty_lists() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    assert engine.depth(levels=5) == {"bids": [], "asks": []}


def test_bid_depth_visible_after_buy_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Bid", price_ticks=100, qty=10)

    assert engine.depth(levels=5) == {
        "bids": [{"price": 100, "qty": 10}],
        "asks": [],
    }


def test_ask_depth_visible_after_sell_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Ask", price_ticks=101, qty=5)

    assert engine.depth(levels=5) == {
        "bids": [],
        "asks": [{"price": 101, "qty": 5}],
    }


def test_same_price_aggregates_quantity() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Bid", price_ticks=100, qty=10)
    engine.place_limit_order(side="Bid", price_ticks=100, qty=7)

    assert engine.depth(levels=5) == {
        "bids": [{"price": 100, "qty": 17}],
        "asks": [],
    }


def test_levels_limit_works() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Bid", price_ticks=103, qty=3)
    engine.place_limit_order(side="Bid", price_ticks=102, qty=2)
    engine.place_limit_order(side="Bid", price_ticks=101, qty=1)

    assert engine.depth(levels=2) == {
        "bids": [
            {"price": 103, "qty": 3},
            {"price": 102, "qty": 2},
        ],
        "asks": [],
    }
    assert engine.depth(levels=0) == {"bids": [], "asks": []}


def test_crossing_order_updates_depth_after_trade() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Ask", price_ticks=101, qty=5)
    engine.place_limit_order(side="Bid", price_ticks=101, qty=3)

    assert engine.depth(levels=5) == {
        "bids": [],
        "asks": [{"price": 101, "qty": 2}],
    }
