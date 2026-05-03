# TES CLI Usage Guide

The `./tes` command is the single entry point for build, validation, and simulation workflows in Tirrad Exchange System (TES).

## Validation commands

### Run the default repository checks

```bash
./tes check
```

Runs the standard project validation flow across configured TES checks.

### Run Python-focused checks

```bash
./tes check python
```

Runs the Python-targeted validation suite.

### Run Python release checks (minimum required for Python-only changes)

```bash
./tes check python-release
```

Runs the Python release-grade validation suite.

## Simulation commands

### Run the demo simulation

```bash
./tes sim demo
```

Runs the built-in deterministic demo simulation and prints the resulting run identifier.

### List available strategies

```bash
./tes sim list-strategies
```

Prints the available strategy names that can be used with `./tes sim run`.

### Run a strategy simulation

```bash
./tes sim run --strategy crossing_taker
```

Runs a deterministic simulation using the `crossing_taker` strategy and returns run output metadata.

### Save a simulation run

```bash
./tes sim save
```

Persists the current simulation output so it can be inspected and replayed later.

### Inspect a saved run

```bash
./tes sim inspect <run_id>
```

Loads a saved run by `run_id` and prints validated run details and event output.

### Replay a saved run

```bash
./tes sim replay <run_id>
```

Replays a previously saved run by `run_id` to reproduce behavior deterministically.
