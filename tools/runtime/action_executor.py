"""Validated runtime actions for emulator control.

This module is the only place where external button/action requests are turned
into emulator bridge calls. Keeping validation here prevents UI or agent callers
from bypassing the allowed action policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .emulators.base import EmulatorBridge
from .trace_recorder import TraceRecorder


ALLOWED_BUTTONS = frozenset({"up", "down", "left", "right", "a", "b", "start", "select", "l", "r"})
ALLOWED_ACTIONS = frozenset({"tap", "press", "release", "wait"})


class ActionValidationError(ValueError):
    """Raised when an action request is outside the runtime policy."""


@dataclass(frozen=True)
class ActionRequest:
    """A normalized action request accepted by the runtime."""

    action: Literal["tap", "press", "release", "wait"]
    button: str | None = None
    frames: int = 1

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "ActionRequest":
        action = str(payload.get("action", "")).lower()
        button_value = payload.get("button")
        button = str(button_value).lower() if button_value is not None else None
        try:
            frames = int(payload.get("frames", 1))
        except (TypeError, ValueError) as exc:
            raise ActionValidationError("frames must be an integer") from exc
        request = cls(action=action, button=button, frames=frames)  # type: ignore[arg-type]
        request.validate()
        return request

    def validate(self) -> None:
        if self.action not in ALLOWED_ACTIONS:
            raise ActionValidationError(f"unsupported action: {self.action!r}")
        if self.frames < 1 or self.frames > 600:
            raise ActionValidationError("frames must be between 1 and 600")
        if self.action in {"tap", "press", "release"}:
            if self.button not in ALLOWED_BUTTONS:
                raise ActionValidationError(f"unsupported button: {self.button!r}")
        if self.action == "wait" and self.button is not None:
            raise ActionValidationError("wait action must not include a button")


class ActionExecutor:
    """Executes validated actions against an emulator bridge and records traces."""

    def __init__(self, emulator: EmulatorBridge, trace_recorder: TraceRecorder) -> None:
        self._emulator = emulator
        self._traces = trace_recorder

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = ActionRequest.from_mapping(payload)
        except ActionValidationError as exc:
            trace = self._traces.record("action", "rejected", {"payload": payload, "error": str(exc)})
            raise ActionValidationError(str(exc)) from exc

        if request.action == "tap":
            assert request.button is not None
            self._emulator.press_button(request.button)
            self._emulator.run_frames(request.frames)
            self._emulator.release_button(request.button)
        elif request.action == "press":
            assert request.button is not None
            self._emulator.press_button(request.button)
        elif request.action == "release":
            assert request.button is not None
            self._emulator.release_button(request.button)
        elif request.action == "wait":
            self._emulator.run_frames(request.frames)

        trace = self._traces.record(
            "action",
            "accepted",
            {"action": request.action, "button": request.button, "frames": request.frames},
        )
        return {"ok": True, "trace_id": trace["id"], "frame": self._emulator.frame_count}
