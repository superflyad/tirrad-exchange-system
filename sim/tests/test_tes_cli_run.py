from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from sim.tes_cli.cli import main
from sim.tes_cli.commands import run as run_command
from sim.tes_cli.commands.run import handle_run

try:
    import tes_engine

    HAS_ENGINE = True
    HAS_DEPTH = hasattr(tes_engine.MatchingEngine(), "depth")
except ImportError:
    HAS_ENGINE = False
    HAS_DEPTH = False


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
    returncode = main(["sim", "run", "--strategy", "crossing_taker", "--verbose"])

    out = capsys.readouterr().out
    assert returncode == 0
    assert "TES Strategy Run" in out
    assert "OrderAccepted" in out
    assert "TradeExecuted" in out
    assert "Total Traded Qty" in out
    assert "Traded Notional" in out
    assert ("Book Depth" in out) or ("<unavailable>" in out)


@pytest.mark.skipif(
    not (HAS_ENGINE and HAS_DEPTH),
    reason="tes_engine depth not available",
)
def test_run_crossing_taker_verbose_output_shows_book_depth(
    capsys: pytest.CaptureFixture[str],
) -> None:
    returncode = handle_run(
        argparse.Namespace(strategy="crossing_taker", verbose=True, depth_levels=5)
    )

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Book Depth" in out
    assert "Bids:" in out
    assert "price=100 qty=5" in out


@pytest.mark.skipif(
    not (HAS_ENGINE and HAS_DEPTH),
    reason="tes_engine depth not available",
)
def test_run_crossing_taker_verbose_output_depth_levels_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    returncode = handle_run(
        argparse.Namespace(strategy="crossing_taker", verbose=True, depth_levels=0)
    )

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Bids: <empty>" in out
    assert "Asks: <empty>" in out


def test_run_verbose_invalid_depth_levels_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    returncode = handle_run(
        argparse.Namespace(strategy="crossing_taker", verbose=True, depth_levels=-1)
    )

    out = capsys.readouterr().out
    assert returncode != 0
    assert "--depth-levels must be >= 0" in out


def test_run_verbose_book_depth_unavailable_when_missing_depth(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubStrategy:
        def on_start(self) -> list[object]:
            return []

        def on_event(self, _event: object) -> list[object]:
            return []

    class EngineWithoutDepth:
        pass

    monkeypatch.setattr(run_command, "get_strategy", lambda _name: StubStrategy())
    monkeypatch.setattr(
        run_command,
        "import_module",
        lambda _name: SimpleNamespace(MatchingEngine=EngineWithoutDepth),
    )

    returncode = handle_run(argparse.Namespace(strategy="fake", verbose=True, depth_levels=5))

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Book Depth" in out
    assert "<unavailable>" in out
