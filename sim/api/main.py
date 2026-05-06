"""Command-line entrypoint for serving the TES API."""

from __future__ import annotations

import argparse
import os


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes api", description="Serve the TES local API")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--store", choices=["memory", "sqlite"], default=None)
    parser.add_argument("--sqlite-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "serve":
        import uvicorn

        if args.store is not None:
            os.environ["TES_RUN_STORE"] = args.store
        if args.sqlite_path is not None:
            os.environ["TES_SQLITE_PATH"] = args.sqlite_path
        uvicorn.run("sim.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
