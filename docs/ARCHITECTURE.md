# TES Architecture

## Design principles

### Event-sourced design
TES is modeled around an event-sourced core: all state transitions are represented as an ordered stream of domain events (order accepted, match executed, cancel acknowledged, risk reject, etc.). Engine state should be reconstructable from event logs without hidden side channels.

### Determinism and golden replay
Determinism is a non-negotiable property. Given the same initial snapshot, inputs, and seeds, TES must produce identical event streams and outputs. Golden replay artifacts are used as canonical references for regression testing and scenario validation.

## Module boundaries

- `engine/`: C++ matching and order-book core, deterministic execution semantics, and replay-safe state transitions.
- `sim/`: Python scenario orchestration, synthetic flow generation, experiment control, and analytics pipelines.
- `api/`: Service layer for run control and data access contracts between simulation outputs and downstream consumers.
- `web/`: Dashboard and observability surfaces for run status, metrics, and event/trade visualization.

## Product posture
TES is analytics-first and explicitly non-HFT. The system optimizes for reproducibility, explainability, and rigorous comparison workflows rather than ultra-low-latency production trading concerns.
