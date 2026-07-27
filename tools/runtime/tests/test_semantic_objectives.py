"""Behavior tests for planner-visible, state-verified objectives."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.runtime.agent_service import AgentService
from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.objective_runner import ObjectiveRunner
from tools.runtime.objective_scoring import evaluate_objective
from tools.runtime.runtime_core import RuntimeCore


FIELD_OBJECTIVE = {
    "description": "Move one tile in Pallet Town",
    "max_steps": 2,
    "success": {
        "mode_is": "field",
        "map_is": "MAP_PALLET_TOWN",
        "position_changed": True,
    },
}


def _context(
    *,
    mode: str = "field",
    available: bool = True,
    map_id: str | None = "MAP_PALLET_TOWN",
    x: int | None = 4,
    y: int | None = 7,
) -> dict[str, Any]:
    return {
        "runtime": {"frame": 10},
        "state": {
            "mode": {"name": mode},
            "location": {
                "available": available,
                "map_id": map_id,
                "map_name": "Pallet Town" if map_id == "MAP_PALLET_TOWN" else None,
                "player_x": x,
                "player_y": y,
            },
        },
    }


class _ObjectiveRuntime:
    def __init__(self, contexts: list[dict[str, Any]], *, checkpoint_error: str | None = None, step_error: str | None = None):
        self.contexts = contexts
        self.checkpoint_error = checkpoint_error
        self.step_error = step_error
        self.actions: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.context_index = 0
        self.context_objectives: list[dict[str, Any] | None] = []

    def agent_context(self, objective: dict[str, Any] | None = None) -> dict[str, Any]:
        self.context_objectives.append(objective)
        context = self.contexts[min(self.context_index, len(self.contexts) - 1)]
        self.context_index += 1
        return context

    def run_agent_step(
        self,
        operator_prompt: str | None = None,
        objective: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.steps.append({"operator_prompt": operator_prompt, "objective": objective})
        if self.step_error is not None:
            raise RuntimeError(self.step_error)
        return {"decision": {"action_id": "tap_right"}, "result": {"ok": True}}

    def execute_agent_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.actions.append(payload)
        if payload["action_id"] == "save_quick" and self.checkpoint_error is not None:
            raise RuntimeError(self.checkpoint_error)
        return {"ok": True, "action_id": payload["action_id"]}


def test_semantic_objective_should_require_mode_map_and_position_criteria() -> None:
    score = evaluate_objective(
        _context(),
        {"success": {"mode_is": "field"}},
        agent_steps=1,
    )

    assert score["success"] is False
    assert score["classification"] == "semantic"
    assert score["reason"] == "incomplete_semantic_criteria"


def test_semantic_objective_should_require_available_location_and_coordinates() -> None:
    before = _context(x=3)
    unavailable_after = _context(available=False, x=4)

    unavailable_score = evaluate_objective(
        unavailable_after,
        FIELD_OBJECTIVE,
        before_context=before,
    )
    missing_coordinate_score = evaluate_objective(
        _context(x=None),
        {"success": {"mode_is": "field", "map_is": "MAP_PALLET_TOWN", "position_is": {"x": 4, "y": 7}}},
    )

    assert unavailable_score["success"] is False
    assert unavailable_score["checks"]["location_available"] is False
    assert missing_coordinate_score["success"] is False
    assert missing_coordinate_score["checks"]["coordinates_available"] is False


def test_semantic_objective_should_require_all_state_checks_and_a_position_transition() -> None:
    before = _context(x=3, y=7)
    moved = _context(x=4, y=7)

    score = evaluate_objective(moved, FIELD_OBJECTIVE, before_context=before)
    wrong_mode = evaluate_objective(_context(mode="menu", x=4, y=7), FIELD_OBJECTIVE, before_context=before)
    wrong_map = evaluate_objective(
        _context(map_id="MAP_VIRIDIAN_CITY", x=4, y=7),
        FIELD_OBJECTIVE,
        before_context=before,
    )
    unchanged = evaluate_objective(before, FIELD_OBJECTIVE, before_context=before)

    assert score["success"] is True
    assert score["classification"] == "semantic"
    assert wrong_mode["success"] is False
    assert wrong_map["success"] is False
    assert unchanged["success"] is False
    assert unchanged["checks"]["position_changed"] is False


def test_semantic_objective_should_not_claim_transition_without_before_state() -> None:
    score = evaluate_objective(_context(x=4), FIELD_OBJECTIVE)

    assert score["success"] is False
    assert score["checks"]["position_changed"] is False


def test_objective_runner_should_claim_semantic_success_after_verified_tile_change() -> None:
    runtime = _ObjectiveRuntime([_context(x=3, y=7), _context(x=3, y=7), _context(x=4, y=7)])
    runner = ObjectiveRunner(runtime)

    result = runner.run(FIELD_OBJECTIVE, operator_prompt="Move one tile to the right.")

    assert result["status"] == "success"
    assert result["verification_class"] == "semantic"
    assert result["steps"] == 1
    assert result["memory"]["steps"][-1]["score"]["checks"]["position_changed"] is True
    assert runtime.steps[0]["objective"]["step"] == 1


def test_smoke_objectives_should_keep_legacy_success_checks_labeled() -> None:
    action_score = evaluate_objective(
        _context(),
        {"success": {"agent_steps_at_least": 2}},
        agent_steps=2,
    )
    frame_score = evaluate_objective(
        {"runtime": {"frame": 15}},
        {"success": {"runtime_frame_at_least": 15}},
    )

    assert action_score == {
        "success": True,
        "reason": "agent_steps_at_least",
        "observed": 2,
        "target": 2,
    }
    assert frame_score == {
        "success": True,
        "reason": "runtime_frame_at_least",
        "observed": 15,
        "target": 15,
    }
    smoke_result = ObjectiveRunner(_ObjectiveRuntime([_context()])).run(
        {"success": {"agent_steps_at_least": 0}}
    )
    assert smoke_result["verification_class"] == "smoke"


def test_objective_should_reach_planner_context_as_an_allowlisted_summary(tmp_path: Path) -> None:
    runtime = RuntimeCore(
        FakeEmulatorBridge(),
        telemetry_reader=lambda emulator: {"frame": emulator.frame_count, "mode": {"name": "field"}},
        state_dir=tmp_path,
    )
    client = FakeAgentClient([{"action_id": "wait_short", "reason": "observe"}])
    runtime.configure_agent_client(client)
    objective = {
        **FIELD_OBJECTIVE,
        "description": "Move up/down and avoid /home/player/private.sav",
        "private_path": "/home/player/private.sav",
        "unrecognized": "must not be forwarded",
    }

    runtime.run_agent_step(operator_prompt="Wait for one observation.", objective=objective)

    planner_objective = client.calls[0]["context"]["objective"]
    assert planner_objective["active"] is True
    assert planner_objective["description"] == "Move up/down and avoid [local path]"
    assert planner_objective["success"] == FIELD_OBJECTIVE["success"]
    assert "private_path" not in planner_objective
    assert "unrecognized" not in planner_objective
    assert client.calls[0]["operator_prompt"] == "Wait for one observation."


def test_semantic_objective_should_reach_planner_and_verify_its_resulting_state(tmp_path: Path) -> None:
    def telemetry_reader(emulator: FakeEmulatorBridge) -> dict[str, Any]:
        return {
            "frame": emulator.frame_count,
            "mode": {"name": "field"},
            "location": {
                "available": True,
                "map_group": 3,
                "map_num": 0,
                "player_x": 3 if emulator.frame_count == 0 else 4,
                "player_y": 7,
                "map": {"available": True, "id": "MAP_PALLET_TOWN", "name": "Pallet Town"},
            },
        }

    runtime = RuntimeCore(FakeEmulatorBridge(), telemetry_reader=telemetry_reader, state_dir=tmp_path)
    client = FakeAgentClient([{"action_id": "tap_right", "reason": "take one step"}])
    runtime.configure_agent_client(client)

    result = runtime.run_objective(FIELD_OBJECTIVE, operator_prompt="Move one tile to the right.")

    assert result["status"] == "success"
    assert result["verification_class"] == "semantic"
    assert client.calls[0]["context"]["objective"]["active"] is True
    assert client.calls[0]["context"]["objective"]["step"] == 1
    assert client.calls[0]["context"]["objective"]["starting_state"] == {
        "mode": "field", "map_id": "MAP_PALLET_TOWN", "player_x": 3, "player_y": 7,
    }
    assert result["memory"]["steps"][-1]["score"]["checks"]["position_changed"] is True


def test_checkpoint_failure_should_stop_before_planner_or_action() -> None:
    runtime = _ObjectiveRuntime([_context()], checkpoint_error="savestate unavailable")
    runner = ObjectiveRunner(runtime)

    result = runner.run(FIELD_OBJECTIVE, operator_prompt="Move one tile.")

    assert result["status"] == "checkpoint_failed"
    assert result["error"] == "savestate unavailable"
    assert runtime.steps == []
    assert [action["action_id"] for action in runtime.actions] == ["save_quick"]
    assert not any(step["kind"] == "recovered" for step in result["memory"]["steps"])


def test_objective_without_new_checkpoint_should_not_recover_from_stale_quick_state() -> None:
    runtime = _ObjectiveRuntime([_context()], step_error="planner failed")
    runner = ObjectiveRunner(runtime)

    result = runner.run(
        {**FIELD_OBJECTIVE, "save_before": False},
        operator_prompt="Move one tile.",
    )

    assert result["status"] == "error"
    assert result["error"] == "planner failed"
    assert runtime.actions == []

