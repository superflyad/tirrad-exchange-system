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
```

You can also invoke the module directly:

```bash
python -m sim.api.main serve --host 127.0.0.1 --port 8000
```

The default bind address is `127.0.0.1:8000`.

## Endpoints

- `GET /health` — service health check.
- `POST /sessions/run` — run a market session synchronously.
- `POST /backtests/run` — run a strategy backtest synchronously.
- `GET /runs` — list stored run summaries.
- `GET /runs/{run_id}` — fetch run metadata and report.
- `GET /runs/{run_id}/report` — fetch the report for a run.
- `GET /runs/{run_id}/events` — fetch JSON-serialized events for a run.
- `GET /runs/{run_id}/snapshots` — fetch market data snapshots for a run.
- `GET /runs/{run_id}/accounts` — fetch account state snapshots for a run.
- `DELETE /runs/{run_id}` — remove a run from in-memory storage.

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

## Current limitations

- Run storage is in-memory and is cleared when the API process exits.
- Execution is synchronous; a background job queue can be added without changing route contracts.
- Streaming is not implemented yet; WebSocket or Server-Sent Events can be layered onto the run service later.
- Authentication and authorization are not implemented.
- Run cancellation is modeled as a future state but not yet wired to an execution interrupt.
- Persistent storage, replay indexing, and dashboard APIs are planned extension points.
