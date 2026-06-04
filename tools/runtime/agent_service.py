"""Agent planning service layered above runtime context and action policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from .codex_client import AgentClientError, DisabledAgentClient, PlannerClient


class AgentRuntime(Protocol):
    """Runtime surface needed by the planner service."""

    def agent_context(self) -> dict[str, Any]:
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

    def run_step(self, *, operator_prompt: str | None = None) -> dict[str, Any]:
        """Observe context, ask the planner for one action, and execute it."""

        context = self.runtime.agent_context()
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
