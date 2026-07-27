"""Agent planning service layered above runtime context and action policy."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from .codex_client import AgentClientError, DisabledAgentClient, PlannerClient


class AgentRuntime(Protocol):
    """Runtime surface needed by the planner service."""

    def agent_context(self, objective: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return compact planner context."""

    def execute_agent_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute one already-decided planner action through policy validation."""


@dataclass
class AgentService:
    """Runs one planner decision against a runtime with a configurable client."""

    runtime: AgentRuntime
    client: PlannerClient = field(default_factory=DisabledAgentClient)
    last_decision: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
    last_error: str | None = None
    step_count: int = 0

    def configure_client(self, client: PlannerClient) -> None:
        """Replace the planner client without changing runtime/manual controls."""

        self.client = client
        self.last_decision = None
        self.last_result = None
        self.last_error = None
        self.step_count = 0

    def status(self) -> dict[str, Any]:
        """Return service and backend state for future API/UI surfaces."""

        return {
            "state": "error" if self.last_error else "idle",
            "step_count": self.step_count,
            "client": self.client.status(),
            "last_decision": self.last_decision,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

    def run_step(
        self,
        *,
        operator_prompt: str | None = None,
        objective: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Observe context, ask for one action, and execute it through policy."""

        objective_summary = _planner_objective_summary(objective)
        context = (
            self.runtime.agent_context(objective_summary)
            if objective_summary is not None
            else self.runtime.agent_context()
        )
        try:
            decision = self.client.decide(context, operator_prompt=operator_prompt)
            result = self.runtime.execute_agent_action(decision.as_agent_action())
        except AgentClientError as exc:
            self.last_error = str(exc)
            raise
        self.step_count += 1
        self.last_error = None
        self.last_decision = {
            "action_id": decision.action_id,
            "reason": decision.reason,
            "metadata": decision.metadata or {},
            "decided_at": datetime.now(UTC).isoformat(),
        }
        self.last_result = result
        return {
            "ok": True,
            "step": self.step_count,
            "decision": self.last_decision,
            "result": result,
        }

    def close(self) -> None:
        """Release resources held by the configured planner client if needed."""

        close = getattr(self.client, "close", None)
        if callable(close):
            close()


_PLANNER_SUCCESS_FIELDS = {
    "agent_steps_at_least",
    "runtime_frame_at_least",
    "mode_is",
    "map_is",
    "position_is",
    "position_changed",
}
_LOCAL_PATH_TOKEN = re.compile(r"(?<![\w])(?:~?/|[A-Za-z]:[/\\]|\\\\)[^\s,;]+")


def _planner_objective_summary(objective: dict[str, Any] | None) -> dict[str, Any] | None:
    """Expose only bounded objective fields to the planner context.

    The objective API accepts an extensible JSON object, while planner context
    should contain only the task and criteria understood by the runtime. This
    prevents private paths or unrelated request fields from flowing to a model.
    """

    if objective is None:
        return None
    description = objective.get("description")
    summary: dict[str, Any] = {
        "active": True,
        "description": _bounded_text(description, 500),
        "success": {},
    }
    max_steps = objective.get("max_steps")
    if type(max_steps) is int:
        summary["max_steps"] = max(1, min(max_steps, 20))
    step = objective.get("step")
    if type(step) is int:
        summary["step"] = max(0, min(step, 20))
    starting_state = objective.get("starting_state")
    if isinstance(starting_state, dict):
        summary["starting_state"] = {
            "mode": _bounded_text(starting_state.get("mode"), 120),
            "map_id": _bounded_text(starting_state.get("map_id"), 120),
            **{name: value for name in ("player_x", "player_y")
               if type(value := starting_state.get(name)) is int},
        }

    success = objective.get("success")
    if isinstance(success, dict):
        safe_success: dict[str, Any] = {}
        for name, value in success.items():
            if name not in _PLANNER_SUCCESS_FIELDS:
                continue
            if name in {"mode_is", "map_is"} and isinstance(value, str):
                safe_success[name] = _bounded_text(value, 120)
            elif name in {"agent_steps_at_least", "runtime_frame_at_least"} and type(value) is int:
                safe_success[name] = max(0, value)
            elif name == "position_changed" and value is True:
                safe_success[name] = True
            elif name == "position_is" and isinstance(value, dict):
                x, y = value.get("x"), value.get("y")
                if type(x) is int and type(y) is int:
                    safe_success[name] = {"x": x, "y": y}
        summary["success"] = safe_success
    return summary


def _bounded_text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.replace("\x00", "").split())
    # Keep task wording while removing absolute local path tokens.
    text = _LOCAL_PATH_TOKEN.sub("[local path]", text)
    return text[:limit] or None
