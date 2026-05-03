# TES Milestone Roadmap

This roadmap captures core Tirrad Exchange System (TES) milestones completed to date and the next milestone targets.

## Current Milestones

- **Build system**: Established `./tes` as the single workflow entry point for reproducible build, test, and contributor operations.
- **C++ engine tests**: Matching-engine behavior is validated with deterministic C++ test coverage to preserve execution semantics.
- **Python bindings**: The pybind11 bridge in `engine/python/bindings.cpp` serves as a strict serialization firewall between engine internals and Python-visible outputs.
- **Strict command/event models**: Python-side command and event model layers enforce exact, validated contracts before execution and at engine-output boundaries.
- **Simulation runner**: Simulation execution runs through strict validated command flows and consumes validated events.
- **Strategy registry**: Strategy integration uses registry-based wiring for explicit, controlled strategy selection and execution.
- **CLI usability**: A unified command-line workflow keeps common project operations discoverable and consistent for contributors.

## Next Milestones

- **Market depth support**: Extend engine and Python-visible outputs for depth-oriented workflows while preserving deterministic behavior and strict public contracts.
- **Verbose evidence output**: Add richer execution evidence and trace artifacts suitable for repeatable analysis without leaking implementation-only internals.
- **Benchmarks**: Introduce standardized performance benchmarks for engine and simulation paths with repeatable measurement workflows.
