from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.execution.executor import RunExecutor
from sim.api.execution.queue import SQLiteRunQueue
from sim.api.execution.worker import Worker
from sim.api.models import SessionRunRequest
from sim.api.services.run_service import RunService
from sim.api.services.stream_service import StreamService
from sim.api.storage.sqlite import SQLiteRunStore


def _session_payload() -> dict[str, object]:
    return {
        "scenario": "calm_market",
        "steps": 2,
        "symbols": ["DEFAULT"],
        "seed": 42,
        "initial_price": 100,
        "volatility": 0.02,
        "participants": 3,
        "depth_levels": 1,
        "initial_cash": 1_000_000,
    }


def test_sqlite_queue_enqueue_and_atomic_claim(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite")
    queue.enqueue("run-1")

    assert [item.run_id for item in queue.list_pending()] == ["run-1"]
    first = queue.claim_next("worker-a")
    second = queue.claim_next("worker-b")

    assert first is not None
    assert first.run_id == "run-1"
    assert first.locked_by == "worker-a"
    assert second is None
    assert [item.run_id for item in queue.list_running()] == ["run-1"]


def test_worker_once_executes_pending_run(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "runs.sqlite"
    store = SQLiteRunStore(sqlite_path)
    stream = StreamService(store)
    service = RunService(store, stream)
    queued = service.queue_session(SessionRunRequest(**_session_payload()))
    queue = SQLiteRunQueue(sqlite_path)
    queue.enqueue(queued.run_id)
    worker = Worker(
        queue=queue,
        executor=RunExecutor(service),
        run_service=service,
        worker_id="worker-a",
        once=True,
    )

    result = worker.run()
    record = store.get_run(queued.run_id)

    assert result.jobs_completed == 1
    assert record is not None
    assert record.status == "completed"
    assert record.report["total_steps"] == 2
    assert queue.get(queued.run_id).status == "completed"  # type: ignore[union-attr]


def test_worker_failure_marks_failed_with_error(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "runs.sqlite"
    store = SQLiteRunStore(sqlite_path)
    stream = StreamService(store)
    service = RunService(store, stream)
    record = store.create_run(run_type="session", config=_session_payload() | {"scenario": "missing"})
    queue = SQLiteRunQueue(sqlite_path)
    queue.enqueue(record.run_id)
    worker = Worker(
        queue=queue,
        executor=RunExecutor(service),
        run_service=service,
        worker_id="worker-a",
        once=True,
    )

    result = worker.run()
    failed = store.get_run(record.run_id)

    assert result.jobs_failed == 1
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error
    assert queue.get(record.run_id).status == "failed"  # type: ignore[union-attr]


def test_queued_api_request_creates_pending_run(tmp_path: Path) -> None:
    client = TestClient(
        create_app(store_kind="sqlite", sqlite_path=str(tmp_path / "runs.sqlite"), queue_enabled=True)
    )

    response = client.post("/sessions/run", json=_session_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["polling_url"] == f"/runs/{payload['run_id']}"
    assert payload["stream_url"] == f"/runs/{payload['run_id']}/stream"


def test_pending_run_can_be_canceled(tmp_path: Path) -> None:
    client = TestClient(
        create_app(store_kind="sqlite", sqlite_path=str(tmp_path / "runs.sqlite"), queue_enabled=True)
    )
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.post(f"/runs/{created['run_id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


def test_sync_mode_still_executes_immediately_when_queue_enabled(tmp_path: Path) -> None:
    client = TestClient(
        create_app(store_kind="sqlite", sqlite_path=str(tmp_path / "runs.sqlite"), queue_enabled=True)
    )

    response = client.post("/sessions/run", json=_session_payload() | {"mode": "sync"})

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["report"]["total_steps"] == 2


def test_workers_endpoint_reports_heartbeats(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "runs.sqlite"
    queue = SQLiteRunQueue(sqlite_path)
    queue.heartbeat("worker-a", status="idle")
    client = TestClient(create_app(store_kind="sqlite", sqlite_path=str(sqlite_path), queue_enabled=True))

    response = client.get("/workers")

    assert response.status_code == 200
    assert response.json()[0]["worker_id"] == "worker-a"
