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
- `GET /runs/{run_id}/timeline` — fetch a normalized post-run inspection timeline. Supports `symbol`, `category`, `type`, `limit`, and `offset` query parameters.
- `GET /runs/{run_id}/orders/{order_id}/timeline` — fetch timeline entries that reference an order ID. Supports `symbol`, `category`, `type`, `limit`, and `offset` query parameters.
- `GET /runs/{run_id}/accounts/{account_id}/timeline` — fetch timeline entries that reference an account ID. Supports `symbol`, `category`, `type`, `limit`, and `offset` query parameters.
- `POST /runs/{run_id}/replay` — reconstruct or replay a persisted run and return replay status.
- `GET /runs/{run_id}/summary` — fetch an inspection-oriented run summary with event, trade, volume, price, and position totals.
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

Timeline response shape:

```json
{
  "run_id": "6fcd1b4e7dc94bb8b61125d2af89eaa1",
  "timeline": [
    {
      "step": 2,
      "timestamp": null,
      "sequence": 1,
      "symbol": "DEFAULT",
      "category": "event",
      "type": "TradeExecuted",
      "summary": "TradeExecuted qty=1 price=100",
      "payload": {
        "type": "TradeExecuted",
        "data": {
          "price": 100,
          "qty": 1,
          "maker_order_id": 1,
          "taker_order_id": 2
        }
      }
    }
  ]
}
```

Timeline entries normalize persisted artifacts into these fields:

- `step` — simulation/backtest step when present in the payload.
- `timestamp` — timestamp-like payload field when present; otherwise `null`.
- `sequence` — stable artifact sequence within its persisted category.
- `symbol` — directly stored symbol, single-symbol snapshot/account symbol, or the run's single configured symbol when inferable.
- `category` — one of `command`, `event`, `snapshot`, `account`, or `log`. Current API storage persists events, snapshots, accounts, and logs; command entries appear only when a future runner persists command artifacts.
- `type` — event type, snapshot/account default type, or log level.
- `summary` — short human-readable description derived from stable public payload fields.
- `payload` — original persisted JSON payload. Event payloads keep the canonical `{"type":"...","data":{...}}` shape.

Timeline examples:

```bash
curl -s 'http://127.0.0.1:8000/runs/6fcd1b4e7dc94bb8b61125d2af89eaa1/timeline?symbol=DEFAULT&category=event&limit=25&offset=0'
curl -s 'http://127.0.0.1:8000/runs/6fcd1b4e7dc94bb8b61125d2af89eaa1/orders/1/timeline'
curl -s 'http://127.0.0.1:8000/runs/6fcd1b4e7dc94bb8b61125d2af89eaa1/accounts/acct-1/timeline'
```

Replay response shape:

```json
{
  "run_id": "6fcd1b4e7dc94bb8b61125d2af89eaa1",
  "status": "reconstructed",
  "message": "Run was reconstructed from persisted artifacts; engine re-execution is unavailable.",
  "total_events": 12,
  "total_snapshots": 5,
  "total_accounts": 1,
  "total_logs": 0,
  "event_count_matches": true,
  "event_hash_matches": null
}
```

Replay status values are `replayed`, `reconstructed`, `unavailable`, and `mismatch`. For the current API, replay is a read-only reconstruction from persisted run artifacts unless a future command stream is available for deterministic engine re-execution and comparison.

Summary response shape:

```json
{
  "run_id": "6fcd1b4e7dc94bb8b61125d2af89eaa1",
  "run_type": "backtest",
  "status": "completed",
  "symbols": ["DEFAULT"],
  "total_steps": 5,
  "total_orders": 2,
  "total_events": 12,
  "total_trades": 1,
  "total_snapshots": 5,
  "total_rejections": 0,
  "total_volume": 1,
  "traded_notional": 100,
  "final_prices": {"DEFAULT": 100.5},
  "final_positions": {"DEFAULT": 1},
  "error": null
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
- `run_accounts` stores one account-state payload per row with indexed `run_id`, `account_id`, `symbol`, and sequence-backed pagination.
- `run_logs` is reserved for progress/log payloads and supports ordered retrieval even when current synchronous runners do not emit logs.

SQLite initialization enables foreign keys, WAL journal mode for file-backed databases, `synchronous=NORMAL`, and a 5-second busy timeout. Indexes are created for `run_id`, `run_type`, `status`, `created_at`, and artifact lookup paths such as event type, symbol, snapshot step, and account filters.

Expected local-use limits: this backend is intended for single-node development, repeatable research runs, and local dashboard/analytics exploration. It is not a distributed execution queue, does not coordinate multiple API writers beyond SQLite's normal locking semantics, and stores flexible payload fields as JSON rather than a fully normalized analytics warehouse. The storage interface is intentionally compatible with a future Postgres implementation using the same run lifecycle methods and indexed artifact tables.

## Current limitations

- SQLite is the default durable local store, while `--store memory` remains available for process-local development and tests.
- Execution is synchronous; a background job queue can be added without changing route contracts.
- Streaming is not implemented yet; WebSocket or Server-Sent Events can be layered onto the run service later.
- Authentication and authorization are not implemented.
- Run cancellation is modeled as a future state but not yet wired to an execution interrupt.
- Replay currently reconstructs from persisted artifacts and does not re-run the C++ engine unless a future persisted command stream is added.
- Timeline command entries are reserved for persisted command artifacts; current session/backtest storage exposes events, snapshots, accounts, and logs.
- Postgres/distributed execution, deeper replay indexing, and dashboard APIs are planned extension points.


## Live run streaming with SSE

API clients can watch run progress by connecting to the Server-Sent Events endpoint for a run:

```http
GET /runs/{run_id}/stream
Accept: text/event-stream
```

A session or backtest request can tune streaming volume with optional fields:

```json
{
  "scenario": "calm_market",
  "steps": 25,
  "progress_interval": 5,
  "stream_events": false,
  "stream_snapshots": false
}
```

- `progress_interval` defaults to `10` and controls progress-log cadence.
- `stream_events` defaults to `false`; enable it only when clients need serialized engine events in the stream.
- `stream_snapshots` defaults to `false`; enable it only when clients need book snapshots in the stream.

Each SSE record uses the event category as the SSE event name and contains one JSON `data` object:

```text
event: progress
data: {"run_id":"abc123","timestamp":"2026-05-06T12:00:00Z","step":10,"category":"progress","type":"progress","payload":{"step":10,"total_steps":25,"total_orders":91,"total_trades":12,"latest_mid":{"DEFAULT":100.5}}}
```

Stream message fields are:

- `run_id`
- `timestamp`
- `step` when available
- `category`: `status`, `progress`, `event`, `snapshot`, `account`, `log`, `error`, or `completed`
- `type`
- `payload`

Behavior notes and current limitations:

- Missing runs return `404`.
- Completed runs replay recent stored stream messages and then close.
- The API uses SSE, not WebSockets; clients should reconnect with normal SSE retry behavior if the HTTP connection drops.
- Existing synchronous run endpoints still return only after execution completes, so clients generally connect after they know the `run_id`; live in-flight consumption is available to callers that have obtained a run id from shared storage or orchestration.
- Event and snapshot streaming are opt-in to avoid noisy logs and large response bodies for quiet runs.
