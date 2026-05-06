# Replay Viewer

TES replay viewer turns persisted runs into time-controlled market sessions for debugging, demos, and replay verification triage.

## Architecture

Replay uses persisted API artifacts and does not re-execute the C++ engine in the visualization path. The backend builds a `ReplayTimeline` from persisted event, snapshot, account, and log steps, and exposes immutable `ReplayFrame` objects for one step at a time. A pure `ReplayPlaybackController` supports play, pause, seek, jump-to-step, jump-to-event, speed changes, and next/previous frame navigation.

The dashboard page at `/runs/[runId]/replay` incrementally requests ranged frames and overlays:

- order-book top-of-book and ladder data
- trade tape entries
- mid/last-trade chart data
- account deltas and account state payloads
- timeline events with filters and jump actions

## Playback controls

The replay page supports:

- play/pause
- next and previous replay frame
- first and last frame jumps
- timeline scrubber
- playback speed selector
- symbol switching
- event marker jumps
- jump to the first replay-verification divergence when available

Playback is client-side over server-provided frames. The cursor step is deterministic and bounded by the backend timeline.

## Replay APIs

### `GET /runs/{run_id}/replay`

Returns initial replay session state:

- `cursor`: current step, paused/playing state, and speed
- `timeline`: available steps, event steps, symbols, and frame count
- `frame`: first frame payload

### `GET /runs/{run_id}/replay/frame/{step}`

Returns one `ReplayFrame`. Optional query params:

- `symbol`: restrict frame artifacts to a symbol where possible

### `GET /runs/{run_id}/replay/range`

Returns bounded replay frames for incremental loading. Query params:

- `start_step`
- `end_step`
- `symbol`
- `include_snapshots`
- `include_events`
- `include_accounts`

Use this endpoint for viewer playback windows instead of loading a full large run.

### `GET /runs/{run_id}/replay/summary`

Returns stable summary metadata: symbols, step bounds, counts, available event types, and first divergence step when replay verification has produced one.

## Replay frame shape

A replay frame contains:

- `step`
- `timestamp`
- `symbols` and selected `symbol`
- `trades`
- `snapshots`
- `top_of_book`
- `account_deltas`
- `accounts`
- `market_metrics`
- `event_summaries`

The event payloads embedded in frames preserve the public Python event contract: `{ "type": "...", "data": {...} }`.

## Performance considerations

Large runs should be explored with range requests and disabled payload classes when not needed. For example, a trade tape can request `include_snapshots=false`, while an account-only panel can request `include_events=false`.

The dashboard requests a small forward playback window from the current step. Backend frame construction is read-only over persisted artifacts, so future optimization can add per-run caches without changing the API shape.

## Current limitations

- The viewer reconstructs visualization frames from persisted artifacts and does not stream engine internals.
- Full depth ladders depend on depth data being present in snapshots; otherwise the UI displays best bid/ask levels only.
- Aggressor side is shown only when the persisted trade event exposes it.
- Charting is intentionally lightweight SVG to avoid adding dashboard dependencies.
