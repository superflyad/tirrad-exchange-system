from __future__ import annotations

import pytest

from sim.tes_run import create_deterministic_run_id, create_run_id, validate_run_id


def test_random_run_id_starts_with_prefix() -> None:
    run_id = create_run_id(prefix="sim")

    assert run_id.startswith("sim-")


def test_deterministic_run_id_is_stable() -> None:
    first = create_deterministic_run_id(seed="alpha", prefix="sim")
    second = create_deterministic_run_id(seed="alpha", prefix="sim")

    assert first == second


def test_deterministic_run_id_differs_for_different_seeds() -> None:
    first = create_deterministic_run_id(seed="alpha", prefix="sim")
    second = create_deterministic_run_id(seed="beta", prefix="sim")

    assert first != second


def test_empty_prefix_is_rejected() -> None:
    with pytest.raises(ValueError):
        create_run_id(prefix="")

    with pytest.raises(ValueError):
        create_deterministic_run_id(seed="alpha", prefix="")


def test_empty_run_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_run_id("")
