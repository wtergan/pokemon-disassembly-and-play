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
from .objective_scoring import evaluate_objective, summarize_context_delta, validate_objective


class ObjectiveRuntime(Protocol):
    """Runtime surface needed by the objective runner."""

    def agent_context(self, objective: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return compact planner context."""

    def run_agent_step(
        self,
        operator_prompt: str | None = None,
        objective: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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

        validation = validate_objective(objective)
        if not validation["valid"]:
            memory.finish()
            score = {"success": False, **{key: value for key, value in validation.items() if key != "valid"}}
            return _result("invalid_objective", objective, memory, score)

        if settings.save_before:
            try:
                checkpoint = self._runtime.execute_agent_action(
                    {"action_id": "save_quick", "reason": "checkpoint objective start"}
                )
                if checkpoint.get("ok") is not True:
                    raise RuntimeError("starting checkpoint did not report success")
            except Exception as exc:
                memory.append_step({"kind": "checkpoint_failed", "error": str(exc)})
                memory.finish()
                score = {
                    "success": False,
                    "reason": "checkpoint_failed",
                    "classification": validation["classification"],
                }
                return _result("checkpoint_failed", objective, memory, score, error=str(exc))

        initial_context = self._runtime.agent_context()
        initial_score = evaluate_objective(initial_context, objective, agent_steps=0)
        if initial_score["success"]:
            memory.finish()
            return _result("success", objective, memory, initial_score)

        last_before_context: dict[str, Any] | None = None
        for step_index in range(1, settings.max_steps + 1):
            if self._stop_event.is_set():
                memory.finish()
                return _result("stopped", objective, memory, initial_score)

            before = self._runtime.agent_context()
            last_before_context = before
            active_objective = _active_objective(objective, step_index, settings.max_steps, initial_context)
            try:
                step_result = self._runtime.run_agent_step(
                    operator_prompt=operator_prompt,
                    objective=active_objective,
                )
            except Exception as exc:
                memory.append_step({"kind": "error", "step": step_index, "error": str(exc)})
                if settings.recover_on_error and settings.save_before:
                    self._try_recover(memory)
                memory.finish()
                return _result("error", objective, memory, initial_score, error=str(exc))

            after = self._runtime.agent_context()
            score = evaluate_objective(after, objective, agent_steps=step_index, before_context=before)
            delta = summarize_context_delta(before, after)
            memory.append_step(
                {
                    "kind": "agent_step",
                    "step": step_index,
                    "decision": step_result.get("decision"),
                    "result": step_result.get("result"),
                    "delta": delta,
                    "score": score,
                    "verification_class": _verification_class(score),
                }
            )
            if step_result.get("decision", {}).get("action_id") == "stop":
                memory.finish()
                return _result("stopped", objective, memory, score)
            if score["success"]:
                memory.finish()
                return _result("success", objective, memory, score)

        final_context = self._runtime.agent_context()
        final_score = evaluate_objective(
            final_context,
            objective,
            agent_steps=settings.max_steps,
            before_context=last_before_context,
        )
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


def _active_objective(objective: dict[str, Any], step: int, max_steps: int, initial_context: dict[str, Any]) -> dict[str, Any]:
    """Add run progress for the planner; the agent service allowlists fields."""

    state = initial_context.get("state", {})
    location = state.get("location", {})
    return {
        **objective, "step": step, "max_steps": max_steps,
        "starting_state": {
            "mode": state.get("mode", {}).get("name"),
            "map_id": location.get("map_id"),
            "player_x": location.get("player_x"),
            "player_y": location.get("player_y"),
        },
    }


def _verification_class(score: dict[str, Any]) -> str:
    """Distinguish semantic state proof from legacy bounded smoke criteria."""

    classification = score.get("classification")
    if classification in {"semantic", "smoke"}:
        return classification
    if score.get("reason") in {"agent_steps_at_least", "runtime_frame_at_least"}:
        return "smoke"
    return "unverified"


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
        "verification_class": _verification_class(score),
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
