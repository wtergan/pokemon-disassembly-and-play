"""Planner-facing action policy for bounded agent control.

The manual runtime accepts primitive button actions through `ActionExecutor`.
Agent callers get a narrower policy: every request names one advertised action
ID, optional fields must match the advertised affordance, and the policy records
proposed, validation, execution, and rejection traces for review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .action_executor import ActionExecutor
from .state_slots import StateSlotError
from .trace_recorder import TraceRecorder


AGENT_BUTTONS = ("up", "down", "left", "right", "a", "b", "start", "select", "l", "r")
_REQUEST_KEYS = frozenset({"action_id", "reason", "button", "frames", "slot"})


class AgentActionValidationError(ValueError):
    """Raised when an agent request is outside the planner action policy."""


def allowed_agent_actions() -> list[dict[str, Any]]:
    """Return the planner action affordances accepted by `AgentActionPolicy`."""

    actions: list[dict[str, Any]] = [
        {"id": "inspect", "type": "observe", "description": "Re-read agent context without pressing inputs."},
        {"id": "wait_short", "type": "wait", "frames": 15, "description": "Wait briefly and observe again."},
        {"id": "save_quick", "type": "save_state", "slot": "quick", "description": "Save a runtime-owned quick checkpoint."},
        {"id": "load_quick", "type": "load_state", "slot": "quick", "description": "Restore the quick checkpoint when recovery is needed."},
        {"id": "stop", "type": "control", "description": "Stop the current objective loop."},
    ]
    actions.extend(
        {"id": f"tap_{button}", "type": "tap", "button": button, "frames": 12, "description": f"Tap {button.upper()}."}
        for button in AGENT_BUTTONS
    )
    actions.extend(
        {
            "id": f"hold_{button}",
            "type": "hold",
            "button": button,
            "frames": 20,
            "description": f"Hold {button.upper()} for a short bounded interval.",
        }
        for button in ("up", "down", "left", "right", "a", "b")
    )
    return actions


@dataclass(frozen=True)
class AgentActionRequest:
    """A normalized planner request after policy validation."""

    action_id: str
    reason: str
    affordance: dict[str, Any]

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "AgentActionRequest":
        unknown_keys = sorted(set(payload) - _REQUEST_KEYS)
        if unknown_keys:
            raise AgentActionValidationError(f"unsupported agent action fields: {', '.join(unknown_keys)}")

        action_id = str(payload.get("action_id", "")).strip()
        reason = str(payload.get("reason", "")).strip()
        if not action_id:
            raise AgentActionValidationError("action_id is required")
        if not reason:
            raise AgentActionValidationError("reason is required")

        affordance = _ACTIONS_BY_ID.get(action_id)
        if affordance is None:
            raise AgentActionValidationError(f"unsupported agent action: {action_id!r}")
        _validate_optional_match(payload, affordance)
        return cls(action_id=action_id, reason=reason[:500], affordance=affordance)


class AgentActionPolicy:
    """Validates and executes advertised planner actions with reviewable traces."""

    def __init__(
        self,
        action_executor: ActionExecutor,
        trace_recorder: TraceRecorder,
        *,
        save_state: Callable[[str], dict[str, Any]],
        load_state: Callable[[str], dict[str, Any]],
    ) -> None:
        self._actions = action_executor
        self._traces = trace_recorder
        self._save_state = save_state
        self._load_state = load_state

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate an agent request, execute it if allowed, and trace the result."""

        proposed = self._traces.record(
            "agent_action",
            "proposed",
            {"action_id": _trace_value(payload.get("action_id")), "reason": _trace_value(payload.get("reason"))},
        )
        try:
            request = AgentActionRequest.from_mapping(payload)
        except AgentActionValidationError as exc:
            self._traces.record(
                "agent_action",
                "rejected",
                {
                    "action_id": _trace_value(payload.get("action_id")),
                    "proposed_trace_id": proposed["id"],
                    "error": str(exc),
                },
            )
            raise AgentActionValidationError(str(exc)) from exc

        self._traces.record(
            "agent_action",
            "validated",
            {"action_id": request.action_id, "reason": request.reason, "proposed_trace_id": proposed["id"]},
        )
        try:
            result = self._execute_allowed(request)
        except (AgentActionValidationError, StateSlotError) as exc:
            self._traces.record(
                "agent_action",
                "failed",
                {"action_id": request.action_id, "reason": request.reason, "error": str(exc)},
            )
            raise type(exc)(str(exc)) from exc

        trace = self._traces.record(
            "agent_action",
            "executed",
            {
                "action_id": request.action_id,
                "reason": request.reason,
                "result_trace_id": result.get("trace_id"),
                "frame": result.get("frame"),
            },
        )
        return {
            "ok": True,
            "action_id": request.action_id,
            "status": result.get("status", "completed"),
            "trace_id": trace["id"],
            "result": result,
        }

    def _execute_allowed(self, request: AgentActionRequest) -> dict[str, Any]:
        affordance = request.affordance
        action_type = affordance["type"]
        if action_type == "observe":
            return {"ok": True, "status": "observed"}
        if action_type == "control" and request.action_id == "stop":
            return {"ok": True, "status": "stopped"}
        if action_type == "wait":
            return self._actions.execute({"action": "wait", "frames": affordance["frames"]})
        if action_type in {"tap", "hold"}:
            return self._actions.execute(
                {"action": "tap", "button": affordance["button"], "frames": affordance["frames"]}
            )
        if action_type == "save_state":
            return self._save_state(affordance["slot"])
        if action_type == "load_state":
            return self._load_state(affordance["slot"])
        raise AgentActionValidationError(f"unsupported agent action type: {action_type!r}")


def _validate_optional_match(payload: dict[str, Any], affordance: dict[str, Any]) -> None:
    for key in ("button", "slot"):
        if key in payload and payload[key] != affordance.get(key):
            raise AgentActionValidationError(f"{key} must match advertised action")
    if "frames" in payload:
        try:
            frames = int(payload["frames"])
        except (TypeError, ValueError) as exc:
            raise AgentActionValidationError("frames must be an integer") from exc
        if frames != affordance.get("frames"):
            raise AgentActionValidationError("frames must match advertised action")


def _trace_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:500]


_ACTIONS_BY_ID = {action["id"]: action for action in allowed_agent_actions()}
