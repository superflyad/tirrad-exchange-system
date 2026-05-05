from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sim.tes_cli.commands.save import run_save_command


class _FakeMatchingEngine:
    def __init__(self) -> None:
        self._next_order_id = 1

    def place_limit_order(
        self, side: str, price: int, qty: int, time_in_force: str = "GTC", symbol: str = "DEFAULT"
    ) -> list[dict]:
        order_id = self._next_order_id
        self._next_order_id += 1
        normalized_side = "BUY" if side == "Bid" else "SELL"
        return [
            {
                "type": "OrderAccepted",
                "data": {"order_id": order_id, "side": normalized_side, "price": price, "qty": qty, "symbol": symbol},
            },
            {
                "type": "TopOfBook",
                "data": {
                    "best_bid": price if normalized_side == "BUY" else None,
                    "best_ask": price if normalized_side == "SELL" else None,
                    "symbol": symbol,
                },
            },
        ]

    def cancel(self, order_id: int) -> list[dict]:
        return [{"type": "OrderCanceled", "data": {"order_id": order_id}}]


def _install_fake_engine_module(monkeypatch) -> None:
    monkeypatch.setitem(__import__("sys").modules, "tes_engine", SimpleNamespace(MatchingEngine=_FakeMatchingEngine))


def test_run_save_command_creates_run_directory_with_expected_files(tmp_path: Path, monkeypatch) -> None:
    _install_fake_engine_module(monkeypatch)

    run_dir = run_save_command(base_dir=tmp_path)

    assert run_dir.exists()
    assert run_dir.is_dir()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "metadata.json").exists()


def test_run_save_command_prints_saved_path(tmp_path: Path, capsys, monkeypatch) -> None:
    _install_fake_engine_module(monkeypatch)

    run_dir = run_save_command(base_dir=tmp_path)

    captured = capsys.readouterr()
    assert "Run saved:" in captured.out
    assert str(run_dir) in captured.out


def test_run_save_command_uses_provided_run_id(tmp_path: Path, monkeypatch) -> None:
    _install_fake_engine_module(monkeypatch)

    run_id = "sim-fixed-id"
    run_dir = run_save_command(base_dir=tmp_path, run_id=run_id)

    assert run_dir.name == run_id
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "metadata.json").exists()
