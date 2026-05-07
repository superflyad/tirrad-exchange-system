from __future__ import annotations

import socket
from typing import Any

from sim.api import main as api_main


def test_demo_payload_is_strict_and_deterministic() -> None:
    payload = api_main._demo_payload(steps=3, symbol=" TES ", seed=7)

    assert payload == {
        "scenario": "calm_market",
        "steps": 3,
        "symbols": ["TES"],
        "seed": 7,
        "initial_price": 100,
        "volatility": 0.02,
        "participants": 6,
        "depth_levels": 3,
        "initial_cash": 1_000_000,
        "mode": "sync",
    }


def test_demo_run_posts_session_and_prints_run_id(monkeypatch: Any, capsys: Any) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, payload))
        return {"run_id": "run-demo-1"}

    monkeypatch.setattr(api_main, "_post_json", fake_post_json)

    result = api_main.main(["demo-run", "--api-url", "http://127.0.0.1:9000/", "--steps", "2"])

    assert result == 0
    assert calls[0][0] == "http://127.0.0.1:9000/sessions/run"
    assert calls[0][1]["steps"] == 2
    output = capsys.readouterr().out
    assert "run_id=run-demo-1" in output
    assert "replay_url=http://127.0.0.1:9000/runs/run-demo-1/replay" in output


def test_select_port_falls_back_when_requested_port_is_busy() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((api_main.DEFAULT_API_HOST, 0))
        busy_port = int(listener.getsockname()[1])
        listener.listen(1)

        selected = api_main._select_port(api_main.DEFAULT_API_HOST, busy_port)

    assert selected > busy_port
