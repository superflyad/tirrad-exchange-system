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


def test_worker_registration_persists_extended_metadata(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite")

    worker = queue.register_worker(
        "worker-a",
        hostname="host-a",
        process_id=123,
        capabilities={"run_types": ["session", "benchmark"]},
    )

    assert worker.worker_id == "worker-a"
    assert worker.hostname == "host-a"
    assert worker.process_id == 123
    assert worker.capabilities == {"run_types": ["session", "benchmark"]}
    assert queue.get_worker("worker-a") == worker


def test_worker_heartbeat_updates_current_job_and_progress(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite")
    queue.register_worker("worker-a", hostname="host-a")

    queue.heartbeat(
        "worker-a",
        status="busy",
        current_run_id="run-1",
        progress_summary={"phase": "executing", "step": 2},
        cpu_percent=12.5,
        memory_bytes=4096,
    )
    worker = queue.get_worker("worker-a")

    assert worker is not None
    assert worker.status == "busy"
    assert worker.current_run_id == "run-1"
    assert worker.progress_summary == {"phase": "executing", "step": 2}
    assert worker.cpu_percent == 12.5
    assert worker.memory_bytes == 4096


def test_priority_queue_ordering_is_fifo_within_priority(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite")
    queue.enqueue("low", priority=0)
    queue.enqueue("high-a", priority=10)
    queue.enqueue("high-b", priority=10)

    assert queue.claim_next("worker-a").run_id == "high-a"  # type: ignore[union-attr]
    assert queue.claim_next("worker-b").run_id == "high-b"  # type: ignore[union-attr]
    assert queue.claim_next("worker-c").run_id == "low"  # type: ignore[union-attr]


def test_stale_worker_detection_and_orphan_requeue(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite", stale_after_seconds=1)
    queue.register_worker("worker-a", hostname="host-a")
    queue.enqueue("run-1")
    claimed = queue.claim_next("worker-a")
    assert claimed is not None
    old = "2000-01-01T00:00:00+00:00"
    with queue._connection:  # noqa: SLF001 - test seeds deterministic stale state.
        queue._connection.execute("UPDATE workers SET heartbeat_at = ? WHERE worker_id = ?", (old, "worker-a"))
        queue._connection.execute("UPDATE run_queue SET locked_at = ? WHERE run_id = ?", (old, "run-1"))
        queue._connection.execute("UPDATE run_leases SET expires_at = ?, heartbeat_at = ? WHERE run_id = ?", (old, old, "run-1"))

    stale = queue.detect_stale_workers(stale_after_seconds=1)
    result = queue.requeue_stale(stale_after_seconds=1)

    assert [worker.worker_id for worker in stale] == ["worker-a"]
    assert result.requeued_runs == ["run-1"]
    assert queue.get("run-1").status == "pending"  # type: ignore[union-attr]
    assert queue.get_lease("run-1") is None


def test_tournament_child_runs_distribute_safely_by_priority(tmp_path: Path) -> None:
    queue = SQLiteRunQueue(tmp_path / "runs.sqlite")
    for run_id in ["child-1", "child-2", "child-3"]:
        queue.enqueue(run_id, priority=5)

    claimed = {queue.claim_next(worker_id).run_id for worker_id in ["worker-a", "worker-b", "worker-c"]}  # type: ignore[union-attr]

    assert claimed == {"child-1", "child-2", "child-3"}
    assert queue.claim_next("worker-d") is None


def test_scheduler_endpoints_report_status_and_requeue(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "runs.sqlite"
    queue = SQLiteRunQueue(sqlite_path, stale_after_seconds=1)
    queue.register_worker("worker-a", hostname="host-a", process_id=123, capabilities={"kind": "test"})
    queue.enqueue("run-1")
    queue.claim_next("worker-a")
    old = "2000-01-01T00:00:00+00:00"
    with queue._connection:  # noqa: SLF001 - test seeds deterministic stale state.
        queue._connection.execute("UPDATE workers SET heartbeat_at = ? WHERE worker_id = ?", (old, "worker-a"))
        queue._connection.execute("UPDATE run_queue SET locked_at = ? WHERE run_id = ?", (old, "run-1"))
    client = TestClient(create_app(store_kind="sqlite", sqlite_path=str(sqlite_path), queue_enabled=True))

    workers = client.get("/workers")
    worker = client.get("/workers/worker-a")
    status = client.get("/scheduler/status")
    requeue = client.post("/scheduler/requeue-stale?stale_after_seconds=1")
    drain = client.post("/workers/worker-a/drain")
    shutdown = client.post("/workers/worker-a/shutdown")

    assert workers.status_code == 200
    assert workers.json()[0]["hostname"] == "host-a"
    assert worker.status_code == 200
    assert status.status_code == 200
    assert status.json()["stale_worker_count"] == 1
    assert requeue.status_code == 200
    assert requeue.json()["requeued_runs"] == ["run-1"]
    assert drain.status_code == 200
    assert drain.json()["drain_requested"] is True
    assert shutdown.status_code == 200
    assert shutdown.json()["shutdown_requested"] is True
