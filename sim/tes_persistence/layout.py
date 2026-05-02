"""Deterministic filesystem layout helpers for TES simulation runs."""

from pathlib import Path

_EVENTS_FILENAME = "events.jsonl"
_METADATA_FILENAME = "metadata.json"


def _validate_base_dir(base_dir: Path) -> None:
    if not isinstance(base_dir, Path):
        raise TypeError("base_dir must be a Path")


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str):
        raise TypeError("run_id must be a non-empty string")
    if run_id == "":
        raise ValueError("run_id must be a non-empty string")


def build_run_dir(base_dir: Path, run_id: str) -> Path:
    """Return the deterministic run directory path for a run identifier."""
    _validate_base_dir(base_dir)
    _validate_run_id(run_id)
    return base_dir / run_id


def build_events_path(run_dir: Path) -> Path:
    """Return the standard events file path under a run directory."""
    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    return run_dir / _EVENTS_FILENAME


def build_metadata_path(run_dir: Path) -> Path:
    """Return the standard metadata file path under a run directory."""
    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    return run_dir / _METADATA_FILENAME


def ensure_run_dir(base_dir: Path, run_id: str) -> Path:
    """Create and return the deterministic run directory path."""
    run_dir = build_run_dir(base_dir=base_dir, run_id=run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
