from __future__ import annotations

from pathlib import Path

from sim.tes_models.events import TesEvent
from sim.tes_persistence.events import read_events_jsonl, write_events_jsonl
from sim.tes_persistence.layout import build_events_path, build_metadata_path, ensure_run_dir
from sim.tes_persistence.metadata import read_metadata_json, write_metadata_json


def save_run(base_dir: Path, run_id: str, events: list[TesEvent], metadata: dict) -> Path:
    run_dir = ensure_run_dir(base_dir=base_dir, run_id=run_id)

    events_path = build_events_path(run_dir=run_dir)
    metadata_path = build_metadata_path(run_dir=run_dir)

    write_events_jsonl(path=events_path, events=events)
    write_metadata_json(path=metadata_path, metadata=metadata)

    return run_dir


def load_run(base_dir: Path, run_id: str) -> tuple[list[TesEvent], dict]:
    run_dir = ensure_run_dir(base_dir=base_dir, run_id=run_id)

    events_path = build_events_path(run_dir=run_dir)
    metadata_path = build_metadata_path(run_dir=run_dir)

    events = read_events_jsonl(path=events_path)
    metadata = read_metadata_json(path=metadata_path)

    return events, metadata
