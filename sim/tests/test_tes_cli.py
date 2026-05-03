from __future__ import annotations

from sim.tes_cli.cli import main


def test_main_help_returns_success() -> None:
    assert main(["--help"]) == 0


def test_main_about_returns_success() -> None:
    assert main(["about"]) == 0


def test_main_version_returns_success() -> None:
    assert main(["version"]) == 0


def test_main_sim_list_strategies_returns_success() -> None:
    assert main(["sim", "list-strategies"]) == 0


def test_main_unknown_command_returns_non_zero() -> None:
    assert main(["not-a-command"]) != 0


def test_main_unknown_sim_command_returns_non_zero() -> None:
    assert main(["sim", "not-a-command"]) != 0
