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

    def _progress(update: dict[str, object]) -> None:
        mids = ", ".join([f"{k}={v:.2f}" for k, v in sorted(update["latest_mid"].items())])
        print(
            f"[session] step {update['step']}/{update['total_steps']} symbols={','.join(update['symbols'])} "
            f"orders={update['total_orders']} trades={update['total_trades']} rejected={update['rejected_orders']} mids=[{mids}]"
        )
        if args.verbose and update["detail"] is not None:
            for item in update["detail"]:
                print(
                    f"[session][detail] step={item['step']} symbol={item['symbol']} events={item['events']} trades={item['trades']} volume={item['volume']}"
                )

    if not args.quiet:
        print(
            f"[session] start scenario={config.scenario} steps={config.steps} symbols={','.join(config.symbols)} "
            f"seed={config.seed} participants={config.participant_count}"
        )

    result = runner.run(
        progress_interval=max(1, args.progress_interval),
        progress_callback=None if args.quiet else _progress,
        verbose=args.verbose,
    )
    if args.output_json:
        runner.save_json(result, args.output_json)
    print(
        f"[session] complete steps={result.report.total_steps} orders={result.report.total_orders} "
        f"trades={result.report.total_trades} volume={result.report.total_volume} rejected={result.report.rejected_orders}"
    )
    if args.output_json:
        print(f"[session] json={args.output_json}")
    print(json.dumps(result.report.__dict__, indent=2, sort_keys=True))
    return 0
