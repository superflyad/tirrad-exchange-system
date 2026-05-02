from __future__ import annotations

import pytest

from sim.tes_strategy.registry import get_strategy, list_strategy_names
from sim.tes_strategy.strategy import Strategy


def test_list_strategy_names_returns_sorted_names() -> None:
    names = list_strategy_names()

    assert names == sorted(names)
    assert "simple_market_maker" in names


def test_get_strategy_returns_strategy_instance() -> None:
    strategy = get_strategy("simple_market_maker")

    assert isinstance(strategy, Strategy)


def test_get_strategy_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown strategy 'nope'") as exc_info:
        get_strategy("nope")

    assert "simple_market_maker" in str(exc_info.value)
