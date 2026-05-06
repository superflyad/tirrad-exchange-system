"""CLI helper for formatting TES benchmark results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sim.tes_benchmarks.runner import run_engine_benchmark, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tes bench helper")
    parser.add_argument("--executable", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--preset", default=None)
    args = parser.parse_args(argv)

    config = {"preset": args.preset} if args.preset else {}
    run, human_output = run_engine_benchmark(
        executable=args.executable,
        repo_root=args.repo_root,
        config=config,
    )
    if args.output is not None:
        write_json(run, Path(args.output))
    if args.json:
        print(json.dumps(run.to_dict(), indent=2, sort_keys=True))
    else:
        print(human_output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
