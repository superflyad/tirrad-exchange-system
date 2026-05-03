from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TES_SCRIPT = REPO_ROOT / "tes"
IS_WINDOWS = sys.platform.startswith("win")

try:
    import tes_engine  # noqa: F401

    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


def _find_git_bash() -> str:
    candidates = [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/usr/bin/bash.exe"),
    ]

    fallback = shutil.which("bash")
    if fallback:
        candidates.append(Path(fallback))

    for candidate in candidates:
        if not candidate.exists():
            continue

        version_result = subprocess.run(
            [str(candidate), "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = version_result.stdout.lower()

        if "gnu bash" not in stdout:
            continue
        if not any(token in stdout for token in ("msys", "mingw", "pc-msys")):
            continue
        if any(
            rejected in stdout
            for rejected in (
                "windows subsystem for linux",
                "install",
                "distribution",
            )
        ):
            continue

        return str(candidate)

    pytest.skip("Git Bash is required for root tes launcher tests on Windows")


def _to_git_bash_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix()[2:]
    return f"/{drive}{rest}"


def _run_tes(*args: str) -> subprocess.CompletedProcess[str]:
    command = (
        [_find_git_bash(), _to_git_bash_path(TES_SCRIPT), *args]
        if IS_WINDOWS
        else [str(TES_SCRIPT), *args]
    )
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_strategy_discovery_lists_simple_market_maker() -> None:
    result = _run_tes("sim", "list-strategies")

    assert result.returncode == 0
    assert "simple_market_maker" in result.stdout


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_strategy_execution_simple_market_maker_returns_success() -> None:
    result = _run_tes("sim", "run", "--strategy", "simple_market_maker")

    assert result.returncode == 0


@pytest.mark.skipif(not HAS_ENGINE, reason="tes_engine extension not available")
def test_strategy_execution_crossing_taker_if_registered() -> None:
    list_result = _run_tes("sim", "list-strategies")
    assert list_result.returncode == 0

    if "crossing_taker" not in list_result.stdout:
        pytest.skip("crossing_taker not registered")

    run_result = _run_tes("sim", "run", "--strategy", "crossing_taker")

    assert run_result.returncode == 0
    assert "Total Trades" in run_result.stdout
