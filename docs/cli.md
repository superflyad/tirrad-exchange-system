# TES CLI Usage Guide

The `./tes` command is the single entry point for simulation workflows in Tirrad Exchange System (TES).

## Run the demo simulation

```bash
./tes sim demo
```

Runs the built-in deterministic demo simulation and prints the resulting run identifier.

## Save a simulation run

```bash
./tes sim save
```

Persists the current simulation output so it can be inspected and replayed later.

## Inspect a saved run

```bash
./tes sim inspect <run_id>
```

Loads a saved run by `run_id` and prints validated run details and event output.

## Replay a saved run

```bash
./tes sim replay <run_id>
```

Replays a previously saved run by `run_id` to reproduce behavior deterministically.
