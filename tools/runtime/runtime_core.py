"""Core runtime orchestration independent of emulator and game details."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .action_executor import ActionExecutor
from .agent_context import build_agent_context
from .agent_service import AgentService
from .codex_client import PlannerClient
from .emulators.base import EmulatorBridge
from .interaction_policy import AgentActionPolicy
from .state_models import empty_telemetry_snapshot
from .state_slots import StateSlotManager
from .trace_recorder import TraceRecorder


TelemetryReader = Callable[[EmulatorBridge], dict[str, Any]]


def empty_telemetry(emulator: EmulatorBridge) -> dict[str, Any]:
    """Return a minimal telemetry payload when no game adapter is configured."""

    return empty_telemetry_snapshot(emulator.frame_count)


class RuntimeCore:
    """Coordinates bridge primitives, traces, actions, and telemetry snapshots."""

    def __init__(
        self,
        emulator: EmulatorBridge,
        telemetry_reader: TelemetryReader = empty_telemetry,
        state_dir: Path | None = None,
    ) -> None:
        self.emulator = emulator
        self.traces = TraceRecorder()
        self.actions = ActionExecutor(emulator, self.traces)
        self._telemetry_reader = telemetry_reader
        self.states = StateSlotManager(emulator, self.traces, state_dir or Path(".runtime-state"))
        self.agent_actions = AgentActionPolicy(
            self.actions,
            self.traces,
            save_state=self.save_state,
            load_state=self.load_state,
        )
        self.agent_service = AgentService(self)

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

    def agent_context(self) -> dict[str, Any]:
        return build_agent_context(self.telemetry(), self.recent_traces(), self.list_states())

    def execute_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.actions.execute(payload)

    def execute_agent_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.agent_actions.execute(payload)

    def configure_agent_client(self, client: PlannerClient) -> None:
        self.agent_service.configure_client(client)

    def agent_status(self) -> dict[str, Any]:
        return self.agent_service.status()

    def run_agent_step(self, operator_prompt: str | None = None) -> dict[str, Any]:
        return self.agent_service.run_step(operator_prompt=operator_prompt)

    def recent_traces(self) -> list[dict[str, Any]]:
        return self.traces.recent()

    def list_states(self) -> dict[str, Any]:
        return self.states.list_slots()

    def save_state(self, slot: str) -> dict[str, Any]:
        return self.states.save(slot)

    def load_state(self, slot: str) -> dict[str, Any]:
        return self.states.load(slot)

    def close(self) -> None:
        """Release emulator resources owned by this runtime."""

        self.agent_service.close()
        close = getattr(self.emulator, "close", None)
        if callable(close):
            close()
