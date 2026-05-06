"""In-process Server-Sent Events stream coordination for TES runs."""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from datetime import UTC, datetime
from queue import Queue
from threading import RLock
from typing import Any, Iterator

from sim.api.models import StreamCategory, StreamMessage
from sim.api.storage import RunStore

_SENTINEL = object()
_DEFAULT_RECENT_LIMIT = 100


class StreamService:
    """Publish, replay, and subscribe to API run progress messages."""

    def __init__(self, store: RunStore, *, recent_limit: int = _DEFAULT_RECENT_LIMIT) -> None:
        self._store = store
        self._recent_limit = max(1, recent_limit)
        self._recent: dict[str, deque[StreamMessage]] = defaultdict(
            lambda: deque(maxlen=self._recent_limit)
        )
        self._subscribers: dict[str, list[Queue[StreamMessage | object]]] = defaultdict(list)
        self._closed: set[str] = set()
        self._lock = RLock()

    def publish(
        self,
        run_id: str,
        message: StreamMessage | dict[str, Any],
        *,
        persist: bool = True,
    ) -> StreamMessage:
        """Publish a stream message to active subscribers and recent replay storage."""

        stream_message = self._coerce_message(run_id, message)
        with self._lock:
            self._recent[run_id].append(stream_message)
            subscribers = list(self._subscribers.get(run_id, ()))
        for subscriber in subscribers:
            subscriber.put(stream_message)
        if persist:
            self._store.append_log(run_id, self.to_log(stream_message))
        return stream_message

    def subscribe(self, run_id: str) -> Iterator[StreamMessage]:
        """Subscribe to future stream messages for a run."""

        queue: Queue[StreamMessage | object] = Queue()
        with self._lock:
            closed = run_id in self._closed
            if not closed:
                self._subscribers[run_id].append(queue)
        try:
            if closed:
                return
            while True:
                item = queue.get()
                if item is _SENTINEL:
                    break
                yield item  # type: ignore[misc]
        finally:
            with self._lock:
                subscribers = self._subscribers.get(run_id)
                if subscribers is not None and queue in subscribers:
                    subscribers.remove(queue)

    def close(self, run_id: str) -> None:
        """Close a run stream and unblock active subscribers."""

        with self._lock:
            self._closed.add(run_id)
            subscribers = list(self._subscribers.pop(run_id, ()))
        for subscriber in subscribers:
            subscriber.put(_SENTINEL)

    def replay_recent(self, run_id: str, limit: int = _DEFAULT_RECENT_LIMIT) -> list[StreamMessage]:
        """Replay recent in-memory or persisted stream messages for a run."""

        bounded_limit = max(0, limit)
        if bounded_limit == 0:
            return []
        with self._lock:
            recent = list(self._recent.get(run_id, ()))
        if recent:
            return deepcopy(recent[-bounded_limit:])
        logs = self._store.get_logs(run_id, limit=bounded_limit)
        if logs is None:
            return []
        messages: list[StreamMessage] = []
        for log in logs[-bounded_limit:]:
            parsed = self.from_log(run_id, log)
            if parsed is not None:
                messages.append(parsed)
        return messages

    def is_closed(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._closed

    @staticmethod
    def to_log(message: StreamMessage) -> dict[str, Any]:
        return {
            "timestamp": message.timestamp.isoformat().replace("+00:00", "Z"),
            "step": message.step,
            "level": message.category,
            "category": message.category,
            "type": message.type,
            "message": message.type,
            "payload": deepcopy(message.payload),
            "stream": message.model_dump(mode="json"),
        }

    @staticmethod
    def from_log(run_id: str, log: dict[str, Any]) -> StreamMessage | None:
        stream = log.get("stream")
        if isinstance(stream, dict):
            return StreamMessage.model_validate(stream)
        category = log.get("category") or log.get("level")
        if not isinstance(category, str):
            return None
        try:
            return StreamMessage(
                run_id=run_id,
                timestamp=_parse_timestamp(log.get("timestamp")),
                step=(
                    log.get("step")
                    if isinstance(log.get("step"), int) and not isinstance(log.get("step"), bool)
                    else None
                ),
                category=category,  # type: ignore[arg-type]
                type=str(log.get("type") or log.get("message") or category),
                payload=log.get("payload") if isinstance(log.get("payload"), dict) else {},
            )
        except Exception:
            return None

    def _coerce_message(self, run_id: str, message: StreamMessage | dict[str, Any]) -> StreamMessage:
        if isinstance(message, StreamMessage):
            if message.run_id != run_id:
                raise ValueError("stream message run_id does not match publish run_id")
            return message
        payload = message.get("payload")
        return StreamMessage(
            run_id=run_id,
            timestamp=(
                message.get("timestamp")
                if isinstance(message.get("timestamp"), datetime)
                else datetime.now(UTC)
            ),
            step=(
                message.get("step")
                if isinstance(message.get("step"), int) and not isinstance(message.get("step"), bool)
                else None
            ),
            category=(
                message["category"]
                if message.get("category") in _CATEGORIES
                else _invalid_category(message.get("category"))
            ),
            type=str(message.get("type") or message.get("category") or "message"),
            payload=deepcopy(payload) if isinstance(payload, dict) else {},
        )


_CATEGORIES: set[str] = {"status", "progress", "event", "snapshot", "account", "log", "error", "completed"}


def _invalid_category(value: object) -> StreamCategory:
    raise ValueError(f"invalid stream category: {value!r}")


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(UTC)
