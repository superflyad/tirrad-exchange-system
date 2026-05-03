from __future__ import annotations

from pathlib import Path

from sim.tes_models.events import OrderAcceptedData, OrderAccepted, TesEngineEvent, TopOfBookData, TopOfBook
from sim.tes_persistence.runs import load_run, save_run


def _sample_events() -> list[TesEngineEvent]:
    return [
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=10)),
        TopOfBook(type="TopOfBook", data=TopOfBookData(best_bid=99, best_ask=101)),
    ]


def test_save_run_writes_events_and_metadata_and_returns_run_dir(tmp_path: Path) -> None:
    run_id = "run-001"
    events = _sample_events()
    metadata = {"run_id": run_id, "summary": {"total_events": 2}}

    run_dir = save_run(base_dir=tmp_path, run_id=run_id, events=events, metadata=metadata)

    assert run_dir == tmp_path / run_id
    assert run_dir.exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "metadata.json").exists()


def test_save_and_load_run_roundtrip(tmp_path: Path) -> None:
    run_id = "run-001"
    events = _sample_events()
    metadata = {
        "run_id": run_id,
        "summary": {
            "total_commands": 2,
            "total_events": 2,
            "total_order_accepted": 1,
            "total_order_canceled": 0,
            "total_trades": 0,
        },
    }

    save_run(base_dir=tmp_path, run_id=run_id, events=events, metadata=metadata)

    loaded_events, loaded_metadata = load_run(base_dir=tmp_path, run_id=run_id)

    assert loaded_events == events
    assert loaded_metadata == metadata
