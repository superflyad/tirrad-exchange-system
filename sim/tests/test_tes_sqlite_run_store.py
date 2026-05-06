from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.storage.sqlite import SQLiteRunStore


def _store(tmp_path: Path) -> SQLiteRunStore:
    return SQLiteRunStore(tmp_path / "tes_runs.sqlite")


def _stored_run(store: SQLiteRunStore) -> str:
    record = store.create_run(run_type="backtest", config={"strategy": "demo"})
    stored = store.store_result(
        record.run_id,
        report={"total_orders": 3},
        events=[
            {"type": "OrderAccepted", "data": {"symbol": "AAA", "step": 1}},
            {"type": "TradeExecuted", "data": {"symbol": "BBB", "step": 2}},
            {"type": "TradeExecuted", "data": {"symbol": "AAA", "step": 3}},
        ],
        snapshots=[
            {"step": 1, "symbols": {"AAA": {"bid": 100}}},
            {"step": 2, "symbols": {"BBB": {"bid": 101}}},
        ],
        accounts=[
            {"account_id": "acct-1", "positions": {"AAA": 4}},
            {"account_id": "acct-2", "positions": {"BBB": 5}},
        ],
        logs=[{"level": "info", "message": "started"}, {"level": "info", "message": "done"}],
    )
    assert stored is not None
    return record.run_id


def test_sqlite_store_creates_schema_and_wal(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "tes_runs.sqlite"
    store = SQLiteRunStore(db_path)

    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = store._connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert {"runs", "run_reports", "run_events", "run_snapshots", "run_accounts"} <= tables
    assert {"idx_runs_status", "idx_runs_created_at", "idx_run_events_symbol"} <= indexes
    assert journal_mode == "wal"
    assert foreign_keys == 1


def test_sqlite_create_get_list_delete_run(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = store.create_run(run_type="session", config={"steps": 2})

    fetched = store.get_run(record.run_id)
    listed = store.list_runs()

    assert fetched is not None
    assert fetched.run_id == record.run_id
    assert fetched.config == {"steps": 2}
    assert [item.run_id for item in listed] == [record.run_id]
    assert store.delete_run(record.run_id) is True
    assert store.get_run(record.run_id) is None
    assert store.delete_run(record.run_id) is False


def test_sqlite_store_and_retrieve_payloads(tmp_path: Path) -> None:
    store = _store(tmp_path)
    run_id = _stored_run(store)

    assert store.get_report(run_id) == {"total_orders": 3}
    assert len(store.get_events(run_id) or []) == 3
    assert len(store.get_snapshots(run_id) or []) == 2
    assert len(store.get_accounts(run_id) or []) == 2
    assert store.get_logs(run_id) == [
        {"level": "info", "message": "started"},
        {"level": "info", "message": "done"},
    ]


def test_sqlite_persists_across_store_reinstantiation(tmp_path: Path) -> None:
    db_path = tmp_path / "tes_runs.sqlite"
    first = SQLiteRunStore(db_path)
    run_id = _stored_run(first)
    first.close()

    second = SQLiteRunStore(db_path)

    assert second.get_run(run_id) is not None
    assert second.get_report(run_id) == {"total_orders": 3}
    assert len(second.get_events(run_id) or []) == 3
    assert len(second.get_snapshots(run_id) or []) == 2
    assert len(second.get_accounts(run_id) or []) == 2


def test_sqlite_filters_and_paginates_payloads(tmp_path: Path) -> None:
    store = _store(tmp_path)
    run_id = _stored_run(store)

    assert [event["data"]["step"] for event in store.get_events(run_id, limit=2, offset=1) or []] == [2, 3]
    assert [event["data"]["symbol"] for event in store.get_events(run_id, symbol="AAA") or []] == [
        "AAA",
        "AAA",
    ]
    assert [event["type"] for event in store.get_events(run_id, event_type="TradeExecuted") or []] == [
        "TradeExecuted",
        "TradeExecuted",
    ]
    assert [snapshot["step"] for snapshot in store.get_snapshots(run_id, symbol="BBB") or []] == [2]
    assert [account["account_id"] for account in store.get_accounts(run_id, account_id="acct-2") or []] == [
        "acct-2"
    ]
    assert [account["account_id"] for account in store.get_accounts(run_id, symbol="AAA") or []] == [
        "acct-1"
    ]
    assert [log["message"] for log in store.get_logs(run_id, limit=1, offset=1) or []] == ["done"]


def test_sqlite_large_run_performance_smoke(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = store.create_run(run_type="backtest", config={"strategy": "large"})
    events = [
        {"type": "OrderAccepted" if index % 2 else "TradeExecuted", "data": {"symbol": "AAA", "step": index}}
        for index in range(500)
    ]

    start = time.perf_counter()
    stored = store.store_result(
        record.run_id,
        report={"total_orders": len(events)},
        events=events,
        snapshots=[{"step": index, "symbols": {"AAA": {}}} for index in range(100)],
        accounts=[{"account_id": "acct-1", "positions": {"AAA": 1}}],
    )
    read_back = store.get_events(record.run_id, symbol="AAA", limit=25, offset=100)
    elapsed = time.perf_counter() - start

    assert stored is not None
    assert read_back is not None
    assert len(read_back) == 25
    assert elapsed < 2.0


def test_api_can_use_sqlite_store_with_temp_db(tmp_path: Path) -> None:
    client = TestClient(create_app(store_kind="sqlite", sqlite_path=str(tmp_path / "api.sqlite")))

    response = client.post(
        "/sessions/run",
        json={
            "scenario": "calm_market",
            "steps": 2,
            "symbols": ["DEFAULT"],
            "seed": 42,
            "initial_price": 100,
            "volatility": 0.02,
            "participants": 5,
            "depth_levels": 3,
            "initial_cash": 1_000_000,
        },
    )

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert client.get(f"/runs/{run_id}").status_code == 200
    assert client.get(f"/runs/{run_id}/events?limit=1").status_code == 200
