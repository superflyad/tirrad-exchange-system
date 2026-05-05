from __future__ import annotations

import json
from pathlib import Path

from sim.session import MarketSessionConfig, MarketSessionRunner
from sim.tes_cli.cli import main


def _config(**kwargs: object) -> MarketSessionConfig:
    base = dict(
        scenario="calm_market",
        steps=10,
        symbols=("TES",),
        seed=42,
        initial_price=100,
        volatility=0.02,
        spread_width=1,
        min_order_size=1,
        max_order_size=5,
        probability_market_order=0.4,
        probability_cancel_replace=0.1,
        participant_count=10,
        depth_levels=5,
    )
    base.update(kwargs)
    return MarketSessionConfig(**base)


def test_session_deterministic_seed() -> None:
    a = MarketSessionRunner(_config()).run().report
    b = MarketSessionRunner(_config()).run().report
    assert a == b


def test_session_runs_n_steps() -> None:
    result = MarketSessionRunner(_config(steps=7)).run()
    assert len(result.step_summaries) == 7


def test_calm_market_produces_trades_and_snapshots() -> None:
    result = MarketSessionRunner(_config(steps=12)).run()
    assert result.report.total_trades > 0
    assert len(result.snapshots) == 12


def test_multi_symbol_session_isolates_symbols() -> None:
    result = MarketSessionRunner(_config(symbols=("TES", "ABC"), steps=6)).run()
    assert set(result.report.per_symbol_volume.keys()) == {"TES", "ABC"}
    assert all(t["symbol"] in {"TES", "ABC"} for t in result.trades)


def test_json_export_has_config_report_steps(tmp_path: Path) -> None:
    cfg = _config(steps=5)
    runner = MarketSessionRunner(cfg)
    result = runner.run()
    out = tmp_path / "session.json"
    runner.save_json(result, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "config" in payload and "report" in payload and "steps" in payload


def test_cli_session_smoke(tmp_path: Path) -> None:
    code = main([
        "sim",
        "session",
        "--scenario",
        "calm_market",
        "--steps",
        "5",
        "--seed",
        "42",
        "--output-json",
        str(tmp_path / "run.json"),
    ])
    assert code == 0
