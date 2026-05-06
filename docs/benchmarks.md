# Engine Benchmarks

Run deterministic engine microbenchmarks:

```bash
./tes bench
```

This builds and runs `tes_engine_bench` from the normal CMake flow while preserving the existing human-readable output.

Scenarios measured:
- cancel same-price first/middle/last order
- cancel many same-price orders
- find many same-price orders
- replace many orders
- partial fills followed by cancels
- multi-symbol mixed add/cancel/replace
- repeated depth/snapshot reads

## Human output

Output format:

```text
<scenario>, operation_count=<N>, elapsed_s=<seconds>, ops_sec=<rate>[, notes=<scenario-parameters>]
```

Sample output:

```text
cancel_same_price_first_middle_last, operation_count=3, elapsed_s=0.000003, ops_sec=1000000.00, notes=same_price_orders=3
cancel_many_same_price_orders, operation_count=40000, elapsed_s=0.012345, ops_sec=3240123.45, notes=price=100
find_many_same_price_orders, operation_count=50000, elapsed_s=0.004210, ops_sec=11876484.56, notes=price=101
```

Benchmarks use fixed symbols and deterministic order generation. Performance results are machine-dependent and should be compared on the same host/profile.

## JSON output

Use `--json` to emit a structured benchmark document instead of the human lines:

```bash
./tes bench --json
```

Write the same structured result to a file with `--output`:

```bash
./tes bench --output runs/benchmarks/latest.json
./tes bench --json --output runs/benchmarks/latest.json
```

The JSON result includes:

- `benchmark_id`
- `created_at`
- `git_sha` when available
- `machine` platform metadata
- per-scenario `name`, `operation_count`, `elapsed_ms`, `ops_per_sec`, `notes`, and `config`
- run-level `config`, including the CMake preset used by `./tes bench`

## SQLite persistence

The API storage layer persists benchmark data in:

- `benchmark_runs` for run metadata
- `benchmark_scenarios` for per-scenario measurements

Storage backends expose:

- `store_benchmark_run`
- `list_benchmark_runs`
- `get_benchmark_run`
- `compare_benchmark_runs`

## API usage

Run and persist a benchmark synchronously:

```bash
curl -X POST http://127.0.0.1:8000/benchmarks/run \
  -H 'Content-Type: application/json' \
  -d '{"threshold_percent": 10.0}'
```

Queue a benchmark job when API queueing is enabled:

```bash
curl -X POST http://127.0.0.1:8000/benchmarks/run \
  -H 'Content-Type: application/json' \
  -d '{"mode": "queued"}'
```

List benchmark runs:

```bash
curl http://127.0.0.1:8000/benchmarks
```

Fetch one run or the latest run:

```bash
curl http://127.0.0.1:8000/benchmarks/<benchmark_id>
curl http://127.0.0.1:8000/benchmarks/latest
```

Compare two runs:

```bash
curl -X POST http://127.0.0.1:8000/benchmarks/compare \
  -H 'Content-Type: application/json' \
  -d '{"baseline_id":"<baseline>","candidate_id":"<candidate>","threshold_percent":10.0}'
```

Check latest regressions:

```bash
curl 'http://127.0.0.1:8000/benchmarks/regressions?threshold_percent=10.0'
```

## Regression threshold

TES compares candidate `ops_per_sec` against baseline `ops_per_sec` per scenario:

```text
percent_delta = ((candidate_ops_per_sec - baseline_ops_per_sec) / baseline_ops_per_sec) * 100
```

A regression is flagged when `percent_delta` is lower than the negative threshold. The default threshold is `10%`, so a scenario is a regression when throughput drops by more than 10%.

Improvements are flagged when throughput increases by more than the same threshold. Missing scenarios are reported with `null` deltas and are not treated as timing regressions.

## Dashboard page

The dashboard includes a `/benchmarks` page with:

- persisted benchmark run list
- latest scenario table
- ops/sec and elapsed time columns
- regression/improvement/stable badges
- latest-vs-baseline regression summary
- a form to compare two benchmark run IDs with a configurable threshold
