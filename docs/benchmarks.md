# Engine Benchmarks

Run deterministic engine microbenchmarks:

```bash
./tes bench
```

This builds and runs `tes_engine_bench` from the normal CMake flow.

Scenarios measured:
- cancel same-price first/middle/last order
- cancel many same-price orders
- find many same-price orders
- replace many orders
- partial fills followed by cancels
- multi-symbol mixed add/cancel/replace
- repeated depth/snapshot reads

Output format:

```
<scenario>, operation_count=<N>, elapsed_s=<seconds>, ops_sec=<rate>[, notes=<scenario-parameters>]
```

Sample output:

```
cancel_same_price_first_middle_last, operation_count=3, elapsed_s=0.000003, ops_sec=1000000.00, notes=same_price_orders=3
cancel_many_same_price_orders, operation_count=40000, elapsed_s=0.012345, ops_sec=3240123.45, notes=price=100
find_many_same_price_orders, operation_count=50000, elapsed_s=0.004210, ops_sec=11876484.56, notes=price=101
```

Benchmarks use fixed symbols and deterministic order generation. Performance results are machine-dependent and should be compared on the same host/profile.
