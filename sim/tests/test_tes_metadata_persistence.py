from __future__ import annotations

from pathlib import Path

import pytest

from sim.tes_persistence.metadata import read_metadata_json, write_metadata_json


def test_write_and_read_metadata_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    metadata = {
        "run_id": "run-001",
        "summary": {
            "total_commands": 3,
            "total_events": 2,
            "total_order_accepted": 1,
            "total_order_canceled": 0,
            "total_trades": 1,
        },
    }

    write_metadata_json(path=path, metadata=metadata)

    expected_json = (
        "{\n"
        '  "run_id": "run-001",\n'
        '  "summary": {\n'
        '    "total_commands": 3,\n'
        '    "total_events": 2,\n'
        '    "total_order_accepted": 1,\n'
        '    "total_order_canceled": 0,\n'
        '    "total_trades": 1\n'
        "  }\n"
        "}\n"
    )
    assert path.read_text(encoding="utf-8") == expected_json

    loaded = read_metadata_json(path=path)

    assert loaded == metadata


def test_write_metadata_json_rejects_non_path() -> None:
    with pytest.raises(TypeError, match="path must be a Path"):
        write_metadata_json(path="metadata.json", metadata={})  # type: ignore[arg-type]


def test_write_metadata_json_rejects_non_dict_metadata(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="metadata must be a dict"):
        write_metadata_json(path=tmp_path / "metadata.json", metadata=[])  # type: ignore[arg-type]


def test_read_metadata_json_rejects_non_path() -> None:
    with pytest.raises(TypeError, match="path must be a Path"):
        read_metadata_json(path="metadata.json")  # type: ignore[arg-type]


def test_read_metadata_json_rejects_non_dict_payload(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="metadata must be a dict"):
        read_metadata_json(path=path)
