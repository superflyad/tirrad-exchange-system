"""Deterministic replay verification and run diff utilities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

ReplayVerificationStatus = Literal["verified", "mismatch", "partial", "failed"]
RunDiffStatus = Literal["matching", "mismatch", "partial", "failed"]

_TIMESTAMP_KEYS = {
    "timestamp",
    "created_at",
    "started_at",
    "completed_at",
    "generated_at",
    "updated_at",
}
_STREAM_NAMES = ("events", "snapshots", "accounts")


@dataclass(frozen=True)
class EventHashSummary:
    """Stable cross-run hash summary for comparable run artifacts."""

    event_hash: str
    snapshot_hash: str
    account_hash: str
    report_hash: str
    combined_hash: str
    event_count: int
    snapshot_count: int
    account_count: int
    trade_count: int
    sequence_count: int
    sequence_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayVerificationReport:
    """Result of rerunning a stored run and comparing deterministic artifacts."""

    run_id: str
    status: ReplayVerificationStatus
    verified_at: str
    matching_fields: list[str]
    mismatched_fields: list[str]
    message: str
    original_hashes: EventHashSummary
    replay_hashes: EventHashSummary | None
    first_divergence_step: int | None
    metric_deltas: dict[str, float]
    comparisons: dict[str, bool]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["original_hashes"] = self.original_hashes.to_dict()
        payload["replay_hashes"] = (
            self.replay_hashes.to_dict() if self.replay_hashes is not None else None
        )
        return payload


@dataclass(frozen=True)
class RunDiffResult:
    """Comparison result for two persisted runs."""

    left_run_id: str
    right_run_id: str
    status: RunDiffStatus
    generated_at: str
    matching_fields: list[str]
    mismatched_fields: list[str]
    first_divergence_step: int | None
    metric_deltas: dict[str, float]
    event_hash_comparison: dict[str, Any]
    snapshot_hash_comparison: dict[str, Any]
    account_hash_comparison: dict[str, Any]
    report_hash_comparison: dict[str, Any]
    timeline_divergence: dict[str, Any]
    pnl_divergence: dict[str, Any]
    sequence_divergence: dict[str, Any]
    left_hashes: EventHashSummary
    right_hashes: EventHashSummary

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["left_hashes"] = self.left_hashes.to_dict()
        payload["right_hashes"] = self.right_hashes.to_dict()
        return payload


class ReplayVerifier:
    """Verify replay determinism and diff stored run artifact streams."""

    def hash_summary(
        self,
        *,
        events: list[dict[str, Any]],
        snapshots: list[dict[str, Any]],
        accounts: list[dict[str, Any]],
        report: dict[str, Any],
    ) -> EventHashSummary:
        event_hash = hash_stream(events)
        snapshot_hash = hash_stream(snapshots)
        account_hash = hash_stream(accounts)
        report_hash = hash_value(report)
        sequence_hash = hash_value(_sequence_numbers(events, snapshots, accounts))
        trade_count = sum(1 for event in events if event.get("type") == "TradeExecuted")
        combined_hash = hash_value(
            {
                "events": event_hash,
                "snapshots": snapshot_hash,
                "accounts": account_hash,
                "report": report_hash,
                "sequence": sequence_hash,
            }
        )
        return EventHashSummary(
            event_hash=event_hash,
            snapshot_hash=snapshot_hash,
            account_hash=account_hash,
            report_hash=report_hash,
            combined_hash=combined_hash,
            event_count=len(events),
            snapshot_count=len(snapshots),
            account_count=len(accounts),
            trade_count=trade_count,
            sequence_count=len(_sequence_numbers(events, snapshots, accounts)),
            sequence_hash=sequence_hash,
        )

    def verify(
        self,
        *,
        run_id: str,
        original: dict[str, Any],
        replayed: dict[str, Any] | None,
        error: str | None = None,
    ) -> ReplayVerificationReport:
        original_hashes = self.hash_summary(
            events=_list(original.get("events")),
            snapshots=_list(original.get("snapshots")),
            accounts=_list(original.get("accounts")),
            report=_dict(original.get("report")),
        )
        if error is not None or replayed is None:
            return ReplayVerificationReport(
                run_id=run_id,
                status="failed",
                verified_at=_now(),
                matching_fields=[],
                mismatched_fields=["rerun"],
                message="Replay re-execution failed.",
                original_hashes=original_hashes,
                replay_hashes=None,
                first_divergence_step=None,
                metric_deltas={},
                comparisons={"rerun": False},
                error=error,
            )
        replay_hashes = self.hash_summary(
            events=_list(replayed.get("events")),
            snapshots=_list(replayed.get("snapshots")),
            accounts=_list(replayed.get("accounts")),
            report=_dict(replayed.get("report")),
        )
        comparisons = _comparisons(original_hashes, replay_hashes)
        deltas = metric_deltas(
            _dict(original.get("report")), _dict(replayed.get("report"))
        )
        if deltas:
            comparisons["report_metrics"] = False
        matching = sorted(key for key, value in comparisons.items() if value)
        mismatched = sorted(key for key, value in comparisons.items() if not value)
        first_divergence = first_divergence_step(original, replayed)
        status: ReplayVerificationStatus = "verified" if not mismatched else "mismatch"
        return ReplayVerificationReport(
            run_id=run_id,
            status=status,
            verified_at=_now(),
            matching_fields=matching,
            mismatched_fields=mismatched,
            message=(
                "Replay matched stored artifacts."
                if status == "verified"
                else "Replay diverged from stored artifacts."
            ),
            original_hashes=original_hashes,
            replay_hashes=replay_hashes,
            first_divergence_step=first_divergence,
            metric_deltas=deltas,
            comparisons=comparisons,
        )

    def diff_runs(
        self,
        *,
        left_run_id: str,
        right_run_id: str,
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> RunDiffResult:
        left_hashes = self.hash_summary(
            events=_list(left.get("events")),
            snapshots=_list(left.get("snapshots")),
            accounts=_list(left.get("accounts")),
            report=_dict(left.get("report")),
        )
        right_hashes = self.hash_summary(
            events=_list(right.get("events")),
            snapshots=_list(right.get("snapshots")),
            accounts=_list(right.get("accounts")),
            report=_dict(right.get("report")),
        )
        comparisons = _comparisons(left_hashes, right_hashes)
        comparisons["report_metrics"] = not metric_deltas(
            _dict(left.get("report")), _dict(right.get("report"))
        )
        matching = sorted(key for key, value in comparisons.items() if value)
        mismatched = sorted(key for key, value in comparisons.items() if not value)
        event_cmp = _hash_comparison(
            "event_hash", left_hashes.event_hash, right_hashes.event_hash
        )
        snapshot_cmp = _hash_comparison(
            "snapshot_hash", left_hashes.snapshot_hash, right_hashes.snapshot_hash
        )
        account_cmp = _hash_comparison(
            "account_hash", left_hashes.account_hash, right_hashes.account_hash
        )
        report_cmp = _hash_comparison(
            "report_hash", left_hashes.report_hash, right_hashes.report_hash
        )
        divergence = first_divergence_step(left, right)
        return RunDiffResult(
            left_run_id=left_run_id,
            right_run_id=right_run_id,
            status="matching" if not mismatched else "mismatch",
            generated_at=_now(),
            matching_fields=matching,
            mismatched_fields=mismatched,
            first_divergence_step=divergence,
            metric_deltas=metric_deltas(
                _dict(left.get("report")), _dict(right.get("report"))
            ),
            event_hash_comparison=event_cmp,
            snapshot_hash_comparison=snapshot_cmp,
            account_hash_comparison=account_cmp,
            report_hash_comparison=report_cmp,
            timeline_divergence={
                "first_divergence_step": divergence,
                "matches": divergence is None,
            },
            pnl_divergence=_pnl_divergence(
                _dict(left.get("report")),
                _dict(right.get("report")),
                _list(left.get("accounts")),
                _list(right.get("accounts")),
            ),
            sequence_divergence=_sequence_divergence(left_hashes, right_hashes),
            left_hashes=left_hashes,
            right_hashes=right_hashes,
        )


def hash_stream(items: list[dict[str, Any]]) -> str:
    return hash_value([_normalize(item) for item in items])


def hash_value(value: Any) -> str:
    encoded = json.dumps(
        _normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def metric_deltas(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key in sorted(set(left) | set(right)):
        lval = left.get(key)
        rval = right.get(key)
        if isinstance(lval, bool) or isinstance(rval, bool):
            continue
        if isinstance(lval, int | float) and isinstance(rval, int | float):
            delta = float(rval) - float(lval)
            if delta != 0.0:
                deltas[key] = delta
    return deltas


def first_divergence_step(left: dict[str, Any], right: dict[str, Any]) -> int | None:
    for stream in _STREAM_NAMES:
        step = _stream_divergence_step(
            _list(left.get(stream)), _list(right.get(stream))
        )
        if step is not None:
            return step
    if hash_value(_dict(left.get("report"))) != hash_value(_dict(right.get("report"))):
        return None
    return None


def _stream_divergence_step(
    left: list[dict[str, Any]], right: list[dict[str, Any]]
) -> int | None:
    for index, lval in enumerate(left):
        if index >= len(right):
            return _step(lval) or index + 1
        rval = right[index]
        if _normalize(lval) != _normalize(rval):
            return _step(lval) or _step(rval) or index + 1
    if len(right) > len(left):
        return _step(right[len(left)]) or len(left) + 1
    return None


def _comparisons(left: EventHashSummary, right: EventHashSummary) -> dict[str, bool]:
    return {
        "event_count": left.event_count == right.event_count,
        "trade_count": left.trade_count == right.trade_count,
        "snapshot_count": left.snapshot_count == right.snapshot_count,
        "account_count": left.account_count == right.account_count,
        "event_hash": left.event_hash == right.event_hash,
        "snapshot_hash": left.snapshot_hash == right.snapshot_hash,
        "account_hash": left.account_hash == right.account_hash,
        "report_hash": left.report_hash == right.report_hash,
        "sequence_numbers": left.sequence_hash == right.sequence_hash,
    }


def _hash_comparison(name: str, left: str, right: str) -> dict[str, Any]:
    return {"field": name, "left": left, "right": right, "matches": left == right}


def _sequence_divergence(
    left: EventHashSummary, right: EventHashSummary
) -> dict[str, Any]:
    return {
        "left_sequence_count": left.sequence_count,
        "right_sequence_count": right.sequence_count,
        "left_sequence_hash": left.sequence_hash,
        "right_sequence_hash": right.sequence_hash,
        "matches": left.sequence_hash == right.sequence_hash,
    }


def _pnl_divergence(
    left_report: dict[str, Any],
    right_report: dict[str, Any],
    left_accounts: list[dict[str, Any]],
    right_accounts: list[dict[str, Any]],
) -> dict[str, Any]:
    keys = (
        "realized_pnl",
        "unrealized_pnl",
        "ending_equity",
        "final_equity",
        "cash_balance",
    )
    values: dict[str, Any] = {}
    for key in keys:
        if key in left_report or key in right_report:
            lval = left_report.get(key)
            rval = right_report.get(key)
            values[key] = {
                "left": lval,
                "right": rval,
                "delta": (
                    (float(rval) - float(lval))
                    if isinstance(lval, int | float) and isinstance(rval, int | float)
                    else None
                ),
            }
    if left_accounts or right_accounts:
        values["final_account_hash"] = {
            "left": hash_value(left_accounts[-1] if left_accounts else {}),
            "right": hash_value(right_accounts[-1] if right_accounts else {}),
        }
    values["matches"] = all(
        (
            item.get("delta") in (None, 0.0)
            for item in values.values()
            if isinstance(item, dict) and "delta" in item
        )
    )
    return values


def _sequence_numbers(
    events: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stream, items in (
        ("event", events),
        ("snapshot", snapshots),
        ("account", accounts),
    ):
        for index, item in enumerate(items):
            rows.append(
                {
                    "stream": stream,
                    "index": index,
                    "step": _step(item),
                    "type": item.get("type"),
                }
            )
    return rows


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _TIMESTAMP_KEYS
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    return value


def _step(item: dict[str, Any]) -> int | None:
    value = item.get("step")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    data = item.get("data")
    if isinstance(data, dict):
        nested = data.get("step")
        if isinstance(nested, int) and not isinstance(nested, bool):
            return nested
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
