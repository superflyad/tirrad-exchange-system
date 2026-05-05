from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from sim.tes_engine_adapter import execute_command
from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import OrderRejected, TesEngineEvent, TradeExecuted
from sim.tes_strategy.strategy import Strategy

@dataclass(frozen=True)
class BacktestConfig:
    strategy_names: list[str]
    symbols: list[str]
    initial_cash: int
    depth_levels: int = 5

@dataclass(frozen=True)
class BacktestStep:
    step_index: int
    commands: list[TesCommand]
    events: list[TesEngineEvent]
    market_snapshots: dict[str, dict[str, Any]]
    account_snapshot: dict[str, Any]

@dataclass(frozen=True)
class BacktestReport:
    starting_equity: int; ending_equity: int; realized_pnl: int; unrealized_pnl: int
    total_traded_notional: int; total_trades: int; total_orders: int; fill_ratio: float; rejected_orders: int
    per_symbol_volume: dict[str, int]; per_symbol_position: dict[str, int]; cash_balance: int; equity_curve: list[int]

@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig; steps: list[BacktestStep]; commands: list[TesCommand]; events: list[TesEngineEvent]
    snapshots: list[dict[str, dict[str, Any]]]; account_states: list[dict[str, Any]]; metrics: BacktestReport
    def to_dict(self) -> dict[str, Any]: return asdict(self)
    def to_json(self) -> str: return json.dumps(self.to_dict(), indent=2, sort_keys=True)

class BacktestRunner:
    def __init__(self, engine: Any, config: BacktestConfig, strategies: list[Strategy]) -> None:
        self._engine = engine; self._config = config; self._strategies = strategies
    def run(self) -> BacktestResult:
        all_commands=[]; all_events=[]; steps=[]; snapshots=[]; account_states=[]
        cash=self._config.initial_cash; positions={s:0 for s in self._config.symbols}
        pending=[]
        for s in self._strategies: pending.extend(s.on_start())
        idx=0
        while pending:
            idx += 1
            command = pending.pop(0); all_commands.append(command)
            step_events = execute_command(self._engine, command); all_events.extend(step_events)
            if isinstance(command, LimitOrderCommand):
                for e in step_events:
                    if isinstance(e, TradeExecuted):
                        sign = 1 if command.side == "BUY" else -1
                        positions[command.symbol] = positions.get(command.symbol, 0) + sign * e.data.qty
                        cash += (-sign) * (e.data.price * e.data.qty)
            for s in self._strategies:
                for e in step_events: pending.extend(s.on_event(e))
                pending.extend(s.on_market_data({sym:self._engine.snapshot(self._config.depth_levels, sym) for sym in self._config.symbols}))
            snaps = {sym:self._engine.snapshot(self._config.depth_levels, sym) for sym in self._config.symbols}
            snapshots.append(snaps)
            equity = cash + self._mark_to_market(positions, snaps)
            acct={"cash":cash,"positions":dict(positions),"equity":equity}
            account_states.append(acct)
            steps.append(BacktestStep(idx,[command],step_events,snaps,acct))
        for s in self._strategies: s.on_finish()
        return BacktestResult(self._config,steps,all_commands,all_events,snapshots,account_states,self._build_report(all_commands,all_events,account_states,positions,cash))
    def _mark_to_market(self, positions: dict[str, int], snapshots: dict[str, dict[str, Any]]) -> int:
        total=0
        for symbol,qty in positions.items():
            mid=self._mid(snapshots.get(symbol, {}))
            if mid is not None: total += qty*mid
        return total
    def _mid(self, snapshot: dict[str, Any]) -> int | None:
        bids=snapshot.get("bids",[]); asks=snapshot.get("asks",[])
        bb=bids[0]["price"] if bids else None; ba=asks[0]["price"] if asks else None
        if bb is None and ba is None: return None
        if bb is None: return int(ba)
        if ba is None: return int(bb)
        return int((bb+ba)/2)
    def _build_report(self, commands, events, account_states, positions, cash):
        trades=[e for e in events if isinstance(e,TradeExecuted)]; rejects=[e for e in events if isinstance(e,OrderRejected)]
        per_symbol_volume={s:0 for s in self._config.symbols}
        for t in trades: per_symbol_volume[t.data.symbol]=per_symbol_volume.get(t.data.symbol,0)+t.data.qty
        curve=[self._config.initial_cash]+[s["equity"] for s in account_states]
        end=curve[-1]
        return BacktestReport(self._config.initial_cash,end,end-self._config.initial_cash,0,sum(t.data.price*t.data.qty for t in trades),len(trades),len(commands),(len(trades)/len(commands) if commands else 0.0),len(rejects),per_symbol_volume,dict(positions),cash,curve)

def export_result_json(result: BacktestResult, path: Path) -> None:
    path.write_text(result.to_json()+"\n", encoding="utf-8")
