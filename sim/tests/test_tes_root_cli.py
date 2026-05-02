from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TES_SCRIPT = REPO_ROOT / "tes"


def _run_tes(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(TES_SCRIPT), *args],
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
