from __future__ import annotations

import pytest

from sim.strategies.fok_failure import FokFailureStrategy
from sim.strategies.fok_success import FokSuccessStrategy
from sim.strategies.ioc_partial_fill import IocPartialFillStrategy
from sim.strategies.market_against_resting import MarketOrderAgainstRestingLiquidityStrategy
from sim.strategies.new_order_support import detect_new_order_api_support, missing_reason


@pytest.mark.parametrize(
    "strategy",
    [
        MarketOrderAgainstRestingLiquidityStrategy(),
        IocPartialFillStrategy(),
        FokSuccessStrategy(),
        FokFailureStrategy(),
    ],
)
def test_new_order_fixtures_on_start_returns_commands_or_skips(strategy) -> None:
    support = detect_new_order_api_support()
    if not support.available:
        pytest.skip(missing_reason())

    commands = strategy.on_start()

    assert isinstance(commands, list)
    assert len(commands) >= 2
