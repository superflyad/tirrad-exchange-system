"""Replay and inspection service for persisted TES API runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sim.api.errors import RunNotFoundError
from sim.api.models import (
    BacktestRunRequest,
    ReplayVerificationReportModel,
    RunDiffRequest,
    RunDiffResultModel,
    ReplayFrame,
    ReplayRangeResponse,
    ReplaySessionResponse,
    ReplaySummaryResponse,
    ReplayTimelineModel,
    ReplayCursorModel,
    RunInspectionSummary,
    RunReplayResponse,
    SessionRunRequest,
    TimelineEntry,
)
from sim.api.storage import RunRecord, RunStore
from sim.api.services.backtest_service import run_backtest
from sim.api.services.session_service import run_session
from sim.tes_replay.playback import ReplayPlaybackController, ReplayTimeline
from sim.tes_replay.verification import ReplayVerifier

TimelineCategory = Literal["command", "event", "snapshot", "account", "log"]
ReplayStatus = Literal["replayed", "reconstructed", "unavailable", "mismatch"]

_CATEGORY_ORDER: dict[str, int] = {
    "command": 0,
    "event": 1,
    "snapshot": 2,
    "account": 3,
    "log": 4,
}
_ORDER_ID_KEYS = {
    "order_id",
    "maker_order_id",
    "taker_order_id",
    "resulting_order_id",
    "resting_order_id",
}


@dataclass(frozen=True)
class _RunArtifacts:
    record: RunRecord
    report: dict[str, Any]
    events: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    accounts: list[dict[str, Any]]
    logs: list[dict[str, Any]]


class ReplayService:
    """Build read-only run timelines, summaries, and replay status from stored artifacts."""

    def __init__(self, store: RunStore) -> None:
        self._store = store
        self._verifier = ReplayVerifier()

    def load_run(self, run_id: str) -> _RunArtifacts:
        record = self._store.get_run(run_id)
        if record is None:
            raise RunNotFoundError(run_id)
        report = self._store.get_report(run_id)
        events = self._store.get_events(run_id)
        snapshots = self._store.get_snapshots(run_id)
        accounts = self._store.get_accounts(run_id)
        logs = self._store.get_logs(run_id)
        if report is None or events is None or snapshots is None or accounts is None or logs is None:
            raise RunNotFoundError(run_id)
        return _RunArtifacts(
            record=record,
            report=report,
            events=events,
            snapshots=snapshots,
            accounts=accounts,
            logs=logs,
        )

    def replay_run(self, run_id: str) -> RunReplayResponse:
        artifacts = self.load_run(run_id)
        events = artifacts.events
        snapshots = artifacts.snapshots
        accounts = artifacts.accounts
        logs = artifacts.logs
        if not events and not snapshots and not accounts and not logs:
            status: ReplayStatus = "unavailable"
            message = "No persisted artifacts are available for read-only reconstruction."
        else:
            status = "reconstructed"
            message = "Run was reconstructed from persisted artifacts; engine re-execution is unavailable."
        return RunReplayResponse(
            run_id=run_id,
            status=status,
            message=message,
            total_events=len(events),
            total_snapshots=len(snapshots),
            total_accounts=len(accounts),
            total_logs=len(logs),
            event_count_matches=True,
            event_hash_matches=None,
        )

    def verify_run(self, run_id: str) -> ReplayVerificationReportModel:
        artifacts = self.load_run(run_id)
        original = _artifact_payload(artifacts)
        replayed: dict[str, Any] | None = None
        error: str | None = None
        if artifacts.record.status != "completed":
            report = self._verifier.verify(
                run_id=run_id,
                original=original,
                replayed=None,
                error="only completed runs can be replay verified",
            )
            payload = report.to_dict() | {
                "status": "partial",
                "message": "Run is not completed; replay verification is partial.",
            }
            self._store.store_verification(run_id, payload)
            return ReplayVerificationReportModel(**payload)
        try:
            if artifacts.record.run_type == "session":
                request = SessionRunRequest(**artifacts.record.config)
                replayed = run_session(request)
            elif artifacts.record.run_type == "backtest":
                request = BacktestRunRequest(**artifacts.record.config)
                replayed = run_backtest(request)
            else:
                error = f"unsupported run type: {artifacts.record.run_type}"
        except Exception as exc:  # deterministic verification must report failures, not leak exceptions
            error = str(exc) or exc.__class__.__name__
        report = self._verifier.verify(
            run_id=run_id, original=original, replayed=replayed, error=error
        )
        payload = report.to_dict()
        self._store.store_verification(run_id, payload)
        return ReplayVerificationReportModel(**payload)

    def get_verification(self, run_id: str) -> ReplayVerificationReportModel:
        if self._store.get_run(run_id) is None:
            raise RunNotFoundError(run_id)
        payload = self._store.get_verification(run_id)
        if not payload:
            artifacts = self.load_run(run_id)
            original = _artifact_payload(artifacts)
            report = self._verifier.verify(
                run_id=run_id,
                original=original,
                replayed=None,
                error="verification has not been run",
            )
            payload = report.to_dict() | {
                "status": "partial",
                "message": "Verification has not been run for this run.",
            }
        return ReplayVerificationReportModel(**payload)

    def diff_runs(self, request: RunDiffRequest) -> RunDiffResultModel:
        left = self.load_run(request.left_run_id)
        right = self.load_run(request.right_run_id)
        result = self._verifier.diff_runs(
            left_run_id=request.left_run_id,
            right_run_id=request.right_run_id,
            left=_artifact_payload(left),
            right=_artifact_payload(right),
        )
        return RunDiffResultModel(**result.to_dict())

    def summarize_run(self, run_id: str) -> RunInspectionSummary:
        artifacts = self.load_run(run_id)
        report = artifacts.report
        events = artifacts.events
        snapshots = artifacts.snapshots
        accounts = artifacts.accounts
        symbols = sorted(_symbols_from_artifacts(artifacts))
        total_volume = _report_int(report, "total_volume")
        if total_volume is None:
            total_volume = sum(_int_value(_event_data(event).get("qty")) or 0 for event in events if event.get("type") == "TradeExecuted")
        traded_notional = _report_int(report, "traded_notional")
        if traded_notional is None:
            traded_notional = sum(
                (_int_value(data.get("price")) or 0) * (_int_value(data.get("qty")) or 0)
                for event in events
                if event.get("type") == "TradeExecuted"
                for data in [_event_data(event)]
            )
        return RunInspectionSummary(
            run_id=artifacts.record.run_id,
            run_type=artifacts.record.run_type,
            status=artifacts.record.status,
            symbols=symbols,
            total_steps=_report_int(report, "total_steps") or _max_step(events, snapshots, accounts, artifacts.logs),
            total_orders=_report_int(report, "total_orders") or _count_orders(events),
            total_events=len(events),
            total_trades=_report_int(report, "total_trades") or _count_event_type(events, "TradeExecuted"),
            total_snapshots=len(snapshots),
            total_rejections=_report_int(report, "total_rejections")
            or _report_int(report, "rejected_orders")
            or _count_rejections(events),
            total_volume=total_volume,
            traded_notional=traded_notional,
            final_prices=_final_prices(snapshots),
            final_positions=_final_positions(report, accounts),
            error=artifacts.record.error,
        )

    def get_replay_session(self, run_id: str) -> ReplaySessionResponse:
        artifacts = self.load_run(run_id)
        timeline = _replay_timeline(artifacts)
        controller = ReplayPlaybackController.create(timeline)
        frame = _build_replay_frame(artifacts, controller.cursor.step, symbol=None) if timeline.steps else None
        return ReplaySessionResponse(
            run_id=run_id,
            cursor=ReplayCursorModel(
                step=controller.cursor.step,
                state=controller.cursor.state,
                speed=controller.cursor.speed,
            ),
            timeline=_timeline_model(timeline, artifacts),
            frame=frame,
        )

    def get_replay_frame(self, run_id: str, step: int, *, symbol: str | None = None) -> ReplayFrame:
        artifacts = self.load_run(run_id)
        timeline = _replay_timeline(artifacts)
        controller = ReplayPlaybackController.create(timeline).jump_to_step(step)
        return _build_replay_frame(artifacts, controller.cursor.step, symbol=symbol)

    def get_replay_range(
        self,
        run_id: str,
        *,
        start_step: int,
        end_step: int,
        symbol: str | None = None,
        include_snapshots: bool = True,
        include_events: bool = True,
        include_accounts: bool = True,
    ) -> ReplayRangeResponse:
        artifacts = self.load_run(run_id)
        timeline = _replay_timeline(artifacts)
        bounded_start = timeline.clamp(start_step)
        bounded_end = timeline.clamp(end_step)
        if bounded_end < bounded_start:
            bounded_start, bounded_end = bounded_end, bounded_start
        steps = [step for step in timeline.steps if bounded_start <= step <= bounded_end]
        frames = [
            frame
            for step in steps
            for frame in [
                _build_replay_frame(
                    artifacts,
                    step,
                    symbol=symbol,
                    include_snapshots=include_snapshots,
                    include_events=include_events,
                    include_accounts=include_accounts,
                )
            ]
            if _frame_has_payload(frame)
        ]
        next_step = None
        for candidate in timeline.steps:
            if candidate > bounded_end:
                next_step = candidate
                break
        return ReplayRangeResponse(
            run_id=run_id,
            start_step=bounded_start,
            end_step=bounded_end,
            frames=frames,
            next_start_step=next_step,
            total_frames=len(steps),
        )

    def get_replay_summary(self, run_id: str) -> ReplaySummaryResponse:
        artifacts = self.load_run(run_id)
        timeline = _replay_timeline(artifacts)
        event_types = sorted({_entry_type("event", event) for event in artifacts.events})
        verification = self._store.get_verification(run_id) or {}
        return ReplaySummaryResponse(
            run_id=run_id,
            symbols=sorted(_symbols_from_artifacts(artifacts)),
            total_steps=timeline.last_step,
            total_frames=len(timeline.steps),
            total_events=len(artifacts.events),
            total_trades=_count_event_type(artifacts.events, "TradeExecuted"),
            total_snapshots=len(artifacts.snapshots),
            total_accounts=len(artifacts.accounts),
            start_step=timeline.first_step,
            end_step=timeline.last_step,
            first_divergence_step=_int_value(verification.get("first_divergence_step")),
            available_event_types=event_types,
            performance_notes=[
                "Use /runs/{run_id}/replay/range with bounded start_step/end_step for large runs.",
                "Disable snapshots, events, or accounts in range requests when a panel does not need them.",
            ],
        )

    def get_timeline(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        category: str | None = None,
        entry_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TimelineEntry]:
        artifacts = self.load_run(run_id)
        entries = _build_timeline(artifacts)
        entries = _filter_timeline(entries, symbol=symbol, category=category, entry_type=entry_type)
        return _page(entries, limit=limit, offset=offset)

    def get_symbol_timeline(
        self,
        run_id: str,
        symbol: str,
        *,
        category: str | None = None,
        entry_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TimelineEntry]:
        return self.get_timeline(
            run_id, symbol=symbol, category=category, entry_type=entry_type, limit=limit, offset=offset
        )

    def get_order_timeline(
        self,
        run_id: str,
        order_id: str,
        *,
        symbol: str | None = None,
        category: str | None = None,
        entry_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TimelineEntry]:
        entries = self.get_timeline(run_id, symbol=symbol, category=category, entry_type=entry_type)
        order_entries = [entry for entry in entries if _payload_has_order_id(entry.payload, order_id)]
        return _page(order_entries, limit=limit, offset=offset)

    def get_account_timeline(
        self,
        run_id: str,
        account_id: str,
        *,
        symbol: str | None = None,
        category: str | None = None,
        entry_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TimelineEntry]:
        entries = self.get_timeline(run_id, symbol=symbol, category=category, entry_type=entry_type)
        account_entries = [entry for entry in entries if _payload_has_account_id(entry.payload, account_id)]
        return _page(account_entries, limit=limit, offset=offset)


def _build_timeline(artifacts: _RunArtifacts) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    run_symbols = _configured_symbols(artifacts.record.config)
    for sequence, event in enumerate(artifacts.events):
        entries.append(_entry(sequence, "event", event, default_symbol=_single_symbol(run_symbols)))
    for sequence, snapshot in enumerate(artifacts.snapshots):
        entries.append(_entry(sequence, "snapshot", snapshot, default_symbol=_single_symbol(run_symbols)))
    for sequence, account in enumerate(artifacts.accounts):
        entries.append(_entry(sequence, "account", account, default_symbol=_single_symbol(run_symbols)))
    for sequence, log in enumerate(artifacts.logs):
        entries.append(_entry(sequence, "log", log, default_symbol=_single_symbol(run_symbols)))
    return sorted(entries, key=lambda item: (_sort_step(item), item.sequence, _CATEGORY_ORDER[item.category]))


def _entry(
    sequence: int,
    category: TimelineCategory,
    payload: dict[str, Any],
    *,
    default_symbol: str | None,
) -> TimelineEntry:
    entry_type = _entry_type(category, payload)
    return TimelineEntry(
        step=_entry_step(payload),
        timestamp=_entry_timestamp(payload),
        sequence=sequence,
        symbol=_entry_symbol(category, payload, default_symbol=default_symbol),
        category=category,
        type=entry_type,
        summary=_entry_summary(category, entry_type, payload),
        payload=payload,
    )


def _filter_timeline(
    entries: list[TimelineEntry], *, symbol: str | None, category: str | None, entry_type: str | None
) -> list[TimelineEntry]:
    filtered = entries
    if symbol is not None:
        filtered = [entry for entry in filtered if entry.symbol == symbol or _payload_references_symbol(entry.payload, symbol)]
    if category is not None:
        filtered = [entry for entry in filtered if entry.category == category]
    if entry_type is not None:
        filtered = [entry for entry in filtered if entry.type == entry_type]
    return filtered


def _page(entries: list[TimelineEntry], *, limit: int | None, offset: int) -> list[TimelineEntry]:
    start = max(0, offset)
    if limit is None:
        return entries[start:]
    return entries[start : start + max(0, limit)]


def _entry_step(payload: dict[str, Any]) -> int | None:
    direct = _int_value(payload.get("step"))
    if direct is not None:
        return direct
    return _int_value(_event_data(payload).get("step"))


def _entry_timestamp(payload: dict[str, Any]) -> Any | None:
    for key in ("timestamp", "time", "created_at"):
        if key in payload:
            return payload[key]
    data = _event_data(payload)
    for key in ("timestamp", "time"):
        if key in data:
            return data[key]
    return None


def _entry_symbol(category: str, payload: dict[str, Any], *, default_symbol: str | None) -> str | None:
    if category == "event":
        value = _string_value(_event_data(payload).get("symbol")) or _string_value(payload.get("symbol"))
        return value or default_symbol
    if category == "snapshot":
        value = _string_value(payload.get("symbol"))
        if value is not None:
            return value
        symbols = payload.get("symbols")
        if isinstance(symbols, dict) and len(symbols) == 1:
            key = next(iter(symbols))
            return key if isinstance(key, str) else None
        return default_symbol
    if category == "account":
        return _account_symbol(payload) or default_symbol
    return _string_value(payload.get("symbol")) or default_symbol


def _entry_type(category: str, payload: dict[str, Any]) -> str:
    if category == "event":
        return _string_value(payload.get("type")) or "event"
    if category == "snapshot":
        return _string_value(payload.get("type")) or "snapshot"
    if category == "account":
        return _string_value(payload.get("type")) or "account"
    if category == "log":
        return _string_value(payload.get("level")) or _string_value(payload.get("type")) or "log"
    return category


def _entry_summary(category: str, entry_type: str, payload: dict[str, Any]) -> str:
    if category == "event":
        data = _event_data(payload)
        symbol = _string_value(data.get("symbol"))
        order_id = _first_order_id(data)
        qty = _int_value(data.get("qty")) or _int_value(data.get("last_fill_qty"))
        price = _int_value(data.get("price"))
        parts = [entry_type]
        if symbol is not None:
            parts.append(f"symbol={symbol}")
        if order_id is not None:
            parts.append(f"order={order_id}")
        if qty is not None:
            parts.append(f"qty={qty}")
        if price is not None:
            parts.append(f"price={price}")
        return " ".join(parts)
    if category == "snapshot":
        step = _entry_step(payload)
        return f"snapshot step={step}" if step is not None else "snapshot"
    if category == "account":
        account_id = _string_value(payload.get("account_id"))
        return f"account {account_id}" if account_id is not None else "account"
    if category == "log":
        return _string_value(payload.get("message")) or entry_type
    return entry_type


def _sort_step(entry: TimelineEntry) -> int:
    return entry.step if entry.step is not None else entry.sequence


def _symbols_from_artifacts(artifacts: _RunArtifacts) -> set[str]:
    symbols = set(_configured_symbols(artifacts.record.config))
    for event in artifacts.events:
        symbol = _entry_symbol("event", event, default_symbol=None)
        if symbol is not None:
            symbols.add(symbol)
    for snapshot in artifacts.snapshots:
        symbols.update(_snapshot_symbols(snapshot))
    for account in artifacts.accounts:
        symbol = _account_symbol(account)
        if symbol is not None:
            symbols.add(symbol)
        symbols.update(_dict_keys(account.get("positions")))
        symbols.update(_dict_keys(account.get("mark_to_market")))
    return symbols


def _configured_symbols(config: dict[str, Any]) -> list[str]:
    symbols = config.get("symbols")
    return [symbol for symbol in symbols if isinstance(symbol, str)] if isinstance(symbols, list) else []


def _single_symbol(symbols: list[str]) -> str | None:
    return symbols[0] if len(symbols) == 1 else None


def _snapshot_symbols(snapshot: dict[str, Any]) -> set[str]:
    symbols: set[str] = set()
    direct = _string_value(snapshot.get("symbol"))
    if direct is not None:
        symbols.add(direct)
    symbols.update(_dict_keys(snapshot.get("symbols")))
    return symbols


def _account_symbol(account: dict[str, Any]) -> str | None:
    direct = _string_value(account.get("symbol"))
    if direct is not None:
        return direct
    positions = account.get("positions")
    if isinstance(positions, dict) and len(positions) == 1:
        key = next(iter(positions))
        return key if isinstance(key, str) else None
    mtm = account.get("mark_to_market")
    if isinstance(mtm, dict) and len(mtm) == 1:
        key = next(iter(mtm))
        return key if isinstance(key, str) else None
    return None


def _payload_references_symbol(payload: dict[str, Any], symbol: str) -> bool:
    if _string_value(payload.get("symbol")) == symbol:
        return True
    if _string_value(_event_data(payload).get("symbol")) == symbol:
        return True
    if symbol in _dict_keys(payload.get("symbols")):
        return True
    if symbol in _dict_keys(payload.get("positions")):
        return True
    if symbol in _dict_keys(payload.get("mark_to_market")):
        return True
    return False


def _payload_has_order_id(payload: dict[str, Any], order_id: str) -> bool:
    target = str(order_id)
    return any(str(value) == target for value in _iter_order_values(payload))


def _iter_order_values(value: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in _ORDER_ID_KEYS:
                values.append(nested)
            values.extend(_iter_order_values(nested))
    elif isinstance(value, list):
        for item in value:
            values.extend(_iter_order_values(item))
    return values


def _payload_has_account_id(payload: dict[str, Any], account_id: str) -> bool:
    target = str(account_id)
    if str(payload.get("account_id")) == target:
        return True
    data = _event_data(payload)
    return str(data.get("account_id")) == target


def _event_data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data")
    return data if isinstance(data, dict) else {}


def _first_order_id(data: dict[str, Any]) -> Any | None:
    for key in _ORDER_ID_KEYS:
        if key in data:
            return data[key]
    return None


def _report_int(report: dict[str, Any], key: str) -> int | None:
    return _int_value(report.get(key))


def _int_value(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _string_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _dict_keys(value: Any) -> set[str]:
    return {key for key in value if isinstance(key, str)} if isinstance(value, dict) else set()


def _max_step(*collections: list[dict[str, Any]]) -> int:
    steps = [_entry_step(item) for collection in collections for item in collection]
    present = [step for step in steps if step is not None]
    return max(present) if present else 0


def _count_orders(events: list[dict[str, Any]]) -> int:
    order_event_types = {
        "OrderAccepted",
        "HiddenOrderAccepted",
        "IcebergOrderAccepted",
        "StopOrderAccepted",
        "OrderRejected",
    }
    return sum(1 for event in events if event.get("type") in order_event_types)


def _count_event_type(events: list[dict[str, Any]], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def _count_rejections(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if str(event.get("type", "")).endswith("Rejected"))


def _final_prices(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    prices: dict[str, Any] = {}
    for snapshot in sorted(snapshots, key=lambda item: (_entry_step(item) or 0)):
        direct_symbol = _string_value(snapshot.get("symbol"))
        if direct_symbol is not None:
            prices[direct_symbol] = _snapshot_price(snapshot.get("snapshot", snapshot))
        symbols = snapshot.get("symbols")
        if isinstance(symbols, dict):
            for symbol, value in symbols.items():
                if isinstance(symbol, str):
                    prices[symbol] = _snapshot_price(value)
    return prices


def _snapshot_price(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    for key in ("last_price", "price", "mid", "mid_price"):
        if key in value:
            return value[key]
    bid = _int_value(value.get("best_bid")) or _int_value(value.get("bid"))
    ask = _int_value(value.get("best_ask")) or _int_value(value.get("ask"))
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    return bid if bid is not None else ask


def _final_positions(report: dict[str, Any], accounts: list[dict[str, Any]]) -> dict[str, Any]:
    report_positions = report.get("final_positions")
    if isinstance(report_positions, dict):
        return dict(report_positions)
    for account in reversed(accounts):
        positions = account.get("positions")
        if isinstance(positions, dict):
            return dict(positions)
    return {}


def _artifact_payload(artifacts: _RunArtifacts) -> dict[str, Any]:
    return {
        "report": artifacts.report,
        "events": artifacts.events,
        "snapshots": artifacts.snapshots,
        "accounts": artifacts.accounts,
        "logs": artifacts.logs,
    }


def _replay_timeline(artifacts: _RunArtifacts) -> ReplayTimeline:
    steps = {_entry_step(item) for collection in (artifacts.events, artifacts.snapshots, artifacts.accounts, artifacts.logs) for item in collection}
    present = sorted(step for step in steps if step is not None)
    if not present:
        max_step = _report_int(artifacts.report, "total_steps") or 0
        present = list(range(0, max_step + 1)) if max_step > 0 else [0]
    return ReplayTimeline(tuple(present))


def _timeline_model(timeline: ReplayTimeline, artifacts: _RunArtifacts) -> ReplayTimelineModel:
    event_steps = sorted({step for event in artifacts.events for step in [_entry_step(event)] if step is not None})
    return ReplayTimelineModel(
        start_step=timeline.first_step,
        end_step=timeline.last_step,
        steps=list(timeline.steps),
        total_frames=len(timeline.steps),
        event_steps=event_steps,
        symbols=sorted(_symbols_from_artifacts(artifacts)),
    )


def _build_replay_frame(
    artifacts: _RunArtifacts,
    step: int,
    *,
    symbol: str | None,
    include_snapshots: bool = True,
    include_events: bool = True,
    include_accounts: bool = True,
) -> ReplayFrame:
    events = _step_items(artifacts.events, step, symbol=symbol) if include_events else []
    snapshots = _step_items(artifacts.snapshots, step, symbol=symbol) if include_snapshots else []
    accounts = _step_items(artifacts.accounts, step, symbol=symbol) if include_accounts else []
    trades = [_trade_payload(event) for event in events if event.get("type") == "TradeExecuted"]
    selected_symbols = sorted(_frame_symbols(symbol, events, snapshots, accounts, artifacts))
    top_of_book = _top_of_book_for_frame(artifacts.snapshots, step, selected_symbols)
    account_deltas = [_account_delta(account) for account in accounts]
    market_metrics = _market_metrics(top_of_book, trades)
    event_summaries = [
        {
            "sequence": index,
            "type": _entry_type("event", event),
            "summary": _entry_summary("event", _entry_type("event", event), event),
            "symbol": _entry_symbol("event", event, default_symbol=symbol),
        }
        for index, event in enumerate(events)
    ]
    timestamp = _first_present([_entry_timestamp(item) for item in [*events, *snapshots, *accounts]])
    return ReplayFrame(
        step=step,
        timestamp=timestamp,
        symbols=selected_symbols,
        symbol=symbol if symbol is not None else (selected_symbols[0] if len(selected_symbols) == 1 else None),
        trades=trades,
        snapshots=snapshots,
        top_of_book=top_of_book,
        account_deltas=account_deltas,
        accounts=accounts,
        market_metrics=market_metrics,
        event_summaries=event_summaries,
    )


def _step_items(items: list[dict[str, Any]], step: int, *, symbol: str | None) -> list[dict[str, Any]]:
    selected = [item for item in items if _entry_step(item) == step]
    if symbol is None:
        return selected
    return [item for item in selected if _payload_references_symbol(item, symbol) or _entry_symbol("snapshot", item, default_symbol=None) == symbol]


def _frame_symbols(
    symbol: str | None,
    events: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    artifacts: _RunArtifacts,
) -> set[str]:
    if symbol is not None:
        return {symbol}
    symbols: set[str] = set()
    for event in events:
        value = _entry_symbol("event", event, default_symbol=None)
        if value is not None:
            symbols.add(value)
    for snapshot in snapshots:
        symbols.update(_snapshot_symbols(snapshot))
    for account in accounts:
        value = _account_symbol(account)
        if value is not None:
            symbols.add(value)
        symbols.update(_dict_keys(account.get("positions")))
    return symbols or _symbols_from_artifacts(artifacts)


def _top_of_book_for_frame(snapshots: list[dict[str, Any]], step: int, symbols: list[str]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for snapshot in sorted(snapshots, key=lambda item: (_entry_step(item) or 0)):
        item_step = _entry_step(snapshot)
        if item_step is None or item_step > step:
            continue
        direct_symbol = _string_value(snapshot.get("symbol"))
        if direct_symbol is not None and direct_symbol in symbols:
            selected[direct_symbol] = _book_payload(snapshot.get("snapshot", snapshot))
        payload_symbols = snapshot.get("symbols")
        if isinstance(payload_symbols, dict):
            for symbol, value in payload_symbols.items():
                if isinstance(symbol, str) and symbol in symbols:
                    selected[symbol] = _book_payload(value)
    return selected


def _book_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    bid = _first_int(value, ("best_bid", "bid", "bid_price"))
    ask = _first_int(value, ("best_ask", "ask", "ask_price"))
    bid_qty = _first_int(value, ("best_bid_qty", "bid_qty", "bid_quantity"))
    ask_qty = _first_int(value, ("best_ask_qty", "ask_qty", "ask_quantity"))
    spread = ask - bid if ask is not None and bid is not None else None
    mid = (ask + bid) / 2 if ask is not None and bid is not None else None
    imbalance = None
    if bid_qty is not None and ask_qty is not None and bid_qty + ask_qty > 0:
        imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)
    return {
        "bid": bid,
        "ask": ask,
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        "spread": spread,
        "mid": mid,
        "imbalance": imbalance,
        "bids": value.get("bids", []),
        "asks": value.get("asks", []),
    }


def _trade_payload(event: dict[str, Any]) -> dict[str, Any]:
    data = _event_data(event)
    return {
        "trade_id": data.get("trade_id") or data.get("execution_id") or f"{data.get('maker_order_id', 'm')}-{data.get('taker_order_id', 't')}-{data.get('step', '')}",
        "symbol": data.get("symbol"),
        "price": data.get("price"),
        "qty": data.get("qty"),
        "aggressor_side": data.get("aggressor_side") or data.get("side"),
        "timestamp": _entry_timestamp(event),
        "step": _entry_step(event),
        "event": event,
    }


def _account_delta(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_id": account.get("account_id"),
        "step": _entry_step(account),
        "positions": account.get("positions", {}),
        "cash": account.get("cash"),
        "pnl": account.get("pnl") or account.get("realized_pnl") or account.get("unrealized_pnl"),
        "equity": account.get("equity") or account.get("net_liquidation"),
        "exposure": account.get("exposure") or account.get("gross_exposure"),
        "leverage": account.get("leverage"),
        "payload": account,
    }


def _market_metrics(top_of_book: dict[str, Any], trades: list[dict[str, Any]]) -> dict[str, Any]:
    volume = sum(_int_value(trade.get("qty")) or 0 for trade in trades)
    notional = sum((_int_value(trade.get("price")) or 0) * (_int_value(trade.get("qty")) or 0) for trade in trades)
    return {"trade_count": len(trades), "volume": volume, "notional": notional, "top_of_book": top_of_book}


def _first_int(value: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        found = _int_value(value.get(key))
        if found is not None:
            return found
    return None


def _first_present(values: list[Any | None]) -> Any | None:
    for value in values:
        if value is not None:
            return value
    return None


def _frame_has_payload(frame: ReplayFrame) -> bool:
    return bool(frame.trades or frame.snapshots or frame.account_deltas or frame.event_summaries)
