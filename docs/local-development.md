# Local Development Workflow

This workflow starts the complete local TES operator stack from a fresh clone: the persisted API, the Next.js dashboard, a persisted demo run, and the replay inspection pages.

## Defaults

- API: `http://127.0.0.1:8000`
- Dashboard: `http://localhost:3000`
- Persisted run database: `runs/tes_runs.sqlite`
- Dashboard API setting: `NEXT_PUBLIC_TES_API_URL=/api/tes`

`NEXT_PUBLIC_TES_API_URL` is the single canonical dashboard API variable. With the default `/api/tes` value, browser requests stay same-origin with the Next.js dashboard and Next.js rewrites forward them to the local API at `http://127.0.0.1:8000`.

## 1. Start the persisted API

From the repository root:

```bash
./tes api serve --store sqlite
```

The default host and port are `127.0.0.1:8000`. If that port is already occupied, the API startup command scans the next local ports and prints the port it selected. On Windows, if no nearby port is available, the error includes a `netstat` command you can use to find the process holding the port.

Verify the API directly:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"tes-api"}
```

## 2. Start the dashboard

In a second terminal:

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>. The default environment keeps dashboard requests on `/api/tes`, so no manual CORS or raw API URL wiring is required for local development.

## 3. Create a persisted demo run

In a third terminal from the repository root:

```bash
./tes api demo-run
```

The helper calls `POST /sessions/run` for you, stores the completed run through the API's SQLite backend, and prints values like:

```text
run_id=<generated-run-id>
run_url=http://127.0.0.1:8000/runs/<generated-run-id>
replay_url=http://127.0.0.1:8000/runs/<generated-run-id>/replay
```

You can customize the demo without writing curl payloads:

```bash
./tes api demo-run --steps 20 --symbol TES --seed 123
```

## 4. Inspect replay data

Use the printed `run_id` in the dashboard:

- Run detail: `http://localhost:3000/runs/<run_id>`
- Replay inspection: the run detail page loads timeline, events, snapshots, accounts, logs, and replay summary data from the persisted API record.
- API health page: `http://localhost:3000/health`

## Verification checklist

A successful local stack has all of the following:

1. API health is online at `http://127.0.0.1:8000/health`.
2. The API health response is `{"status":"ok","service":"tes-api"}`.
3. The dashboard loads at `http://localhost:3000` without a Next.js workspace-root warning.
4. `./tes api demo-run` prints a non-empty `run_id`.
5. The persisted run appears in the dashboard run list.
6. The run detail/replay data pages load for the printed `run_id`.
