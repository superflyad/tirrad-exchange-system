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


def test_cli_emits_progress(capsys: object) -> None:
    code = main(["sim", "session", "--scenario", "calm_market", "--steps", "12", "--seed", "42", "--progress-interval", "5"])
    assert code == 0
    out = capsys.readouterr().out
    assert "[session] start" in out
    assert "step 5/12" in out
    assert "step 10/12" in out


def test_cli_quiet_suppresses_progress(capsys: object) -> None:
    code = main(["sim", "session", "--scenario", "calm_market", "--steps", "10", "--seed", "42", "--quiet"])
    assert code == 0
    out = capsys.readouterr().out
    assert "[session] start" not in out
    assert "step 10/10" not in out
    assert "[session] complete" in out


def test_cli_verbose_includes_step_detail(capsys: object) -> None:
    code = main(["sim", "session", "--scenario", "calm_market", "--steps", "5", "--seed", "42", "--verbose", "--progress-interval", "5"])
    assert code == 0
    out = capsys.readouterr().out
    assert "[session][detail]" in out


def test_progress_interval_respected(capsys: object) -> None:
    code = main(["sim", "session", "--scenario", "calm_market", "--steps", "21", "--seed", "42", "--progress-interval", "10"])
    assert code == 0
    out = capsys.readouterr().out
    assert "step 10/21" in out
    assert "step 20/21" in out
    assert "step 11/21" not in out


def test_opening_auction_session_scenario_runs() -> None:
    from sim.session.models import MarketSessionConfig
    from sim.session.runner import MarketSessionRunner

    config = MarketSessionConfig(
        scenario="opening_auction",
        steps=2,
        symbols=("TES",),
        seed=7,
        initial_price=100,
        volatility=0.01,
        spread_width=2,
        min_order_size=1,
        max_order_size=2,
        probability_market_order=0.0,
        probability_cancel_replace=0.0,
        participant_count=3,
        depth_levels=3,
    )
    result = MarketSessionRunner(config).run()
    assert result.report.total_steps == 2
    assert result.step_summaries
