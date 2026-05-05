"""TES Python CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes", description="Tirrad Exchange System Python CLI")
    subparsers = parser.add_subparsers(dest="command")

    about_parser = subparsers.add_parser("about", help="Show TES CLI information")
    about_parser.set_defaults(handler=_handle_about)

    version_parser = subparsers.add_parser("version", help="Show TES CLI version")
    version_parser.set_defaults(handler=_handle_about)

    sim_parser = subparsers.add_parser("sim", help="Run simulation workflows")
    sim_subparsers = sim_parser.add_subparsers(dest="sim_command")

    demo_parser = sim_subparsers.add_parser("demo", help="Run deterministic TES demo simulation")
    demo_parser.set_defaults(handler=_handle_demo)

    save_parser = sim_subparsers.add_parser("save", help="Persist a simulation run")
    save_parser.add_argument("--run-id", default=None)
    save_parser.add_argument("--runs-dir", default="out/runs")
    save_parser.set_defaults(handler=_handle_save)

    inspect_parser = sim_subparsers.add_parser("inspect", help="Inspect a saved run")
    inspect_parser.add_argument("run_id")
    inspect_parser.add_argument("--runs-dir", default="out/runs")
    inspect_parser.set_defaults(handler=_handle_inspect)

    replay_parser = sim_subparsers.add_parser("replay", help="Replay a saved run")
    replay_parser.add_argument("run_id")
    replay_parser.add_argument("--runs-dir", default="out/runs")
    replay_parser.set_defaults(handler=_handle_replay)

    run_parser = sim_subparsers.add_parser("run", help="Run a strategy simulation")
    run_parser.add_argument("--strategy", required=True)
    run_parser.add_argument("--verbose", action="store_true", help="Show detailed commands/events/depth")
    run_parser.add_argument("--depth-levels", type=int, default=5, help="Depth levels to print (>= 0)")
    run_parser.set_defaults(func=_handle_run, handler=_handle_run)

    backtest_parser = sim_subparsers.add_parser("backtest", help="Run a strategy backtest")
    backtest_parser.add_argument("--strategy", required=True)
    backtest_parser.add_argument("--symbols", default="DEFAULT")
    backtest_parser.add_argument("--initial-cash", type=int, default=1_000_000)
    backtest_parser.add_argument("--depth-levels", type=int, default=5)
    backtest_parser.add_argument("--output-json", default=None)
    backtest_parser.set_defaults(handler=_handle_backtest)


    session_parser = sim_subparsers.add_parser("session", help="Run a time-stepped market session")
    session_parser.add_argument("--scenario", default="calm_market")
    session_parser.add_argument("--steps", type=int, required=True)
    session_parser.add_argument("--symbols", default="DEFAULT")
    session_parser.add_argument("--seed", type=int, default=42)
    session_parser.add_argument("--initial-price", type=int, default=100)
    session_parser.add_argument("--volatility", type=float, default=0.02)
    session_parser.add_argument("--participants", type=int, default=20)
    session_parser.add_argument("--output-json", type=Path, default=None)
    session_parser.add_argument("--depth-levels", type=int, default=5)
    session_parser.set_defaults(handler=_handle_session)

    list_strategies_parser = sim_subparsers.add_parser(
        "list-strategies",
        help="List available strategies",
    )
    list_strategies_parser.set_defaults(handler=_handle_list_strategies)

    return parser


def _handle_about(_args: argparse.Namespace) -> int:
    print("Tirrad Exchange System (TES) Python CLI foundation")
    return 0


def _handle_demo(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.demo import handle_demo

    return int(handle_demo(args))


def _handle_save(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.save import run_save_command

    run_save_command(base_dir=Path(args.runs_dir), run_id=args.run_id)
    return 0


def _handle_inspect(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.inspect import handle_inspect

    return int(handle_inspect(args))


def _handle_run(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.run import handle_run

    return int(handle_run(args))


def _handle_replay(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.replay import replay_saved_run

    return int(replay_saved_run(run_id=args.run_id, base_dir=Path(args.runs_dir)))


def _handle_backtest(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.backtest import handle_backtest

    return int(handle_backtest(args))

def _handle_session(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.session import handle_session

    return int(handle_session(args))

def _handle_list_strategies(args: argparse.Namespace) -> int:
    from sim.tes_cli.commands.list_strategies import handle_list_strategies

    return int(handle_list_strategies(args))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    handler = getattr(args, "handler", getattr(args, "func", None))
    if handler is None:
        parser.print_help()
        return 0

    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
