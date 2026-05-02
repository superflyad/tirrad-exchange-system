from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from sim.tes_cli.commands.inspect import handle_inspect
from sim.tes_models.events import (
    OrderAcceptedData,
    OrderAcceptedEvent,
    TesEvent,
    TradeExecutedData,
    TradeExecutedEvent,
)
from sim.tes_persistence.runs import save_run


def _sample_events() -> list[TesEvent]:
    return [
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=10)),
        TradeExecutedEvent(type="TradeExecuted", data=TradeExecutedData(maker_order_id=1, taker_order_id=2, price=100, qty=4)),
    ]


def test_inspect_valid_run_loads_and_returns_success(tmp_path: Path) -> None:
    run_id = "run-001"
    save_run(base_dir=tmp_path, run_id=run_id, events=_sample_events(), metadata={"run_id": run_id})

    args = Namespace(run_id=run_id, runs_dir=str(tmp_path))

    assert handle_inspect(args) == 0


def test_inspect_summary_prints_totals(tmp_path: Path, capsys: object) -> None:
    run_id = "run-002"
    save_run(base_dir=tmp_path, run_id=run_id, events=_sample_events(), metadata={"run_id": run_id})

    args = Namespace(run_id=run_id, runs_dir=str(tmp_path))
    handle_inspect(args)

    captured = capsys.readouterr()

    assert "Total Events: 2" in captured.out
    assert "Total Trades: 1" in captured.out
