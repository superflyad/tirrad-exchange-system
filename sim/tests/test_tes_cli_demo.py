from __future__ import annotations

import argparse

from sim.tes_cli.commands.demo import add_demo_command


def _build_demo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes")
    subparsers = parser.add_subparsers(dest="command")
    sim_parser = subparsers.add_parser("sim")
    sim_subparsers = sim_parser.add_subparsers(dest="sim_command")
    add_demo_command(sim_subparsers)
    return parser


def test_demo_command_runs_without_crash(capsys) -> None:
    parser = _build_demo_parser()
    args = parser.parse_args(["sim", "demo"])

    result = args.handler(args)

    captured = capsys.readouterr()
    assert result == 0
    assert "Total Events" in captured.out
    assert "Total Trades" in captured.out
