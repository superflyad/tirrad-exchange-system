from __future__ import annotations

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.models import SessionRunRequest
from sim.api.services.session_service import run_session
from sim.api.storage.in_memory import InMemoryRunStore
from sim.tes_replay.verification import ReplayVerifier, hash_stream


def _session_payload(seed: int = 42) -> dict[str, object]:
    return {
        "scenario": "calm_market",
        "steps": 5,
        "symbols": ["DEFAULT"],
        "seed": seed,
        "initial_price": 100,
        "volatility": 0.02,
        "participants": 5,
        "depth_levels": 3,
        "initial_cash": 1_000_000,
    }


def test_hash_generation_is_stable_and_ignores_timestamps() -> None:
    events = [
        {
            "type": "OrderAccepted",
            "data": {"order_id": 1, "symbol": "TES"},
            "timestamp": "one",
        }
    ]
    same_events = [
        {
            "timestamp": "two",
            "data": {"symbol": "TES", "order_id": 1},
            "type": "OrderAccepted",
        }
    ]

    assert hash_stream(events) == hash_stream(same_events)


def test_deterministic_replay_verification_passes() -> None:
    store = InMemoryRunStore()
    client = TestClient(create_app(store))
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.post(f"/runs/{created['run_id']}/verify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "verified"
    assert payload["mismatched_fields"] == []
    assert (
        payload["original_hashes"]["combined_hash"]
        == payload["replay_hashes"]["combined_hash"]
    )


def test_modified_stored_run_fails_verification() -> None:
    store = InMemoryRunStore()
    record = store.create_run(run_type="session", config=_session_payload())
    result = run_session(SessionRunRequest(**_session_payload()))
    events = list(result["events"])
    events[0] = {
        "type": events[0]["type"],
        "data": dict(events[0]["data"]) | {"qty": 999},
    }
    stored = store.store_result(
        record.run_id,
        report=result["report"],
        events=events,
        snapshots=result["snapshots"],
        accounts=result["accounts"],
    )
    assert stored is not None
    store.update_run_status(record.run_id, status="completed")
    client = TestClient(create_app(store))

    response = client.post(f"/runs/{record.run_id}/verify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mismatch"
    assert "event_hash" in payload["mismatched_fields"]


def test_diff_identifies_matching_runs() -> None:
    result = run_session(SessionRunRequest(**_session_payload()))
    verifier = ReplayVerifier()

    diff = verifier.diff_runs(
        left_run_id="left", right_run_id="right", left=result, right=result
    )

    assert diff.status == "matching"
    assert diff.mismatched_fields == []
    assert diff.event_hash_comparison["matches"] is True


def test_diff_identifies_mismatched_runs() -> None:
    left = run_session(SessionRunRequest(**_session_payload(seed=42)))
    right = run_session(SessionRunRequest(**_session_payload(seed=43)))
    verifier = ReplayVerifier()

    diff = verifier.diff_runs(
        left_run_id="left", right_run_id="right", left=left, right=right
    )

    assert diff.status == "mismatch"
    assert (
        "event_hash" in diff.mismatched_fields
        or "snapshot_hash" in diff.mismatched_fields
    )


def test_api_verification_and_diff_endpoints_work() -> None:
    client = TestClient(create_app(InMemoryRunStore()))
    left = client.post("/sessions/run", json=_session_payload(seed=42)).json()
    right = client.post("/sessions/run", json=_session_payload(seed=43)).json()

    verify_response = client.post(f"/runs/{left['run_id']}/verify")
    get_response = client.get(f"/runs/{left['run_id']}/verification")
    diff_response = client.post(
        "/runs/diff",
        json={"left_run_id": left["run_id"], "right_run_id": right["run_id"]},
    )

    assert verify_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "verified"
    assert diff_response.status_code == 200
    assert diff_response.json()["status"] == "mismatch"
    assert "event_hash_comparison" in diff_response.json()
