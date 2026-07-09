"""Bounded objective runner for planner-safe agent steps.

The runner does not infer success from action count. Each step captures context
before and after the planner action, records a compact delta, and stops only on
explicit success criteria, planner stop, step cap, external stop, or error.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Protocol

from .objective_memory import ObjectiveMemory
from .objective_scoring import evaluate_objective, summarize_context_delta


class ObjectiveRuntime(Protocol):
    """Runtime surface needed by the objective runner."""

    def agent_context(self) -> dict[str, Any]:
        """Return compact planner context."""

    def run_agent_step(self, operator_prompt: str | None = None) -> dict[str, Any]:
        """Run one planner/client action step."""

    def execute_agent_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute one policy action, used for save/load recovery hooks."""


@dataclass(frozen=True)
class ObjectiveRunSettings:
    """Execution bounds for one objective run."""

    max_steps: int = 5
    save_before: bool = True
    recover_on_error: bool = True


class ObjectiveRunner:
    """Runs short objectives with step caps and telemetry-backed scoring."""

    def __init__(self, runtime: ObjectiveRuntime) -> None:
        self._runtime = runtime
        self._stop_event = Event()
        self.last_memory: ObjectiveMemory | None = None

    def request_stop(self) -> None:
        """Ask the active or next objective run to stop."""

        self._stop_event.set()

    def clear_stop(self) -> None:
        """Clear a previous stop request before starting another objective."""

        self._stop_event.clear()

    def run(self, objective: dict[str, Any], *, operator_prompt: str | None = None) -> dict[str, Any]:
        """Run a bounded objective until success, stop, step cap, or error."""

        settings = _settings_from_objective(objective)
        memory = ObjectiveMemory(objective=objective)
        self.last_memory = memory
        self.clear_stop()

        if settings.save_before:
            try:
                self._runtime.execute_agent_action({"action_id": "save_quick", "reason": "checkpoint objective start"})
            except Exception as exc:
                memory.append_step({"kind": "checkpoint_failed", "error": str(exc)})

        initial_context = self._runtime.agent_context()
        initial_score = evaluate_objective(initial_context, objective, agent_steps=0)
        if initial_score["success"]:
            memory.finish()
            return _result("success", objective, memory, initial_score)

        for step_index in range(1, settings.max_steps + 1):
            if self._stop_event.is_set():
                memory.finish()
                return _result("stopped", objective, memory, initial_score)

            before = self._runtime.agent_context()
            try:
                step_result = self._runtime.run_agent_step(operator_prompt=operator_prompt)
            except Exception as exc:
                memory.append_step({"kind": "error", "step": step_index, "error": str(exc)})
                if settings.recover_on_error:
                    self._try_recover(memory)
                memory.finish()
                return _result("error", objective, memory, initial_score, error=str(exc))

            after = self._runtime.agent_context()
            score = evaluate_objective(after, objective, agent_steps=step_index)
            delta = summarize_context_delta(before, after)
            memory.append_step(
                {
                    "kind": "agent_step",
                    "step": step_index,
                    "decision": step_result.get("decision"),
                    "result": step_result.get("result"),
                    "delta": delta,
                    "score": score,
                }
            )
            if step_result.get("decision", {}).get("action_id") == "stop":
                memory.finish()
                return _result("stopped", objective, memory, score)
            if score["success"]:
                memory.finish()
                return _result("success", objective, memory, score)

        final_context = self._runtime.agent_context()
        final_score = evaluate_objective(final_context, objective, agent_steps=settings.max_steps)
        memory.finish()
        return _result("step_limit", objective, memory, final_score)

    def _try_recover(self, memory: ObjectiveMemory) -> None:
        try:
            result = self._runtime.execute_agent_action({"action_id": "load_quick", "reason": "recover objective error"})
        except Exception as exc:
            memory.append_step({"kind": "recovery_failed", "error": str(exc)})
        else:
            memory.append_step({"kind": "recovered", "result": result})


def _settings_from_objective(objective: dict[str, Any]) -> ObjectiveRunSettings:
    return ObjectiveRunSettings(
        max_steps=max(1, min(int(objective.get("max_steps", 5)), 20)),
        save_before=bool(objective.get("save_before", True)),
        recover_on_error=bool(objective.get("recover_on_error", True)),
    )


def _result(
    status: str,
    objective: dict[str, Any],
    memory: ObjectiveMemory,
    score: dict[str, Any],
    *,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": status == "success",
        "status": status,
        "objective": objective,
        "score": score,
        "steps": len([step for step in memory.steps if step.get("kind") == "agent_step"]),
        "memory": {
            "started_at": memory.started_at,
            "completed_at": memory.completed_at,
            "steps": memory.steps,
        },
        "error": error,
    }
