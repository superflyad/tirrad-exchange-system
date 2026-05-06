"""Scheduler orchestration services for distributed TES workers."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from sim.api.execution.queue import QueueItem, RequeueResult, SQLiteRunQueue, WorkerRecord


class WorkerRegistry:
    """Persist and query worker registration and liveness metadata."""

    def __init__(self, queue: SQLiteRunQueue) -> None:
        self._queue = queue

    def register(
        self,
        worker_id: str,
        *,
        hostname: str,
        process_id: int | None = None,
        started_at: datetime | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> WorkerRecord:
        return self._queue.register_worker(
            worker_id,
            hostname=hostname,
            process_id=process_id,
            started_at=started_at,
            capabilities=capabilities,
        )

    def list_workers(self) -> list[WorkerRecord]:
        return self._queue.list_worker_records()

    def get_worker(self, worker_id: str) -> WorkerRecord | None:
        return self._queue.get_worker(worker_id)

    def drain(self, worker_id: str) -> WorkerRecord | None:
        return self._queue.drain_worker(worker_id)

    def shutdown(self, worker_id: str) -> WorkerRecord | None:
        return self._queue.shutdown_worker(worker_id)

    def detect_stale(self, *, stale_after_seconds: int | None = None) -> list[WorkerRecord]:
        return self._queue.detect_stale_workers(stale_after_seconds=stale_after_seconds)


class WorkerLeaseManager:
    """Maintain single-owner run leases and stale lease recovery."""

    def __init__(self, queue: SQLiteRunQueue) -> None:
        self._queue = queue

    def requeue_stale(self, *, stale_after_seconds: int | None = None) -> RequeueResult:
        return self._queue.requeue_stale(stale_after_seconds=stale_after_seconds)

    def leases(self) -> list[dict[str, Any]]:
        return [asdict(lease) for lease in self._queue.list_leases()]


class RunAllocator:
    """Allocate the next priority/FIFO queued run to a polling worker."""

    def __init__(self, queue: SQLiteRunQueue) -> None:
        self._queue = queue

    def claim_next(self, worker_id: str) -> QueueItem | None:
        return self._queue.claim_next(worker_id)


class SchedulerService:
    """Top-level scheduler facade used by API routes and operators."""

    def __init__(self, queue: SQLiteRunQueue) -> None:
        self.registry = WorkerRegistry(queue)
        self.lease_manager = WorkerLeaseManager(queue)
        self.allocator = RunAllocator(queue)
        self._queue = queue

    def status(self) -> dict[str, Any]:
        snapshot = self._queue.record_scheduler_metrics()
        return asdict(snapshot)

    def requeue_stale(self, *, stale_after_seconds: int | None = None) -> dict[str, Any]:
        result = self.lease_manager.requeue_stale(stale_after_seconds=stale_after_seconds)
        return asdict(result)
