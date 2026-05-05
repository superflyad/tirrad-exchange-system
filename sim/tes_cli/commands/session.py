from __future__ import annotations

import json

from sim.session import MarketSessionConfig, MarketSessionRunner


def handle_session(args: object) -> int:
    symbols = tuple([s.strip() for s in args.symbols.split(",") if s.strip()])
    config = MarketSessionConfig(
        scenario=args.scenario,
        steps=args.steps,
        symbols=symbols,
        seed=args.seed,
        initial_price=args.initial_price,
        volatility=args.volatility,
        spread_width=max(1, int(round(args.initial_price * 0.001))),
        min_order_size=1,
        max_order_size=10,
        probability_market_order=0.35,
        probability_cancel_replace=0.1,
        participant_count=args.participants,
        depth_levels=args.depth_levels,
    )
    runner = MarketSessionRunner(config)
    result = runner.run()
    if args.output_json:
        runner.save_json(result, args.output_json)
    print(json.dumps(result.report.__dict__, indent=2, sort_keys=True))
    return 0
