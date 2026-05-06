"""Run and parse TES engine benchmarks."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

from sim.tes_benchmarks.models import BenchmarkRun, BenchmarkScenario

_HUMAN_RE = re.compile(
    r"^(?P<name>[^,]+), operation_count=(?P<ops>\d+), elapsed_s=(?P<elapsed>[0-9.]+), ops_sec=(?P<ops_sec>[0-9.]+)(?:, notes=(?P<notes>.*))?$"
)


def run_engine_benchmark(
    *,
    executable: str | Path,
    repo_root: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[BenchmarkRun, str]:
    """Execute the C++ benchmark binary and return structured plus human output."""

    completed = subprocess.run([str(executable)], text=True, capture_output=True, check=True)
    human_output = completed.stdout
    scenarios = parse_human_output(human_output)
    root = Path(repo_root or Path.cwd())
    run = BenchmarkRun.create(
        scenarios=scenarios,
        git_sha=_git_sha(root),
        machine=machine_info(),
        config=config or {},
    )
    return run, human_output


def parse_human_output(output: str) -> list[BenchmarkScenario]:
    """Parse existing human-readable benchmark output without changing it."""

    scenarios: list[BenchmarkScenario] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[TES]"):
            continue
        match = _HUMAN_RE.match(stripped)
        if match is None:
            continue
        elapsed_s = float(match.group("elapsed"))
        scenarios.append(
            BenchmarkScenario(
                name=match.group("name"),
                operation_count=int(match.group("ops")),
                elapsed_ms=elapsed_s * 1000.0,
                ops_per_sec=float(match.group("ops_sec")),
                notes=match.group("notes"),
                config={},
            )
        )
    if not scenarios:
        raise ValueError("benchmark output did not contain any parseable scenarios")
    return scenarios


def machine_info() -> dict[str, Any]:
    """Return stable platform metadata for benchmark context."""

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def write_json(run: BenchmarkRun, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_sha(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = completed.stdout.strip()
    return sha or None
