from __future__ import annotations

import tes_engine
from sim.tes_models.commands import LimitOrderCommand
from sim.tes_simulation.runner import run_simulation


def main() -> None:
    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]

    result = run_simulation(engine, commands)

    for event in result.events:
        print(f"{event.type}: {event.data}")


if __name__ == "__main__":
    main()
