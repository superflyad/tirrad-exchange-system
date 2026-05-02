from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = REPO_ROOT / "examples" / "save_and_load_run.py"


def test_saved_run_example_exists() -> None:
    assert EXAMPLE_PATH.is_file()


def test_saved_run_example_imports_without_running_main() -> None:
    spec = importlib.util.spec_from_file_location("examples.save_and_load_run", EXAMPLE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
