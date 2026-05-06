"""Worker process implementation for queued TES API runs."""

from __future__ import annotations

import argparse
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path

from sim.api.execution.executor import RunExecutor
from sim.api.execution.queue import SQLiteRunQueue
from sim.api.services.benchmark_service import BenchmarkService
from sim.api.services.run_service import RunService
from sim.api.services.stream_service import StreamService
from sim.api.services.tournament_service import TournamentService
from sim.api.storage.sqlite import SQLiteRunStore
from sim.api.storage import DEFAULT_SQLITE_PATH


@dataclass(frozen=True)
class WorkerResult:
    """Summary of a worker polling run."""

    worker_id: str
    jobs_completed: int
    jobs_failed: int
    polls: int


class Worker:
    """Poll a durable run queue and execute claimed runs."""

    def __init__(
        self,
        *,
        queue: SQLiteRunQueue,
        executor: RunExecutor,
        run_service: RunService,
        worker_id: str,
        tournament_service: TournamentService | None = None,
        poll_interval: float = 1.0,
        max_jobs: int | None = None,
        once: bool = False,
    ) -> None:
        self._queue = queue
        self._executor = executor
        self._run_service = run_service
        self._tournament_service = tournament_service
        self._worker_id = worker_id
        self._poll_interval = poll_interval
        self._max_jobs = max_jobs
        self._once = once

    def run(self) -> WorkerResult:
        jobs_completed = 0
        jobs_failed = 0
        polls = 0
        self._queue.register_worker(
            self._worker_id,
            hostname=socket.gethostname(),
            process_id=os.getpid(),
            capabilities={"run_types": ["session", "backtest", "benchmark"]},
            status="idle",
        )
        while self._max_jobs is None or jobs_completed + jobs_failed < self._max_jobs:
            polls += 1
            worker_record = self._queue.get_worker(self._worker_id)
            if worker_record is not None and worker_record.shutdown_requested:
                self._queue.heartbeat(self._worker_id, status="offline")
                break
            if worker_record is not None and worker_record.drain_requested:
                self._queue.heartbeat(self._worker_id, status="idle")
                if self._once:
                    break
                time.sleep(self._poll_interval)
                continue

            item = self._queue.claim_next(self._worker_id)
            if item is None:
                self._queue.heartbeat(self._worker_id, status="idle")
                if self._once:
                    break
                time.sleep(self._poll_interval)
                continue

            self._queue.heartbeat(
                self._worker_id,
                status="busy",
                current_run_id=item.run_id,
                progress_summary={"phase": "claimed"},
            )
            self._run_service._store.append_log(  # noqa: SLF001 - worker intentionally records lifecycle logs.
                item.run_id,
                {"level": "info", "message": "worker claimed run", "worker_id": self._worker_id},
            )
            try:
                self._executor.execute(item.run_id)
                if self._tournament_service is not None:
                    self._tournament_service.aggregate_for_child(item.run_id)
            except Exception as exc:  # Worker boundary must turn all failures into durable state.
                message = str(exc) or exc.__class__.__name__
                self._queue.heartbeat(
                    self._worker_id,
                    status="busy",
                    current_run_id=item.run_id,
                    progress_summary={"phase": "failed", "error": message},
                )
                self._queue.mark_failed(item.run_id, message)
                self._run_service._store.append_log(  # noqa: SLF001
                    item.run_id,
                    {"level": "error", "message": "worker execution failed", "error": message},
                )
                if self._tournament_service is not None:
                    self._tournament_service.aggregate_for_child(item.run_id)
                jobs_failed += 1
            else:
                self._queue.heartbeat(
                    self._worker_id,
                    status="busy",
                    current_run_id=item.run_id,
                    progress_summary={"phase": "completed"},
                )
                self._queue.mark_completed(item.run_id)
                jobs_completed += 1
            finally:
                self._queue.heartbeat(self._worker_id, status="idle")

            if self._once:
                break
        return WorkerResult(
            worker_id=self._worker_id,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed,
            polls=polls,
        )


def build_worker(*, sqlite_path: str | Path, worker_id: str, poll_interval: float, max_jobs: int | None, once: bool) -> Worker:
    store = SQLiteRunStore(sqlite_path)
    stream_service = StreamService(store)
    run_service = RunService(store, stream_service)
    queue = SQLiteRunQueue(sqlite_path)
    return Worker(
        queue=queue,
        executor=RunExecutor(run_service, BenchmarkService(store)),
        run_service=run_service,
        tournament_service=TournamentService(store, run_service, queue),
        worker_id=worker_id,
        poll_interval=poll_interval,
        max_jobs=max_jobs,
        once=once,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tes worker", description="Run TES queued execution workers")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Poll and execute queued runs")
    run_parser.add_argument("--worker-id", default=f"{socket.gethostname()}-{id(parser)}")
    run_parser.add_argument("--poll-interval", type=float, default=1.0)
    run_parser.add_argument("--max-jobs", type=int, default=None)
    run_parser.add_argument("--sqlite-path", default=str(DEFAULT_SQLITE_PATH))
    run_parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command != "run":
        _build_parser().print_help()
        return 0
    worker = build_worker(
        sqlite_path=args.sqlite_path,
        worker_id=args.worker_id,
        poll_interval=args.poll_interval,
        max_jobs=args.max_jobs,
        once=args.once,
    )
    result = worker.run()
    print(
        f"worker_id={result.worker_id} completed={result.jobs_completed} "
        f"failed={result.jobs_failed} polls={result.polls}"
    )
    return 0 if result.jobs_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
