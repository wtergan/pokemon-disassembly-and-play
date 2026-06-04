"""In-memory objective run ledger for bounded agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ObjectiveMemory:
    """Records objective-run steps without creating unbounded logs."""

    objective: dict[str, Any]
    started_at: str = field(default_factory=_timestamp)
    completed_at: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def append_step(self, record: dict[str, Any]) -> None:
        """Append one step record with a stable timestamp."""

        self.steps.append({"timestamp": _timestamp(), **record})

    def finish(self) -> None:
        """Mark the run complete."""

        self.completed_at = _timestamp()
