from __future__ import annotations

from fastapi.testclient import TestClient

from sim.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _session_payload() -> dict[str, object]:
    return {
        "scenario": "calm_market",
        "steps": 5,
        "symbols": ["DEFAULT"],
        "seed": 42,
        "initial_price": 100,
        "volatility": 0.02,
        "participants": 5,
        "depth_levels": 3,
        "initial_cash": 1_000_000,
    }


def _backtest_payload() -> dict[str, object]:
    return {
        "strategy": "crossing_taker",
        "symbols": ["DEFAULT"],
        "initial_cash": 1_000_000,
        "depth_levels": 3,
    }


def test_health_endpoint_works() -> None:
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "tes-api"}


def test_run_session_endpoint_works() -> None:
    response = _client().post("/sessions/run", json=_session_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_type"] == "session"
    assert payload["status"] == "completed"
    assert payload["report"]["total_steps"] == 5
    assert payload["report_summary"]["total_steps"] == 5


def test_run_backtest_endpoint_works() -> None:
    response = _client().post("/backtests/run", json=_backtest_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_type"] == "backtest"
    assert payload["status"] == "completed"
    assert payload["report"]["total_orders"] >= 2
    assert payload["report_summary"]["total_trades"] >= 1


def test_list_runs_returns_created_runs() -> None:
    client = _client()
    session = client.post("/sessions/run", json=_session_payload()).json()
    backtest = client.post("/backtests/run", json=_backtest_payload()).json()

    response = client.get("/runs")

    assert response.status_code == 200
    run_ids = {item["run_id"] for item in response.json()}
    assert {session["run_id"], backtest["run_id"]} <= run_ids


def test_get_run_by_id_works() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.get(f"/runs/{created['run_id']}")

    assert response.status_code == 200
    assert response.json()["run_id"] == created["run_id"]
    assert response.json()["report"]["total_steps"] == 5


def test_get_report_works() -> None:
    client = _client()
    created = client.post("/backtests/run", json=_backtest_payload()).json()

    response = client.get(f"/runs/{created['run_id']}/report")

    assert response.status_code == 200
    assert response.json()["report"]["total_orders"] >= 2


def test_get_events_works() -> None:
    client = _client()
    created = client.post("/backtests/run", json=_backtest_payload()).json()

    response = client.get(f"/runs/{created['run_id']}/events")

    assert response.status_code == 200
    events = response.json()["events"]
    assert events
    assert set(events[0].keys()) == {"type", "data"}


def test_get_snapshots_works() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.get(f"/runs/{created['run_id']}/snapshots")

    assert response.status_code == 200
    assert response.json()["snapshots"]


def test_get_accounts_works() -> None:
    client = _client()
    created = client.post("/backtests/run", json=_backtest_payload()).json()

    response = client.get(f"/runs/{created['run_id']}/accounts")

    assert response.status_code == 200
    assert response.json()["accounts"]


def test_delete_run_works() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    delete_response = client.delete(f"/runs/{created['run_id']}")
    get_response = client.get(f"/runs/{created['run_id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_missing_run_returns_404() -> None:
    response = _client().get("/runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_invalid_scenario_returns_clean_error() -> None:
    payload = _session_payload() | {"scenario": "nope"}

    response = _client().post("/sessions/run", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_invalid_strategy_returns_clean_error() -> None:
    payload = _backtest_payload() | {"strategy": "nope"}

    response = _client().post("/backtests/run", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_request_validation_returns_clean_error() -> None:
    payload = _session_payload() | {"steps": True}

    response = _client().post("/sessions/run", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
