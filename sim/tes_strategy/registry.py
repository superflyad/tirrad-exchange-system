from __future__ import annotations

from collections.abc import Callable

from sim.tes_strategy.examples import CrossingTakerStrategy
from sim.tes_strategy.strategy import SimpleMarketMaker, Strategy

StrategyFactory = Callable[[], Strategy]

STRATEGY_REGISTRY: dict[str, StrategyFactory] = {
    "crossing_taker": CrossingTakerStrategy,
    "simple_market_maker": SimpleMarketMaker,
}


def list_strategy_names() -> list[str]:
    """Return the sorted list of available strategy names."""

    return sorted(STRATEGY_REGISTRY)


def get_strategy(name: str) -> Strategy:
    """Create a strategy by name."""

    try:
        factory = STRATEGY_REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(list_strategy_names()) or "none"
        raise ValueError(
            f"Unknown strategy '{name}'. Available strategies: {available}."
        ) from exc
    return factory()
