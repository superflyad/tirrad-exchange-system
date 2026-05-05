from __future__ import annotations

import json


def test_python_bindings_expose_fee_config_and_performance_snapshot() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    assert engine.fee_model()["maker_fee_rate"] == 0.0
    assert engine.fee_model()["taker_fee_rate"] == 0.0
    engine.set_fee_model(0.01, 0.02, 1)
    assert engine.fee_model() == {"maker_fee_rate": 0.01, "taker_fee_rate": 0.02, "fixed_fee": 1}

    engine.set_account_state(1, "AAA", 10_000, 10)
    engine.set_account_state(2, "AAA", 10_000, 0)
    engine.place_limit_order("Ask", 100, 10, "GTC", "AAA", account_id=1)
    engine.place_limit_order("Bid", 100, 10, "GTC", "AAA", account_id=2)

    assert engine.latest_account_snapshot(2)["cash_balance"] == 8_979
    perf = engine.performance_snapshot(2)
    assert perf["cash"] == 8_979
    assert perf["positions"]["AAA"] == 10
    assert perf["average_cost"]["AAA"] == 100.0
    assert perf["realized_pnl"] == -21.0
    assert sum(entry["fee_delta"] for entry in engine.account_ledger(2, "AAA")) == 21


def test_backtest_and_session_reports_include_pnl_fields() -> None:
    import tes_engine
    from sim.backtest import BacktestConfig, BacktestRunner
    from sim.session import MarketSessionConfig, MarketSessionRunner
    from sim.tes_strategy.examples import CrossingTakerStrategy

    backtest = BacktestRunner(
        engine=tes_engine.MatchingEngine(),
        config=BacktestConfig(strategy_names=["crossing_taker"], symbols=["DEFAULT"], initial_cash=1_000_000),
        strategies=[CrossingTakerStrategy()],
    ).run()
    backtest_payload = json.loads(backtest.to_json())["metrics"]
    assert "total_fees" in backtest_payload
    assert "realized_pnl" in backtest_payload
    assert "unrealized_pnl" in backtest_payload
    assert "ending_equity" in backtest_payload

    session = MarketSessionRunner(
        MarketSessionConfig(
            scenario="calm_market",
            steps=3,
            symbols=("TES",),
            seed=42,
            initial_price=100,
            volatility=0.02,
            spread_width=1,
            min_order_size=1,
            max_order_size=5,
            probability_market_order=0.4,
            probability_cancel_replace=0.1,
            participant_count=5,
            depth_levels=5,
        )
    ).run()
    session_payload = session.to_dict()["report"]
    assert "final_equity" in session_payload
    assert "per_symbol_pnl" in session_payload
    assert "realized_pnl" in session_payload
    assert "unrealized_pnl" in session_payload
    assert "total_fees" in session_payload
