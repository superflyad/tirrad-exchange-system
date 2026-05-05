# Engine Benchmarks

Run deterministic engine microbenchmarks:

```bash
./tes bench
```

This builds and runs `tes_engine_bench` from the normal CMake flow.

Scenarios measured:
- add many resting limit orders
- sweep one price level
- sweep many price levels
- cancel many orders
- replace many orders
- multi-symbol mixed order flow
- repeated depth/snapshot reads

Output format:

```
<scenario>, operation_count=<N>, elapsed_s=<seconds>, ops_sec=<rate>
```

Benchmarks use fixed symbols and deterministic order generation. Performance results are machine-dependent and should be compared on the same host/profile.
