from __future__ import annotations

import pytest

from sim.tes_cli.cli import main


def test_list_strategies_command_returns_success(capsys: pytest.CaptureFixture[str]) -> None:
    returncode = main(["sim", "list-strategies"])

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Available Strategies" in out
    assert "simple_market_maker" in out
