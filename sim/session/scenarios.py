from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketScenario:
    name: str
    volatility_multiplier: float
    spread_multiplier: float
    market_order_bias: float


_SCENARIOS: dict[str, MarketScenario] = {
    "calm_market": MarketScenario("calm_market", 0.7, 0.9, -0.1),
    "volatile_market": MarketScenario("volatile_market", 1.8, 1.4, 0.2),
    "trending_up": MarketScenario("trending_up", 1.1, 1.0, 0.1),
    "trending_down": MarketScenario("trending_down", 1.1, 1.0, 0.1),
    "liquidity_shock": MarketScenario("liquidity_shock", 2.2, 2.0, 0.35),
}


def get_market_scenario(name: str) -> MarketScenario:
    if name not in _SCENARIOS:
        raise ValueError(f"unknown scenario: {name}")
    return _SCENARIOS[name]
