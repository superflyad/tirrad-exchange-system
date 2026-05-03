# TES Strategy Registry

This document describes the currently registered TES strategies and how to discover and run them from the CLI.

## List available strategies

Use the strategy registry listing command:

```bash
./tes sim list-strategies
```

Current registered strategy names:

- `simple_market_maker`
- `crossing_taker`

## Run a strategy by name

Use:

```bash
./tes sim run --strategy <name>
```

Examples:

```bash
./tes sim run --strategy simple_market_maker
./tes sim run --strategy crossing_taker
```

Unknown names are rejected by the strategy loader with a non-zero exit status.

## Registered strategy behavior

### `simple_market_maker`

`simple_market_maker` is a two-sided quoting strategy. It places both a bid and an ask as resting limit orders and provides liquidity to the book. This is a **market maker** pattern: it aims to be passively filled by incoming opposing flow rather than immediately crossing the spread.

### `crossing_taker`

`crossing_taker` is an aggressive execution strategy. It sends orders that cross the spread to trade against existing resting liquidity. This is a **crossing taker** pattern: it consumes liquidity immediately when executable contra-side orders are present.

## Market maker vs crossing taker

At a high level:

- **Market maker (`simple_market_maker`)**: posts resting liquidity on both sides and waits to be matched.
- **Crossing taker (`crossing_taker`)**: submits aggressive orders intended to execute immediately against resting book liquidity.

This distinction is useful when designing deterministic scenarios:

- use market-making behavior to model quoting and passive fills,
- use crossing-taking behavior to model immediate execution and liquidity consumption.
