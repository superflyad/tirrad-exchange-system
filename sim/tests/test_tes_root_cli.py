from __future__ import annotations

import subprocess
import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TES_SCRIPT = REPO_ROOT / "tes"
IS_WINDOWS = sys.platform.startswith("win")


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


def _bash_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def test_usage_includes_core_commands() -> None:
    result = _run_tes("help")

    assert result.returncode == 0
    assert "./tes check [preset|python|python-release]" in result.stdout
    assert "./tes clean" in result.stdout
    assert "./tes presets" in result.stdout


def test_sim_demo_exits_success() -> None:
    result = _run_tes("sim", "demo")

    assert result.returncode == 0


def test_resolve_python_skips_windows_store_python3_alias(tmp_path: Path) -> None:
    if not IS_WINDOWS:
        pytest.skip("Windows Store aliases are Windows-specific")

    bash = _find_git_bash()
    windows_apps = tmp_path / "Microsoft" / "WindowsApps"
    windows_apps.mkdir(parents=True)
    fake_alias = windows_apps / "python3"
    fake_alias.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    fake_alias.chmod(0o755)

    path_entries = [
        _to_git_bash_path(windows_apps),
        _to_git_bash_path(Path(sys.executable).parent),
    ]
    command = (
        f"source {_bash_quote(_to_git_bash_path(TES_SCRIPT))}; "
        f"PATH={_bash_quote(':'.join(path_entries))}; "
        "resolve_python"
    )
    result = subprocess.run(
        [bash, "-lc", command],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Microsoft/WindowsApps" not in result.stdout.replace("\\", "/")
    assert "python" in Path(result.stdout.strip()).name.lower()
