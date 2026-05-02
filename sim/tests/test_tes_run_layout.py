from pathlib import Path

import pytest

from sim.tes_persistence.layout import (
    build_events_path,
    build_metadata_path,
    build_run_dir,
    ensure_run_dir,
)


def test_build_run_dir_returns_expected_path() -> None:
    base_dir = Path("/tmp/tes-runs")

    run_dir = build_run_dir(base_dir=base_dir, run_id="run-001")

    assert run_dir == Path("/tmp/tes-runs/run-001")


def test_build_run_dir_validates_base_dir_type() -> None:
    with pytest.raises(TypeError, match="base_dir must be a Path"):
        build_run_dir(base_dir="/tmp/tes-runs", run_id="run-001")  # type: ignore[arg-type]


def test_build_run_dir_validates_run_id_type() -> None:
    with pytest.raises(TypeError, match="run_id must be a non-empty string"):
        build_run_dir(base_dir=Path("/tmp/tes-runs"), run_id=123)  # type: ignore[arg-type]


def test_build_run_dir_validates_non_empty_run_id() -> None:
    with pytest.raises(ValueError, match="run_id must be a non-empty string"):
        build_run_dir(base_dir=Path("/tmp/tes-runs"), run_id="")


def test_build_events_path_uses_standard_filename() -> None:
    events_path = build_events_path(run_dir=Path("/tmp/tes-runs/run-001"))

    assert events_path == Path("/tmp/tes-runs/run-001/events.jsonl")


def test_build_events_path_validates_run_dir_type() -> None:
    with pytest.raises(TypeError, match="run_dir must be a Path"):
        build_events_path(run_dir="/tmp/tes-runs/run-001")  # type: ignore[arg-type]


def test_build_metadata_path_uses_standard_filename() -> None:
    metadata_path = build_metadata_path(run_dir=Path("/tmp/tes-runs/run-001"))

    assert metadata_path == Path("/tmp/tes-runs/run-001/metadata.json")


def test_build_metadata_path_validates_run_dir_type() -> None:
    with pytest.raises(TypeError, match="run_dir must be a Path"):
        build_metadata_path(run_dir="/tmp/tes-runs/run-001")  # type: ignore[arg-type]


def test_ensure_run_dir_creates_directory(tmp_path: Path) -> None:
    run_dir = ensure_run_dir(base_dir=tmp_path, run_id="run-001")

    assert run_dir == tmp_path / "run-001"
    assert run_dir.exists()
    assert run_dir.is_dir()
