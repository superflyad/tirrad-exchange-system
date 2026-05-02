from __future__ import annotations

import json
from pathlib import Path


def write_metadata_json(path: Path, metadata: dict) -> None:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dict")

    path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_metadata_json(path: Path) -> dict:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")

    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dict")

    return metadata
