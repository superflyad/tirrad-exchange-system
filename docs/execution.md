# TES Execution Architecture

TES supports two API execution modes for sessions and backtests:

- **Sync execution** runs the simulation inside the API request handler and returns a completed run response.
- **Queued execution** persists a pending run, places its run ID on a durable queue, and lets one or more worker processes claim and execute jobs outside the API process.

The queued path separates responsibilities clearly:

1. The API validates the incoming `/sessions/run` or `/backtests/run` request.
2. The API stores a run record with `status=pending`.
3. The API enqueues the `run_id` in SQLite `run_queue`.
4. A worker polls the queue and atomically claims one available run.
5. The worker loads the stored run config, executes the session or backtest, and writes reports, events, snapshots, accounts, and logs through the existing run store.
6. The worker marks the queue item and run record `completed` or `failed`.
7. Clients observe status through `/runs/{run_id}`, `/runs/{run_id}/stream`, timeline/replay endpoints, and `/workers`.

## Starting the API

Sync-only local API:

```bash
./tes api serve --store sqlite --sqlite-path runs/tes_runs.sqlite
```

Queued-by-default API:

```bash
./tes api serve --store sqlite --sqlite-path runs/tes_runs.sqlite --queue
```

Queued execution can also be enabled with:

```bash
TES_QUEUE_ENABLED=1 ./tes api serve --store sqlite --sqlite-path runs/tes_runs.sqlite
```

## Submitting Runs

Both run endpoints accept an optional `mode` field:

```json
{
  "mode": "queued"
}
```

Valid modes are:

- `"sync"` — execute immediately in the API process.
- `"queued"` — persist as pending and enqueue for workers.
- omitted — queued when the API queue system is enabled; otherwise sync.

Queued responses keep existing run fields and add observation URLs:

```json
{
  "run_id": "...",
  "status": "pending",
  "polling_url": "/runs/...",
  "stream_url": "/runs/.../stream"
}
```

## Starting Workers

Run one worker until interrupted:

```bash
./tes worker run --worker-id worker-a --sqlite-path runs/tes_runs.sqlite
```

Run a worker for one polling pass, which is useful for tests and local smoke checks:

```bash
./tes worker run --once --worker-id worker-a --sqlite-path runs/tes_runs.sqlite
```

Worker options:

- `--worker-id`: stable ID written to queue locks and heartbeat rows.
- `--poll-interval`: seconds to wait between empty polls.
- `--max-jobs`: stop after completing or failing this many claimed jobs.
- `--sqlite-path`: SQLite database containing run storage and queue tables.
- `--once`: perform one claim/poll cycle and exit.

## SQLite Queue Behavior

The first durable queue backend is SQLite. It creates these tables in the configured database:

- `run_queue`
- `worker_heartbeats`
- `run_locks` (reserved for future lock metadata)

`run_queue` stores:

- `run_id`
- `status`
- `priority`
- `created_at`
- `available_at`
- `started_at`
- `completed_at`
- `attempts`
- `last_error`
- `locked_by`
- `locked_at`

Workers claim jobs with a single atomic SQLite update, so two workers cannot claim the same pending run. Attempts are incremented when a worker claims a run. Failed jobs retain the error in both run storage and the queue. Running jobs with stale locks are claimable again after the queue's stale-lock window.

## Cancellation

Use:

```bash
curl -X POST http://127.0.0.1:8000/runs/<run_id>/cancel
```

Pending runs are canceled before execution and removed from the executable queue path. Running cancellation is currently cooperative at the API/storage boundary: the run status and logs record the request, but engine/session loops are not forcibly interrupted.

## Worker Observation

Use:

```bash
curl http://127.0.0.1:8000/workers
```

The response lists worker IDs, status, heartbeat timestamps, and current run IDs when a worker is executing a job.

## Current Limitations

- SQLite is suitable for local durable execution and small worker pools, not high-throughput distributed clusters.
- Running cancellation is not a hard interrupt of engine execution.
- Queue priority is available in storage but not yet exposed on public run request models.
- SSE streaming works for queued runs through stored/replayed stream messages, but separate processes do not share in-memory subscribers.

## Future Queue Backends

The queue abstraction is intentionally narrow: `enqueue`, `dequeue`, `mark_running`, `mark_completed`, `mark_failed`, `list_pending`, and `list_running`. This leaves a path to add Redis, SQS, or Postgres-backed queues without changing route handlers or worker execution semantics.
