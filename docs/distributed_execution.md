# Distributed Execution

TES distributed execution extends the existing queued API mode with a SQLite-backed scheduler, worker registry, and run leasing model. The goal is to let many local or host-distributed workers poll concurrently while preserving deterministic simulation inputs and existing run/event contracts.

## Architecture overview

The orchestration layer is intentionally small and storage-first:

- `SchedulerService` exposes scheduler status and stale recovery operations.
- `WorkerRegistry` stores worker identity, host/process metadata, capabilities, status, and operator controls.
- `RunAllocator` claims pending runs by priority and FIFO ordering within the same priority.
- `WorkerLeaseManager` maintains single-owner run leases and recovers expired leases.
- `SQLiteRunQueue` remains the durable queue implementation and owns the atomic SQL updates used by workers.

The C++ matching engine remains the execution source of truth. Distributed orchestration only decides *which worker owns a pending run*; it does not change matching behavior, command validation, event serialization, replay verification, or benchmark semantics.

## Worker lifecycle

A worker follows this lifecycle:

1. Register with `worker_id`, `hostname`, optional `process_id`, `started_at`, capabilities, and initial status.
2. Heartbeat while idle with status `idle`.
3. Atomically claim a run and transition to `busy` with `current_run_id`.
4. Heartbeat progress summaries while the run is active.
5. Mark the run completed or failed and clear the active lease.
6. Return to `idle`, or become `offline` when shutdown is requested.

Supported statuses are:

- `idle`: worker is healthy and can accept new work.
- `busy`: worker owns a current run lease.
- `offline`: worker has been intentionally stopped or shut down.
- `stale`: scheduler detected that heartbeats exceeded the configured timeout.

Workers can also receive drain and shutdown requests through the API. Drain requests tell a worker to stop claiming additional work after its current run; shutdown requests mark a worker offline for operator visibility.

## Leasing model

Run ownership is represented twice for compatibility and observability:

- `run_queue.locked_by` / `run_queue.locked_at` provide the queue-visible lock state.
- `run_leases` stores the single-owner lease with acquisition, heartbeat, and expiration timestamps.

Claiming is atomic: SQLite updates one eligible pending or expired running row and returns the claimed row in a single statement. Eligible runs are ordered by `priority DESC`, then `created_at ASC`, then `run_id ASC`, which gives priority scheduling plus FIFO behavior within each priority bucket.

Workers refresh their lease on heartbeat by extending `expires_at`. Terminal run states delete the lease so completed, failed, and canceled runs cannot be reclaimed.

## Stale recovery

The scheduler detects stale workers by comparing `workers.heartbeat_at` against the configured timeout. Stale jobs are running queue items whose `locked_at` timestamp is older than the timeout. Calling `POST /scheduler/requeue-stale`:

1. Marks expired workers as `stale`.
2. Resets expired running queue rows to `pending`.
3. Clears their stale lease rows.
4. Records a scheduler metric snapshot.

This makes orphaned jobs recoverable without weakening strict run models. A requeued run is executed from persisted config by a later worker claim.

## API endpoints

Distributed execution adds these endpoints:

- `GET /workers`
- `GET /workers/{worker_id}`
- `GET /scheduler/status`
- `POST /scheduler/requeue-stale`
- `POST /workers/{worker_id}/drain`
- `POST /workers/{worker_id}/shutdown`

The dashboard Workers page consumes the worker list and scheduler status to show active worker activity, current jobs, stale worker alerts, queue depth, run counts, utilization, stale jobs, failed jobs, throughput, average wait time, and average run duration.

## Storage schema

SQLite stores orchestration data in these tables:

- `workers`: current registration, status, heartbeat, capabilities, resource usage, drain/shutdown flags.
- `worker_heartbeats`: append-only heartbeat samples for audit and future time-series views.
- `run_leases`: current single-owner run lease for active jobs.
- `scheduler_metrics`: point-in-time queue depth, wait/run duration, utilization, stale count, failed count, and throughput snapshots.

The existing `run_queue` table remains the queue source for pending/running/completed/failed/canceled jobs.

## Scaling limitations

SQLite WAL mode supports multiple polling workers well for local and modest shared-host deployments, but it is not a global distributed lock service. Practical limitations include:

- one writer at a time;
- file-system dependent lock behavior on network volumes;
- no cross-region latency tolerance;
- limited time-series retention controls;
- operator-managed stale timeout tuning.

Use conservative heartbeat intervals and stale timeouts so long deterministic simulations are not prematurely requeued.

## Future Redis/Postgres/cloud migration path

The scheduler API is intentionally separated from the storage implementation. A future migration can keep the service contracts while replacing SQLite with:

- Postgres row-level locks or advisory locks for stronger concurrent leasing;
- Redis streams or sorted sets for high-throughput queues;
- cloud queue systems for elastic worker pools;
- a metrics backend such as Prometheus for long retention and alerting;
- object storage for large replay artifacts.

The migration should preserve the public event shape, strict command/event models, replay determinism, and the scheduler endpoints listed above.
