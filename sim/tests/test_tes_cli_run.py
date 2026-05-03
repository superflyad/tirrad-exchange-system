from __future__ import annotations

import argparse

import pytest

from sim.tes_cli.cli import main
from sim.tes_cli.commands.run import handle_run

try:
    import tes_engine

    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_simple_market_maker(capsys: pytest.CaptureFixture[str]) -> None:
    returncode = main(["sim", "run", "--strategy", "simple_market_maker"])

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Strategy: simple_market_maker" in out
    assert "Total Events" in out
    assert "Total Trades" in out


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_unknown_strategy_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    returncode = main(["sim", "run", "--strategy", "unknown"])

    out = capsys.readouterr().out
    assert returncode != 0
    assert "Unknown strategy 'unknown'" in out


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_crossing_taker(capsys: pytest.CaptureFixture[str]) -> None:
    returncode = main(["sim", "run", "--strategy", "crossing_taker"])

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Strategy: crossing_taker" in out
    assert "Total Trades" in out


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_crossing_taker_verbose_output(capsys: pytest.CaptureFixture[str]) -> None:
    returncode = handle_run(argparse.Namespace(strategy="crossing_taker", verbose=True))

    out = capsys.readouterr().out
    assert returncode == 0
    assert "OrderAccepted" in out
    assert "TradeExecuted" in out
    assert "price=100" in out
    assert "qty=5" in out
    assert "Total Traded Qty" in out
    assert "Traded Notional" in out
