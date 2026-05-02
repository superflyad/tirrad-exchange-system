from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TES_SCRIPT = REPO_ROOT / "tes"
IS_WINDOWS = sys.platform.startswith("win")


def _run_tes(*args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(TES_SCRIPT), *args] if IS_WINDOWS else [str(TES_SCRIPT), *args]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_usage_includes_core_commands() -> None:
    result = _run_tes("help")

    assert result.returncode == 0
    assert "./tes check [preset|python|python-release]" in result.stdout
    assert "./tes clean" in result.stdout
    assert "./tes presets" in result.stdout


def test_sim_demo_exits_success() -> None:
    result = _run_tes("sim", "demo")

    assert result.returncode == 0
