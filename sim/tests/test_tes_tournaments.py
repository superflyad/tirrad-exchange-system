from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.models import TournamentConfig
from sim.api.storage.in_memory import InMemoryRunStore
from sim.api.tournaments import build_report, expand_tournament


def test_parameter_sweep_expands_expected_child_runs() -> None:
    config = TournamentConfig(
        tournament_type="parameter_sweep",
        strategies=["crossing_taker"],
        symbols=["TES"],
        seeds=[1, 2],
        strategy_parameters={"size": [1, 2], "offset": [0.1, 0.2]},
    )

    specs = expand_tournament(config)

    assert len(specs) == 8
    assert specs[0].run_type == "backtest"
    assert specs == sorted(specs, key=lambda item: item.child_key)
    assert {spec.dimensions["strategy"] for spec in specs} == {"crossing_taker"}


def test_tournament_persists_metadata_and_links_children() -> None:
    store = InMemoryRunStore()
    client = TestClient(create_app(store, queue_enabled=False))

    response = client.post(
        "/tournaments/run",
        json={
            "tournament_type": "multi_symbol_sweep",
            "strategies": ["crossing_taker"],
            "symbols": ["A", "B"],
            "seeds": [7],
        },
    )

    assert response.status_code == 200
    tournament = response.json()
    assert tournament["status"] == "running"
    assert tournament["child_count"] == 3
    stored = store.get_tournament(tournament["tournament_id"])
    assert stored is not None
    children = store.list_tournament_children(tournament["tournament_id"])
    assert children is not None
    assert len(children) == 3
    assert all(child["child_run_id"] for child in children)


def test_aggregation_ranks_results_and_keeps_failures() -> None:
    store = InMemoryRunStore()
    tournament = store.create_tournament(
        tournament_type="strategy_vs_strategy",
        config={"tournament_type": "strategy_vs_strategy"},
    )
    good = store.create_run(run_type="backtest", config={"initial_cash": 100})
    better = store.create_run(run_type="backtest", config={"initial_cash": 100})
    failed = store.create_run(run_type="backtest", config={"initial_cash": 100})
    store.link_tournament_child(tournament.tournament_id, child_run_id=good.run_id, child_key="a", run_type="backtest", dimensions={"strategy": "a"})
    store.link_tournament_child(tournament.tournament_id, child_run_id=better.run_id, child_key="b", run_type="backtest", dimensions={"strategy": "b"})
    store.link_tournament_child(tournament.tournament_id, child_run_id=failed.run_id, child_key="c", run_type="backtest", dimensions={"strategy": "c"})
    store.store_result(good.run_id, report={"starting_equity": 100, "ending_equity": 105, "total_orders": 2, "fill_ratio": 1.0}, events=[], snapshots=[], accounts=[])
    store.store_result(better.run_id, report={"starting_equity": 100, "ending_equity": 110, "total_orders": 2, "fill_ratio": 1.0}, events=[], snapshots=[], accounts=[])
    store.update_run(good.run_id, status="completed", completed_at=datetime.now(UTC))
    store.update_run(better.run_id, status="completed", completed_at=datetime.now(UTC))
    store.update_run(failed.run_id, status="failed", completed_at=datetime.now(UTC), error="boom")

    report = build_report(
        tournament.tournament_id,
        store.list_tournament_children(tournament.tournament_id) or [],
        [store.get_run(good.run_id), store.get_run(better.run_id), store.get_run(failed.run_id)],
    )

    assert report["status"] == "completed"
    assert report["results"][0]["child_run_id"] == better.run_id
    assert report["results"][0]["rank"] == 1
    assert report["failed_child_count"] == 1
    assert report["failures"][0]["error"] == "boom"


def test_api_tournament_endpoints_work() -> None:
    client = TestClient(create_app(InMemoryRunStore(), queue_enabled=False))
    created = client.post(
        "/tournaments/run",
        json={
            "tournament_type": "strategy_vs_scenario",
            "strategies": ["liquidity"],
            "scenarios": ["calm_market"],
            "symbols": ["DEFAULT"],
            "seeds": [42],
            "steps": 3,
            "participant_counts": [3],
            "volatility_ranges": [0.02],
        },
    )
    assert created.status_code == 200
    tournament_id = created.json()["tournament_id"]

    assert client.get("/tournaments").status_code == 200
    assert client.get(f"/tournaments/{tournament_id}").status_code == 200
    children = client.get(f"/tournaments/{tournament_id}/children")
    assert children.status_code == 200
    assert len(children.json()["children"]) == 1
    report = client.get(f"/tournaments/{tournament_id}/report")
    assert report.status_code == 200
    assert report.json()["child_count"] == 1
    canceled = client.post(f"/tournaments/{tournament_id}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"


def test_sqlite_tournament_metadata_reloads(tmp_path) -> None:
    from sim.api.storage.sqlite import SQLiteRunStore

    db_path = tmp_path / "tes.sqlite"
    store = SQLiteRunStore(db_path)
    tournament = store.create_tournament(
        tournament_type="parameter_sweep",
        config={"tournament_type": "parameter_sweep", "strategies": ["crossing_taker"]},
    )
    child = store.create_run(run_type="backtest", config={"strategy": "crossing_taker", "symbols": ["TES"]})
    store.link_tournament_child(
        tournament.tournament_id,
        child_run_id=child.run_id,
        child_key="strategy=crossing_taker",
        run_type="backtest",
        dimensions={"strategy": "crossing_taker"},
    )
    store.close()

    reloaded = SQLiteRunStore(db_path)
    stored = reloaded.get_tournament(tournament.tournament_id)
    children = reloaded.list_tournament_children(tournament.tournament_id)

    assert stored is not None
    assert stored.config["strategies"] == ["crossing_taker"]
    assert children is not None
    assert children[0]["child_run_id"] == child.run_id
