from __future__ import annotations

from argparse import Namespace

import pytest

try:
    import tes_engine

    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

if HAS_ENGINE:
    from sim.tes_cli.commands.run import handle_run


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_simple_market_maker(capsys) -> None:
    returncode = handle_run(Namespace(strategy="simple_market_maker"))

    out = capsys.readouterr().out
    assert returncode == 0
    assert "Strategy: simple_market_maker" in out
    assert "Total Events" in out
    assert "Total Trades" in out


@pytest.mark.skipif(
    not HAS_ENGINE,
    reason="tes_engine extension not available",
)
def test_run_unknown_strategy_returns_error(capsys) -> None:
    returncode = handle_run(Namespace(strategy="unknown"))

    out = capsys.readouterr().out
    assert returncode != 0
    assert "Unknown strategy: unknown" in out
