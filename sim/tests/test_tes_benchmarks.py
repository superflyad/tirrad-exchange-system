from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.storage.in_memory import InMemoryRunStore
from sim.api.storage.sqlite import SQLiteRunStore
from sim.tes_benchmarks.models import BenchmarkRun, BenchmarkScenario, compare_benchmark_runs
from sim.tes_benchmarks.runner import parse_human_output


def _run(benchmark_id: str, ops: float) -> BenchmarkRun:
    return BenchmarkRun.create(
        benchmark_id=benchmark_id,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="abc123",
        machine={"platform": "test"},
        scenarios=[
            BenchmarkScenario(
                name="scenario_a",
                operation_count=100,
                elapsed_ms=100.0,
                ops_per_sec=ops,
                notes="test",
            )
        ],
        config={"preset": "test"},
    )


def test_bench_json_shape_is_stable() -> None:
    scenarios = parse_human_output(
        "scenario_a, operation_count=100, elapsed_s=0.050000, ops_sec=2000.00, notes=sample\n"
    )
    run = BenchmarkRun.create(
        benchmark_id="bench-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="abc123",
        machine={"platform": "test"},
        scenarios=scenarios,
        config={"preset": "debug-ninja"},
    )

    payload = run.to_dict()

    assert set(payload) == {"benchmark_id", "created_at", "git_sha", "machine", "scenarios", "config"}
    assert set(payload["scenarios"][0]) == {
        "name",
        "operation_count",
        "elapsed_ms",
        "ops_per_sec",
        "config",
        "notes",
    }
    assert payload["scenarios"][0]["elapsed_ms"] == 50.0


def test_benchmark_storage_persists_results(tmp_path) -> None:
    store = SQLiteRunStore(tmp_path / "bench.sqlite")
    stored = store.store_benchmark_run(_run("baseline", 1000.0))

    reloaded = store.get_benchmark_run(stored.benchmark_id)

    assert reloaded is not None
    assert reloaded.benchmark_id == "baseline"
    assert reloaded.scenarios[0].ops_per_sec == 1000.0
    assert [run.benchmark_id for run in store.list_benchmark_runs()] == ["baseline"]


def test_comparison_detects_regression() -> None:
    comparison = compare_benchmark_runs(_run("base", 1000.0), _run("candidate", 850.0))

    assert comparison.has_regression is True
    assert comparison.scenarios[0].percent_delta == -15.0
    assert comparison.scenarios[0].regression is True


def test_comparison_detects_improvement() -> None:
    comparison = compare_benchmark_runs(_run("base", 1000.0), _run("candidate", 1150.0))

    assert comparison.has_regression is False
    assert comparison.scenarios[0].improvement is True


def test_api_benchmark_endpoints_work() -> None:
    store = InMemoryRunStore()
    baseline = store.store_benchmark_run(_run("baseline", 1000.0))
    candidate = store.store_benchmark_run(_run("candidate", 850.0))
    client = TestClient(create_app(store))

    list_response = client.get("/benchmarks")
    detail_response = client.get(f"/benchmarks/{baseline.benchmark_id}")
    latest_response = client.get("/benchmarks/latest")
    compare_response = client.post(
        "/benchmarks/compare",
        json={
            "baseline_id": baseline.benchmark_id,
            "candidate_id": candidate.benchmark_id,
            "threshold_percent": 10.0,
        },
    )
    regressions_response = client.get("/benchmarks/regressions")

    assert list_response.status_code == 200
    assert [item["benchmark_id"] for item in list_response.json()] == ["baseline", "candidate"]
    assert detail_response.status_code == 200
    assert detail_response.json()["benchmark_id"] == "baseline"
    assert latest_response.status_code == 200
    assert latest_response.json()["benchmark_id"] == "candidate"
    assert compare_response.status_code == 200
    assert compare_response.json()["has_regression"] is True
    assert regressions_response.status_code == 200
    assert regressions_response.json()["has_regression"] is True


def test_api_queued_benchmark_run_is_trackable() -> None:
    store = InMemoryRunStore()
    client = TestClient(create_app(store, queue_enabled=False))

    response = client.post("/benchmarks/run", json={"mode": "queued", "threshold_percent": 10.0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_type"] == "benchmark"
    assert payload["status"] == "pending"
    assert store.get_run(payload["run_id"]) is not None
