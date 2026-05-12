from __future__ import annotations

from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.api.storage.in_memory import InMemoryRunStore


def _client() -> TestClient:
    return TestClient(create_app(InMemoryRunStore()))


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
    runs = response.json()
    run_ids = {item["run_id"] for item in runs}
    assert {session["run_id"], backtest["run_id"]} <= run_ids
    session_summary = next(item for item in runs if item["run_id"] == session["run_id"])
    assert {
        "run_id",
        "scenario",
        "strategy",
        "created_at",
        "step_count",
        "trade_count",
        "rejection_count",
        "status",
    } <= set(session_summary)
    assert session_summary["scenario"] == "calm_market"
    assert session_summary["step_count"] == 5


def test_get_run_by_id_works() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.get(f"/runs/{created['run_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == created["run_id"]
    assert payload["report"]["total_steps"] == 5
    assert payload["scenario"] == "calm_market"
    assert payload["step_count"] == 5
    assert payload["trade_count"] >= 0
    assert payload["rejection_count"] >= 0


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


def _client_with_inspectable_run() -> tuple[TestClient, str]:
    store = InMemoryRunStore()
    record = store.create_run(run_type="backtest", config={"strategy": "demo", "symbols": ["TES"]})
    stored = store.store_result(
        record.run_id,
        report={
            "total_orders": 2,
            "total_trades": 1,
            "total_volume": 5,
            "traded_notional": 505,
            "rejected_orders": 1,
            "final_positions": {"TES": 5},
        },
        events=[
            {"type": "OrderAccepted", "data": {"order_id": 101, "symbol": "TES", "qty": 5, "price": 100, "step": 1}},
            {
                "type": "TradeExecuted",
                "data": {"maker_order_id": 101, "taker_order_id": 202, "symbol": "TES", "qty": 5, "price": 101, "step": 2},
            },
            {"type": "OrderRejected", "data": {"symbol": "ALT", "qty": 1, "price": 99, "reason": "NoLiquidity", "step": 3}},
        ],
        snapshots=[
            {"step": 1, "symbols": {"TES": {"bid": 100, "ask": 102}}},
            {"step": 2, "symbols": {"TES": {"bid": 101, "ask": 103}}},
        ],
        accounts=[
            {"account_id": "acct-1", "step": 2, "positions": {"TES": 5}, "mark_to_market": {"TES": 510}}
        ],
        logs=[{"level": "info", "message": "done", "step": 3}],
    )
    assert stored is not None
    store.update_run_status(record.run_id, status="completed")
    return TestClient(create_app(store)), record.run_id


def test_run_timeline_endpoint_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/timeline")

    assert response.status_code == 200
    timeline = response.json()["timeline"]
    assert {"step", "timestamp", "sequence", "symbol", "category", "type", "summary", "payload"} <= set(timeline[0])
    assert {entry["category"] for entry in timeline} >= {"event", "snapshot", "account", "log"}


def test_run_timeline_pagination_works() -> None:
    client, run_id = _client_with_inspectable_run()

    first = client.get(f"/runs/{run_id}/timeline?limit=1").json()["timeline"]
    second = client.get(f"/runs/{run_id}/timeline?limit=1&offset=1").json()["timeline"]

    assert len(first) == 1
    assert len(second) == 1
    assert first[0] != second[0]


def test_run_timeline_symbol_filter_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/timeline?symbol=TES")

    assert response.status_code == 200
    timeline = response.json()["timeline"]
    assert timeline
    assert all(entry["symbol"] == "TES" or "TES" in str(entry["payload"]) for entry in timeline)


def test_run_timeline_category_filter_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/timeline?category=event")

    assert response.status_code == 200
    assert {entry["category"] for entry in response.json()["timeline"]} == {"event"}


def test_run_order_timeline_works_for_order_ids_in_events() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/orders/101/timeline")

    assert response.status_code == 200
    timeline = response.json()["timeline"]
    assert [entry["type"] for entry in timeline] == ["OrderAccepted", "TradeExecuted"]


def test_run_account_timeline_works_for_account_payloads() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/accounts/acct-1/timeline")

    assert response.status_code == 200
    timeline = response.json()["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["category"] == "account"


def test_run_replay_endpoint_returns_valid_status() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.post(f"/runs/{run_id}/replay")

    assert response.status_code == 200
    assert response.json()["status"] in {"replayed", "reconstructed", "unavailable", "mismatch"}


def test_run_summary_endpoint_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["run_id"] == run_id
    assert summary["symbols"] == ["ALT", "TES"]
    assert summary["total_events"] == 3
    assert summary["total_trades"] == 1
    assert summary["final_positions"] == {"TES": 5}


def test_missing_run_timeline_returns_404() -> None:
    response = _client().get("/runs/missing/timeline")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def _sse_payloads(text: str) -> list[dict[str, object]]:
    import json

    payloads: list[dict[str, object]] = []
    for block in text.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                payloads.append(json.loads(line.removeprefix("data: ")))
    return payloads


def test_stream_endpoint_exists_for_completed_run() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    response = client.get(f"/runs/{created['run_id']}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_missing_run_stream_returns_404() -> None:
    response = _client().get("/runs/missing/stream")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_session_run_publishes_progress_messages() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload() | {"progress_interval": 2}).json()

    response = client.get(f"/runs/{created['run_id']}/stream")

    assert response.status_code == 200
    messages = _sse_payloads(response.text)
    progress = [message for message in messages if message["category"] == "progress"]
    assert progress
    assert progress[0]["payload"]["total_orders"] >= 0  # type: ignore[index]


def test_completed_run_stream_emits_completion_message() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload()).json()

    messages = _sse_payloads(client.get(f"/runs/{created['run_id']}/stream").text)

    completed = [message for message in messages if message["category"] == "completed"]
    assert completed
    assert completed[-1]["type"] == "run_completed"


def test_quiet_stream_mode_does_not_log_every_event_or_snapshot() -> None:
    client = _client()
    created = client.post("/sessions/run", json=_session_payload() | {"progress_interval": 10}).json()

    logs = client.get(f"/runs/{created['run_id']}/logs").json()["logs"]
    categories = [log.get("category") for log in logs]

    assert "event" not in categories
    assert "snapshot" not in categories
    assert categories.count("progress") <= 2


def test_replay_get_endpoint_returns_timeline_frame_and_events() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/replay")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["event_count"] == 3
    assert all(set(event) == {"type", "data"} for event in payload["events"])
    assert set(payload["cursor"]) == {"step", "state", "speed"}
    assert {"step", "trades", "snapshots", "top_of_book", "account_deltas", "market_metrics", "event_summaries"} <= set(payload["frame"])


def test_replay_get_missing_run_returns_404() -> None:
    response = _client().get("/runs/missing/replay")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_replay_get_malformed_event_returns_validation_error() -> None:
    store = InMemoryRunStore()
    record = store.create_run(run_type="session", config={"scenario": "demo", "symbols": ["TES"]})
    stored = store.store_result(
        record.run_id,
        report={"total_steps": 1},
        events=[{"type": "TradeExecuted", "data": {}, "debug": "leak"}],
        snapshots=[],
        accounts=[],
    )
    assert stored is not None
    client = TestClient(create_app(store))

    response = client.get(f"/runs/{record.run_id}/replay")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "replay_validation_error"


def test_replay_frame_retrieval_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/replay/frame/2?symbol=TES")

    assert response.status_code == 200
    frame = response.json()
    assert frame["step"] == 2
    assert frame["symbol"] == "TES"
    assert frame["trades"]
    assert frame["top_of_book"]["TES"]["spread"] == 2


def test_replay_range_filtering_works() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(
        f"/runs/{run_id}/replay/range?start_step=1&end_step=3&symbol=TES&include_snapshots=false&include_accounts=false"
    )

    assert response.status_code == 200
    payload = response.json()
    assert [frame["step"] for frame in payload["frames"]] == [1, 2]
    assert all(frame["snapshots"] == [] for frame in payload["frames"])
    assert all(frame["accounts"] == [] for frame in payload["frames"])
    assert payload["frames"][1]["trades"][0]["symbol"] == "TES"


def test_replay_summary_shape_is_stable() -> None:
    client, run_id = _client_with_inspectable_run()

    response = client.get(f"/runs/{run_id}/replay/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"] == ["ALT", "TES"]
    assert payload["total_events"] == 3
    assert payload["total_trades"] == 1
    assert "TradeExecuted" in payload["available_event_types"]
