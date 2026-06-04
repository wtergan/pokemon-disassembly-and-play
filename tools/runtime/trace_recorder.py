"""Bounded in-memory trace recorder for runtime actions and events."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from itertools import count
from typing import Any


class TraceRecorder:
    """Records recent runtime events without writing unbounded logs."""

    def __init__(self, limit: int = 200) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=limit)
        self._ids = count(1)

    def record(self, event_type: str, status: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "id": next(self._ids),
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "status": status,
            "detail": detail or {},
        }
        self._events.append(event)
        return event

    def recent(self) -> list[dict[str, Any]]:
        return list(self._events)

