from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path

from sim.backtest import BacktestConfig, BacktestRunner, export_result_json
from sim.tes_strategy.registry import get_strategy


def handle_backtest(args: argparse.Namespace) -> int:
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] if args.symbols else ["DEFAULT"]
    try:
        strategy = get_strategy(args.strategy)
    except ValueError as exc:
        print(str(exc))
        return 1
    tes_engine = import_module("tes_engine")
    engine = tes_engine.MatchingEngine()
    config = BacktestConfig(
        strategy_names=[args.strategy],
        symbols=symbols,
        initial_cash=int(args.initial_cash),
        depth_levels=int(args.depth_levels),
    )
    result = BacktestRunner(engine=engine, config=config, strategies=[strategy]).run()
    print("TES Backtest")
    print("------------")
    print(f"Strategy: {args.strategy}")
    print(f"Total Orders: {result.metrics.total_orders}")
    print(f"Total Trades: {result.metrics.total_trades}")
    print(f"Ending Equity: {result.metrics.ending_equity}")
    if args.output_json:
        output = Path(args.output_json)
        export_result_json(result, output)
        print(f"Wrote JSON report: {output}")
    return 0
