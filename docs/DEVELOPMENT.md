# Development Notes

## Engine-only bootstrap (Linux/macOS shell)

For early bring-up, build and test only the C++ engine with Python bindings disabled:

```bash
./scripts/build_engine.sh
```

Override defaults when needed:

```bash
TES_BUILD_PYTHON_BINDINGS=ON ./scripts/build_engine.sh engine/build-py
```

## Why this script exists

- Keeps local/CI bootstrap deterministic and minimal.
- Matches the current verified path for environments without Python binding dependencies.
- Avoids platform-specific command drift between Windows and Unix-like shells.
