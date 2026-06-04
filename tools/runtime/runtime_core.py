"""Core runtime orchestration independent of emulator and game details."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .action_executor import ActionExecutor
from .emulators.base import EmulatorBridge
from .trace_recorder import TraceRecorder


TelemetryReader = Callable[[EmulatorBridge], dict[str, Any]]


def empty_telemetry(emulator: EmulatorBridge) -> dict[str, Any]:
    """Return a minimal telemetry payload when no game adapter is configured."""

    return {"frame": emulator.frame_count, "status": "unavailable"}


class RuntimeCore:
    """Coordinates bridge primitives, traces, actions, and telemetry snapshots."""

    def __init__(self, emulator: EmulatorBridge, telemetry_reader: TelemetryReader = empty_telemetry) -> None:
        self.emulator = emulator
        self.traces = TraceRecorder()
        self.actions = ActionExecutor(emulator, self.traces)
        self._telemetry_reader = telemetry_reader

    def health(self) -> dict[str, Any]:
        health = self.emulator.health()
        return {
            "ok": health.running,
            "bridge": health.bridge,
            "frame": health.frame,
            "detail": health.detail,
        }

    def snapshot(self) -> dict[str, Any]:
        snapshot = self.emulator.snapshot()
        return {
            "frame": snapshot.frame,
            "mime_type": snapshot.mime_type,
            "image_base64": snapshot.image_base64,
        }

    def telemetry(self) -> dict[str, Any]:
        return self._telemetry_reader(self.emulator)

    def execute_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.actions.execute(payload)

    def recent_traces(self) -> list[dict[str, Any]]:
        return self.traces.recent()

