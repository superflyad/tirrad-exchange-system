from __future__ import annotations

from dataclasses import dataclass

from sim.tes_models.events import TesEvent


@dataclass(frozen=True)
class StrategyRunMetadata:
    strategy_name: str
    total_commands: int
    total_events: int
    total_trades: int


def build_strategy_run_metadata(
    strategy_name: str,
    events: list[TesEvent],
    total_commands: int,
) -> StrategyRunMetadata:
    if strategy_name == "":
        raise ValueError("strategy_name must be a non-empty string")
    if total_commands < 0:
        raise ValueError("total_commands must be >= 0")

    total_trades = sum(1 for event in events if event.type == "TradeExecuted")

    return StrategyRunMetadata(
        strategy_name=strategy_name,
        total_commands=total_commands,
        total_events=len(events),
        total_trades=total_trades,
    )


def strategy_metadata_to_dict(metadata: StrategyRunMetadata) -> dict[str, int | str]:
    if metadata.total_commands < 0:
        raise ValueError("total_commands must be >= 0")
    if metadata.total_events < 0:
        raise ValueError("total_events must be >= 0")
    if metadata.total_trades < 0:
        raise ValueError("total_trades must be >= 0")

    return {
        "strategy_name": metadata.strategy_name,
        "total_commands": metadata.total_commands,
        "total_events": metadata.total_events,
        "total_trades": metadata.total_trades,
    }
