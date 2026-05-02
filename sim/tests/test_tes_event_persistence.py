from __future__ import annotations

from pathlib import Path

import pytest

from sim.tes_models.events import (
    OrderAcceptedData,
    OrderAcceptedEvent,
    TesEvent,
    TopOfBookData,
    TopOfBookEvent,
)
from sim.tes_persistence.events import read_events_jsonl, write_events_jsonl


def _sample_events() -> list[TesEvent]:
    return [
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=10)),
        TopOfBookEvent(type="TopOfBook", data=TopOfBookData(best_bid=99, best_ask=101)),
    ]


def test_write_read_events_jsonl_roundtrip(tmp_path: Path) -> None:
    events = _sample_events()
    file_path = tmp_path / "events.jsonl"

    write_events_jsonl(file_path, events)

    lines = file_path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        '{"type":"OrderAccepted","data":{"order_id":1,"side":"BUY","price":100,"qty":10}}',
        '{"type":"TopOfBook","data":{"best_bid":99,"best_ask":101}}',
    ]

    parsed_events = read_events_jsonl(file_path)
    assert parsed_events == events


def test_write_read_events_jsonl_empty_list(tmp_path: Path) -> None:
    file_path = tmp_path / "events-empty.jsonl"

    write_events_jsonl(file_path, [])

    assert file_path.read_text(encoding="utf-8") == ""
    assert read_events_jsonl(file_path) == []


def test_read_events_jsonl_rejects_malformed_line(tmp_path: Path) -> None:
    file_path = tmp_path / "events-malformed.jsonl"
    file_path.write_text(
        '{"type":"OrderAccepted","data":{"order_id":1,"side":"BUY","price":100,"qty":10}}\nnot-json\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="malformed JSONL at line 2: invalid JSON"):
        read_events_jsonl(file_path)
