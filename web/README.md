# TES Dashboard

The TES dashboard is a Next.js + TypeScript web interface for operating local Tirrad Exchange System API runs.

## Local startup

Start the FastAPI service on port 8000:

```bash
./tes api serve --host 127.0.0.1 --port 8000 --store sqlite
```

Start the dashboard on port 3000:

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:3000>. The dashboard proxies `/api/tes/*` requests to `http://127.0.0.1:8000` by default.

## Configuration

- `TES_API_URL`: server-side Next.js rewrite target. Defaults to `http://127.0.0.1:8000`.
- `NEXT_PUBLIC_TES_API_URL`: browser-visible API base. Defaults to `/api/tes`, which uses the local Next.js rewrite and avoids CORS requirements during local development.

## Architecture

- `src/app`: App Router pages for dashboard home, run list, run detail, live monitor, and API health.
- `src/components`: reusable operator UI components such as tables, timeline viewer, market data panel, JSON inspector, and live monitor.
- `src/lib/api`: typed API client helpers. Components should use this layer instead of scattering `fetch` calls.
- `src/hooks`: client-side hooks for async loading and SSE live stream handling.
- `src/types`: TypeScript mirrors of stable TES API response contracts.
- `src/styles`: global dark-mode friendly operator styling.

## Streaming behavior

The live page connects to `GET /runs/{run_id}/stream` using `EventSource`. It replays recent messages, displays progress, trade counts, latest prices, and recent logs/events, then reconnects with exponential backoff if the stream drops. Terminal `completed` and `error` stream categories stop reconnect attempts.

## Current limitations

- Market visualization is intentionally lightweight and uses latest-snapshot cards rather than a full charting dependency.
- Run detail tabs load bounded recent collections for responsiveness.
- The dashboard is read-only; launching sessions/backtests remains in the CLI/API workflow.
