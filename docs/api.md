# TES API Service

TES includes a local FastAPI service for running deterministic market sessions and strategy backtests through JSON endpoints. The service uses the existing C++ matching engine and Python simulation layer; it does not expose raw engine objects or implementation-only fields.

## Start the API

From the repository root:

```bash
./tes api serve
```

Optional flags:

```bash
./tes api serve --host 127.0.0.1 --port 8000 --reload
./tes api serve --store sqlite --sqlite-path runs/tes_runs.sqlite
./tes api serve --store memory
```

You can also invoke the module directly:

```bash
python -m sim.api.main serve --host 127.0.0.1 --port 8000
```

The default bind address is `127.0.0.1:8000`. Local API runs use SQLite by default and create `runs/tes_runs.sqlite` when no storage flags or environment variables are provided. Set `TES_RUN_STORE=memory|sqlite` and `TES_SQLITE_PATH=/path/to/tes_runs.sqlite` to configure the same behavior through the environment.

## Endpoints

- `GET /health` — service health check.
- `POST /sessions/run` — run a market session synchronously.
- `POST /backtests/run` — run a strategy backtest synchronously.
- `GET /runs` — list stored run summaries.
- `GET /runs/{run_id}` — fetch run metadata and report.
- `GET /runs/{run_id}/report` — fetch the report for a run.
- `GET /runs/{run_id}/events` — fetch JSON-serialized events for a run. Supports `symbol`, `event_type`, `limit`, and `offset` query parameters.
- `GET /runs/{run_id}/snapshots` — fetch market data snapshots for a run. Supports `symbol`, `limit`, and `offset` query parameters.
- `GET /runs/{run_id}/accounts` — fetch account state snapshots for a run. Supports `account_id` and `symbol` query parameters.
- `GET /runs/{run_id}/logs` — fetch stored progress/log messages for a run. Supports `limit` and `offset` query parameters.
- `DELETE /runs/{run_id}` — remove a run and its stored artifacts.

## Session request example

```json
{
  "scenario": "calm_market",
  "steps": 25,
  "symbols": ["DEFAULT"],
  "seed": 42,
  "initial_price": 100,
  "volatility": 0.02,
  "participants": 20,
  "depth_levels": 5,
  "initial_cash": 1000000
}
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/sessions/run \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"calm_market","steps":25,"symbols":["DEFAULT"],"seed":42,"initial_price":100,"volatility":0.02,"participants":20,"depth_levels":5,"initial_cash":1000000}'
```

## Backtest request example

```json
{
  "strategy": "crossing_taker",
  "symbols": ["DEFAULT"],
  "initial_cash": 1000000,
  "depth_levels": 5
}
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/backtests/run \
  -H 'Content-Type: application/json' \
  -d '{"strategy":"crossing_taker","symbols":["DEFAULT"],"initial_cash":1000000,"depth_levels":5}'
```

## Response examples

Health response:

```json
{
  "status": "ok",
  "service": "tes-api"
}
```

Run response shape:

```json
{
  "run_id": "6fcd1b4e7dc94bb8b61125d2af89eaa1",
  "run_type": "backtest",
  "status": "completed",
  "created_at": "2026-05-06T12:00:00Z",
  "started_at": "2026-05-06T12:00:00Z",
  "completed_at": "2026-05-06T12:00:00Z",
  "config": {
    "strategy": "crossing_taker",
    "symbols": ["DEFAULT"],
    "initial_cash": 1000000,
    "depth_levels": 5
  },
  "report_summary": {
    "total_orders": 2,
    "total_trades": 1,
    "ending_equity": 1000000
  },
  "error": null,
  "report": {
    "starting_equity": 1000000,
    "ending_equity": 1000000,
    "total_orders": 2,
    "total_trades": 1
  }
}
```

Events are returned with the canonical TES shape:

```json
{
  "run_id": "6fcd1b4e7dc94bb8b61125d2af89eaa1",
  "events": [
    {
      "type": "OrderAccepted",
      "data": {
        "order_id": 1,
        "side": "BUY",
        "price": 100,
        "qty": 1
      }
    }
  ]
}
```

Error response shape:

```json
{
  "error": {
    "code": "run_not_found",
    "message": "run not found: missing"
  }
}
```

## Run storage

TES API storage is selected through `TES_RUN_STORE` or `./tes api serve --store`:

- `sqlite` is the default local backend. It persists runs across API restarts and creates the parent directory for `TES_SQLITE_PATH` or `--sqlite-path` when it is missing. If no path is supplied, the API uses `runs/tes_runs.sqlite` under the repository root.
- `memory` keeps the previous process-local behavior for tests and short-lived development runs. Runs are cleared when the API process exits.

The SQLite backend uses a hybrid schema designed for fast local analytics while keeping payload evolution simple:

- `runs` stores indexed metadata: `run_id`, `run_type`, `status`, timestamps, config JSON, report JSON, and failure error text.
- `run_reports` stores the full report JSON for direct report retrieval.
- `run_events` stores one event per row with indexed `run_id`, `sequence`, `event_type`, `symbol`, and optional `step`, plus the canonical event JSON payload.
- `run_snapshots` stores one snapshot per row with indexed `run_id`, `step`, `symbol`, and the snapshot JSON payload.
- `run_accounts` stores one account-state payload per row with indexed `run_id`, `account_id`, and `symbol`.
- `run_logs` is reserved for progress/log payloads and supports ordered retrieval even when current synchronous runners do not emit logs.

SQLite initialization enables foreign keys, WAL journal mode for file-backed databases, `synchronous=NORMAL`, and a 5-second busy timeout. Indexes are created for `run_id`, `run_type`, `status`, `created_at`, and artifact lookup paths such as event type, symbol, snapshot step, and account filters.

Expected local-use limits: this backend is intended for single-node development, repeatable research runs, and local dashboard/analytics exploration. It is not a distributed execution queue, does not coordinate multiple API writers beyond SQLite's normal locking semantics, and stores flexible payload fields as JSON rather than a fully normalized analytics warehouse. The storage interface is intentionally compatible with a future Postgres implementation using the same run lifecycle methods and indexed artifact tables.

## Current limitations

- SQLite is the default durable local store, while `--store memory` remains available for process-local development and tests.
- Execution is synchronous; a background job queue can be added without changing route contracts.
- Streaming is not implemented yet; WebSocket or Server-Sent Events can be layered onto the run service later.
- Authentication and authorization are not implemented.
- Run cancellation is modeled as a future state but not yet wired to an execution interrupt.
- Postgres/distributed execution, deeper replay indexing, and dashboard APIs are planned extension points.
