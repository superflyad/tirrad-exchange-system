"""Command-line entrypoint for serving and operating the TES API."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_API_URL = f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}"
_PORT_SCAN_LIMIT = 20


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes api", description="Serve and operate the TES local API")
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="Serve the TES local API")
    serve.add_argument("--host", default=DEFAULT_API_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_API_PORT)
    serve.add_argument("--reload", action="store_true")
    serve.add_argument("--store", choices=["memory", "sqlite"], default=None)
    serve.add_argument("--sqlite-path", default=None)
    serve.add_argument("--queue", action="store_true", help="Enable queued run execution by default")

    demo = subparsers.add_parser("demo-run", help="Create a persisted demo session run through the API")
    demo.add_argument("--api-url", default=DEFAULT_API_URL, help=f"TES API base URL (default: {DEFAULT_API_URL})")
    demo.add_argument("--steps", type=int, default=8, help="Number of deterministic demo steps to run")
    demo.add_argument("--symbol", default="DEFAULT", help="Symbol for the demo run")
    demo.add_argument("--seed", type=int, default=42, help="Deterministic seed for the demo run")
    return parser


def _normalize_api_url(value: str) -> str:
    normalized = value.strip()
    return normalized[:-1] if normalized.endswith("/") else normalized


def _demo_payload(*, steps: int, symbol: str, seed: int) -> dict[str, Any]:
    symbol_value = symbol.strip()
    if symbol_value == "":
        raise ValueError("--symbol must be a non-empty string")
    if steps <= 0:
        raise ValueError("--steps must be a positive integer")
    return {
        "scenario": "calm_market",
        "steps": steps,
        "symbols": [symbol_value],
        "seed": seed,
        "initial_price": 100,
        "volatility": 0.02,
        "participants": 6,
        "depth_levels": 3,
        "initial_cash": 1_000_000,
        "mode": "sync",
    }


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TES API returned HTTP {exc.code} for {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Could not reach TES API at {url}. Start it with './tes api serve --store sqlite' first. Details: {exc.reason}"
        ) from exc
    return json.loads(text)


def _run_demo(args: argparse.Namespace) -> int:
    try:
        payload = _demo_payload(steps=args.steps, symbol=args.symbol, seed=args.seed)
        api_url = _normalize_api_url(args.api_url)
        result = _post_json(f"{api_url}/sessions/run", payload)
    except (RuntimeError, ValueError) as exc:
        print(f"[TES] demo-run failed: {exc}", file=sys.stderr)
        return 1

    run_id = result.get("run_id")
    if not isinstance(run_id, str) or run_id == "":
        print(f"[TES] demo-run failed: API response did not include run_id: {result}", file=sys.stderr)
        return 1
    print(f"run_id={run_id}")
    print(f"run_url={api_url}/runs/{run_id}")
    print(f"replay_url={api_url}/runs/{run_id}/replay")
    return 0


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _select_port(host: str, requested_port: int) -> int:
    if _port_is_available(host, requested_port):
        return requested_port
    for candidate in range(requested_port + 1, requested_port + _PORT_SCAN_LIMIT + 1):
        if _port_is_available(host, candidate):
            print(
                f"[TES] Port {requested_port} is already in use on {host}; starting API on {candidate} instead. "
                "If you need a fixed port, stop the process using the original port or pass --port explicitly.",
                file=sys.stderr,
            )
            return candidate
    raise RuntimeError(
        f"No available API port found from {requested_port} through {requested_port + _PORT_SCAN_LIMIT} on {host}. "
        "On Windows this is commonly caused by reserved or occupied localhost ports; run 'netstat -ano | findstr :"
        f"{requested_port}' to identify a listener, then stop it or choose a free --port."
    )


def _run_serve(args: argparse.Namespace) -> int:
    import uvicorn

    if args.store is not None:
        os.environ["TES_RUN_STORE"] = args.store
    if args.sqlite_path is not None:
        os.environ["TES_SQLITE_PATH"] = args.sqlite_path
    if args.queue:
        os.environ["TES_QUEUE_ENABLED"] = "1"
    try:
        port = _select_port(args.host, args.port)
    except RuntimeError as exc:
        print(f"[TES] API startup failed: {exc}", file=sys.stderr)
        return 1
    uvicorn.run("sim.api.app:app", host=args.host, port=port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if not raw_args or raw_args[0].startswith("-"):
        raw_args.insert(0, "serve")
    args = _build_parser().parse_args(raw_args)
    command = args.command or "serve"
    if command == "serve":
        return _run_serve(args)
    if command == "demo-run":
        return _run_demo(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
