"""Runtime-owned savestate slot management with path containment.

The browser and future agent loop address savestates by slot name only. This
module maps validated names to files under the configured runtime state
directory and calls emulator bridge save/load primitives with contained paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .emulators.base import EmulatorBridge
from .trace_recorder import TraceRecorder


SLOT_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
STATE_SUFFIX = ".ss"


class StateSlotError(ValueError):
    """Raised when a state slot request is invalid or cannot be fulfilled."""


@dataclass(frozen=True)
class StateSlotManager:
    """Owns savestate files for one runtime instance."""

    emulator: EmulatorBridge
    trace_recorder: TraceRecorder
    state_dir: Path

    def list_slots(self) -> dict[str, Any]:
        """Return metadata for existing runtime-owned state slots."""

        self.state_dir.mkdir(parents=True, exist_ok=True)
        return {"slots": [self._metadata(path) for path in sorted(self.state_dir.glob(f"*{STATE_SUFFIX}"))]}

    def save(self, slot: str) -> dict[str, Any]:
        """Save emulator state into a validated runtime-owned slot."""

        path = self._slot_path(slot)
        save_state = getattr(self.emulator, "save_state", None)
        if not callable(save_state):
            raise StateSlotError("emulator bridge does not support savestates")
        save_state(path)
        trace = self.trace_recorder.record("state", "saved", {"slot": slot, "frame": self.emulator.frame_count})
        return {"ok": True, "slot": self._metadata(path), "trace_id": trace["id"], "frame": self.emulator.frame_count}

    def load(self, slot: str) -> dict[str, Any]:
        """Load emulator state from a validated runtime-owned slot."""

        path = self._slot_path(slot)
        if not path.exists():
            raise StateSlotError(f"state slot does not exist: {slot}")
        load_state = getattr(self.emulator, "load_state", None)
        if not callable(load_state):
            raise StateSlotError("emulator bridge does not support savestates")
        load_state(path)
        trace = self.trace_recorder.record("state", "loaded", {"slot": slot, "frame": self.emulator.frame_count})
        return {"ok": True, "slot": self._metadata(path), "trace_id": trace["id"], "frame": self.emulator.frame_count}

    def _slot_path(self, slot: str) -> Path:
        if not SLOT_RE.match(slot):
            raise StateSlotError("slot must be 1-32 letters, numbers, underscores, or dashes")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        root = self.state_dir.resolve()
        path = (root / f"{slot}{STATE_SUFFIX}").resolve()
        if root != path.parent:
            raise StateSlotError("state slot path escaped runtime state directory")
        return path

    def _metadata(self, path: Path) -> dict[str, Any]:
        exists = path.exists()
        stat = path.stat() if exists else None
        return {
            "name": path.stem,
            "exists": exists,
            "size_bytes": stat.st_size if stat else 0,
            "updated_at": _iso_timestamp(stat.st_mtime) if stat else None,
        }


def _iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
