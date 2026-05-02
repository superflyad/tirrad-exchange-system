"""TES Python CLI entrypoint."""

from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes", description="Tirrad Exchange System Python CLI")
    subparsers = parser.add_subparsers(dest="command")

    about_parser = subparsers.add_parser("about", help="Show TES CLI information")
    about_parser.set_defaults(handler=_handle_about)

    version_parser = subparsers.add_parser("version", help="Show TES CLI version")
    version_parser.set_defaults(handler=_handle_about)

    return parser


def _handle_about(_args: argparse.Namespace) -> int:
    print("Tirrad Exchange System (TES) Python CLI foundation")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return int(handler(args))
