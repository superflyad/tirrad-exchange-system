from __future__ import annotations

import json
from argparse import Namespace

from sim.backtest import BacktestConfig, BacktestRunner
from sim.tes_cli.commands.backtest import handle_backtest
from sim.tes_strategy.examples import CrossingTakerStrategy


def test_backtest_runner_executes_crossing_taker_and_records_outputs() -> None:
    import tes_engine

    runner = BacktestRunner(
        engine=tes_engine.MatchingEngine(),
        config=BacktestConfig(strategy_names=["crossing_taker"], symbols=["DEFAULT"], initial_cash=1_000_000, depth_levels=5),
        strategies=[CrossingTakerStrategy()],
    )
    result = runner.run()

    assert result.commands
    assert result.events
    assert result.snapshots
    assert result.account_states
    assert result.metrics.total_orders >= 2
    assert result.metrics.total_trades >= 1


def test_backtest_json_export_roundtrip(tmp_path) -> None:
    import tes_engine

    runner = BacktestRunner(
        engine=tes_engine.MatchingEngine(),
        config=BacktestConfig(strategy_names=["crossing_taker"], symbols=["DEFAULT"], initial_cash=1_000_000, depth_levels=5),
        strategies=[CrossingTakerStrategy()],
    )
    result = runner.run()
    payload = json.loads(result.to_json())
    assert "config" in payload
    assert "metrics" in payload


def test_backtest_multisymbol_metrics_split() -> None:
    import tes_engine
    from sim.tes_models.commands import LimitOrderCommand

    class MultiSymbolStrategy(CrossingTakerStrategy):
        def on_start(self):
            return [
                LimitOrderCommand(side="BUY", price=100, qty=2, symbol="AAA"),
                LimitOrderCommand(side="SELL", price=100, qty=2, symbol="AAA"),
                LimitOrderCommand(side="BUY", price=200, qty=1, symbol="BBB"),
                LimitOrderCommand(side="SELL", price=200, qty=1, symbol="BBB"),
            ]

    runner = BacktestRunner(
        engine=tes_engine.MatchingEngine(),
        config=BacktestConfig(strategy_names=["multi"], symbols=["AAA", "BBB"], initial_cash=1_000_000, depth_levels=5),
        strategies=[MultiSymbolStrategy()],
    )
    result = runner.run()
    assert set(result.metrics.per_symbol_volume.keys()) == {"AAA", "BBB"}
    assert result.metrics.per_symbol_volume["AAA"] > 0
    assert result.metrics.per_symbol_volume["BBB"] > 0


def test_backtest_cli_command_works(tmp_path) -> None:
    output = tmp_path / "backtest.json"
    rc = handle_backtest(Namespace(strategy="crossing_taker", symbols="DEFAULT", initial_cash=1000000, depth_levels=5, output_json=str(output)))
    assert rc == 0
    assert output.exists()
