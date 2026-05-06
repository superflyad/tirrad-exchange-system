# TES Dashboard

The TES dashboard in `web/` is the first React/Next.js operator interface for persisted and live TES API runs.

## Run locally

```bash
./tes api serve --host 127.0.0.1 --port 8000 --store sqlite
cd web
npm install
npm run dev
```

Then open <http://localhost:3000>.

## Pages

- `/`: dashboard home with run totals, recent runs, recent symbols, and API health.
- `/runs`: sortable/filterable run table.
- `/runs/[runId]`: run summary, metrics, timeline, market data, accounts, logs, and raw JSON.
- `/runs/[runId]/live`: SSE live monitor for `GET /runs/{run_id}/stream`.
- `/health`: API health/debug checks.

## API integration

The frontend keeps API access in `web/src/lib/api/client.ts`. By default the browser calls `/api/tes`, and `next.config.ts` rewrites that path to `TES_API_URL` or `http://127.0.0.1:8000`.

## Streaming

The live monitor uses `EventSource`, replays recent messages, and reconnects with exponential backoff after connection drops. Reconnects stop when a terminal `completed` or `error` category is received.

## Limitations

The initial dashboard is read-only and intentionally avoids heavy charting/state dependencies. Market data visualization is based on latest-snapshot cards and tables.


## Strategy tournaments

See [Strategy Tournaments and Parameter Sweeps](tournaments.md) for tournament API examples, report semantics, and dashboard usage.
