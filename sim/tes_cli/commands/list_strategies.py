from __future__ import annotations

import argparse

from sim.tes_strategy.registry import list_strategy_names


def handle_list_strategies(_args: argparse.Namespace) -> int:
    print("Available Strategies")
    print("--------------------")
    for strategy_name in list_strategy_names():
        print(strategy_name)
    return 0
