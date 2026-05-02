from __future__ import annotations

from pathlib import Path

from sim.tes_cli.commands.save import run_save_command


def test_run_save_command_creates_run_directory_with_expected_files(tmp_path: Path) -> None:
    run_dir = run_save_command(base_dir=tmp_path)

    assert run_dir.exists()
    assert run_dir.is_dir()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "metadata.json").exists()


def test_run_save_command_prints_saved_path(tmp_path: Path, capsys) -> None:
    run_dir = run_save_command(base_dir=tmp_path)

    captured = capsys.readouterr()
    assert captured.out == f"Run saved:\n{run_dir}\n"
