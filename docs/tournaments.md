# Strategy Tournaments and Parameter Sweeps

TES tournaments run many deterministic child sessions or backtests from one parent configuration. The API persists tournament metadata, child run links, and aggregate reports in the same SQLite database used for run storage.

## Tournament types

- `strategy_vs_strategy`: creates one backtest child per strategy and seed.
- `strategy_vs_scenario`: creates session children across strategies, scenarios, seeds, participant counts, and volatility values.
- `parameter_sweep`: creates backtest children for the Cartesian product of strategy parameter values and seeds. Parameter values are persisted as tournament dimensions so reports and dashboard filters can compare them.
- `multi_symbol_sweep`: creates backtest children for each individual symbol and for the combined symbol basket.

## API examples

Create a parameter sweep:

```bash
curl -X POST http://localhost:8000/tournaments/run \
  -H 'content-type: application/json' \
  -d '{
    "tournament_type": "parameter_sweep",
    "strategies": ["crossing_taker"],
    "symbols": ["TES"],
    "seeds": [1, 2],
    "initial_cash": 1000000,
    "strategy_parameters": {
      "size": [1, 2],
      "offset": [0.1, 0.2]
    }
  }'
```

Inspect tournament state and reports:

```bash
curl http://localhost:8000/tournaments
curl http://localhost:8000/tournaments/<tournament_id>
curl http://localhost:8000/tournaments/<tournament_id>/children
curl http://localhost:8000/tournaments/<tournament_id>/report
```

Cancel a tournament and any pending children:

```bash
curl -X POST http://localhost:8000/tournaments/<tournament_id>/cancel
```

## Execution model

Tournament creation expands the parent config into stable child keys, creates child run records, links them to the parent, and enqueues the child run IDs when the durable queue is enabled. Workers execute the normal session/backtest run records, then refresh the parent aggregate report after child completion.

The aggregate report ranks completed child runs and records failed or canceled children separately. A failed child does not fail report generation for the whole tournament.

## Ranking metrics

Reports include these comparable metrics when the child run report exposes enough data:

- ending equity
- total PnL
- simple return/stability metric from the equity curve
- max drawdown from the equity curve
- total volume
- fill ratio
- rejection rate
- final position exposure

## Dashboard usage

Open `/tournaments` in the React dashboard to see persisted tournament parents. Open a tournament detail page to view leaderboard rankings, child run links, child dimensions, and parent configuration. Child run links open the existing run detail pages for timeline, events, snapshots, accounts, and logs.
