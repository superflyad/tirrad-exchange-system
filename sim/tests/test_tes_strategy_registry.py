from __future__ import annotations

import pytest

from sim.tes_strategy.examples import CrossingTakerStrategy
from sim.tes_strategy.registry import get_strategy, list_strategy_names
from sim.tes_strategy.strategy import Strategy


def test_list_strategy_names_returns_sorted_names() -> None:
    names = list_strategy_names()

    assert names == sorted(names)
    assert "crossing_taker" in names
    assert "simple_market_maker" in names


def test_list_strategy_names_are_non_empty_strings() -> None:
    names = list_strategy_names()

    assert names
    assert all(isinstance(name, str) and name for name in names)


def test_get_strategy_returns_strategy_instance() -> None:
    strategy = get_strategy("simple_market_maker")

    assert isinstance(strategy, Strategy)


def test_get_strategy_crossing_taker_returns_crossing_taker_strategy() -> None:
    strategy = get_strategy("crossing_taker")

    assert isinstance(strategy, CrossingTakerStrategy)


def test_get_strategy_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown strategy 'nope'") as exc_info:
        get_strategy("nope")

    assert "crossing_taker" in str(exc_info.value)
    assert "simple_market_maker" in str(exc_info.value)


def test_registered_strategy_objects_expose_on_start_and_on_event() -> None:
    for name in list_strategy_names():
        strategy = get_strategy(name)

        assert hasattr(strategy, "on_start")
        assert callable(strategy.on_start)
        assert hasattr(strategy, "on_event")
        assert callable(strategy.on_event)
