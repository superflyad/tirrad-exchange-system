# Replay Verification and Run Diffing

TES treats deterministic replay as a platform contract: a completed run should be reproducible from its stored run type and strict configuration, and the rerun should produce the same public artifacts. Replay verification is intentionally artifact-focused and uses only Python-visible run outputs rather than C++ implementation details.

## Deterministic replay philosophy

A verification pass loads a persisted run, reconstructs the original strict API request from the stored config, reruns the same session or backtest path, and compares the stored artifacts with the rerun artifacts. The verifier reports one of four statuses:

- `verified`: all compared counts, hashes, sequence summaries, and report metrics match.
- `mismatch`: replay completed but at least one deterministic artifact diverged.
- `partial`: the run cannot be fully verified yet, such as a run that is not completed or a run with no verification history.
- `failed`: replay execution failed before comparable artifacts were available.

## Hashing approach

`ReplayVerifier` builds stable SHA-256 hashes for:

- event streams
- snapshot streams
- account state streams
- final reports
- sequence summaries
- a combined hash over the individual artifact hashes

Before hashing, objects are serialized with sorted keys and compact JSON separators. Timestamp-like metadata keys such as `timestamp`, `created_at`, `started_at`, `completed_at`, `generated_at`, and `updated_at` are omitted so operational timing does not affect deterministic comparisons. Stream ordering remains significant: two runs with identical events in a different order intentionally hash differently.

## What is compared

Replay verification compares the stored run against a deterministic rerun for:

- total event count
- trade count
- snapshot count
- account state count
- event stream hash
- snapshot stream hash
- account stream hash
- final report hash
- report metric deltas
- sequence-number/step summaries
- first divergent stream step when available

Run diffing compares two persisted runs and returns:

- summary status
- matching and mismatched fields
- first divergence step
- metric deltas
- event, snapshot, account, and report hash comparisons
- timeline divergence summary
- PnL-related divergence summary
- sequence divergence summary

## API usage

Verify a run and persist the latest verification report:

```bash
curl -X POST http://127.0.0.1:8000/runs/<run_id>/verify
```

Fetch the latest stored report, or a `partial` placeholder if verification has not yet been run:

```bash
curl http://127.0.0.1:8000/runs/<run_id>/verification
```

Diff two runs:

```bash
curl -X POST http://127.0.0.1:8000/runs/diff \
  -H 'Content-Type: application/json' \
  -d '{"left_run_id":"<run-a>","right_run_id":"<run-b>"}'
```

## Debugging divergence

1. Check `mismatched_fields` to identify whether divergence started in events, snapshots, account states, reports, sequence summaries, or counts.
2. Check `first_divergence_step` to narrow the inspection window.
3. Use `/runs/{run_id}/timeline` around the divergent step and compare commands, events, snapshots, accounts, and logs.
4. Check `metric_deltas` for report-level numerical drift.
5. If event hashes diverge but counts match, inspect event ordering and public event data shape.
6. If report hashes diverge but stream hashes match, inspect analytics/report generation logic.

## Known limitations

- Verification reruns currently use the API session and backtest execution paths. Runs produced by unsupported future run types return `failed` until a replay executor is added.
- The verifier compares persisted public artifacts, not private engine internals.
- The first divergence step is best-effort because some report-only divergences do not map to a single simulation step.
- Timestamp-like keys are ignored in hashes by design; do not place deterministic business values in timestamp-named fields.
