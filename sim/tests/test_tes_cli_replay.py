from __future__ import annotations

from sim.tes_cli.commands.replay import replay_saved_run
from sim.tes_models.events import OrderAcceptedData, OrderAcceptedEvent
from sim.tes_persistence.runs import save_run


def test_replay_executes(tmp_path, capsys) -> None:
    event = OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=2))
    save_run(
        base_dir=tmp_path,
        run_id="run-001",
        events=[event],
        metadata={"run_id": "run-001"},
    )

    exit_code = replay_saved_run(run_id="run-001", base_dir=tmp_path)

    assert exit_code == 0


def test_replay_output_contains_expected_text(tmp_path, capsys) -> None:
    event = OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=2))
    save_run(
        base_dir=tmp_path,
        run_id="run-002",
        events=[event],
        metadata={"run_id": "run-002"},
    )

    replay_saved_run(run_id="run-002", base_dir=tmp_path)
    output = capsys.readouterr().out

    assert "Replay Complete" in output
    assert "Total Events: 1" in output
