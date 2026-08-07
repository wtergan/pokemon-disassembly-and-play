"""Tests for objective execution and completion rules."""

from __future__ import annotations

from pathlib import Path

from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request


def test_agent_status_endpoint_should_preserve_disabled_default() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "GET", "/agent/status")

    assert response.status_code == 200
    assert response.json()["client"]["mode"] == "disabled"

def test_agent_step_endpoint_should_run_fake_client(tmp_path: Path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient([{"action_id": "tap_a", "reason": "advance"}]))

    response = request(create_app(runtime), "POST", "/agent/step", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["action_id"] == "tap_a"
    assert payload["result"]["result"]["frame"] == 12

def test_agent_objective_endpoint_should_run_bounded_goal(tmp_path: Path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient())

    response = request(
        create_app(runtime),
        "POST",
        "/agent/objective",
        json={"objective": {"description": "wait", "max_steps": 1, "success": {"runtime_frame_at_least": 15}}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_agent_step_endpoint_should_report_disabled_client() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "POST", "/agent/step", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "agent planning is disabled"

# Behavior coverage for action-count objective completion criteria.


def test_objective_agent_steps_should_require_each_executed_action(tmp_path) -> None:
    """Avoid passing a planner smoke solely because visible mGBA keeps advancing."""

    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(
        FakeAgentClient(
            [
                {"action_id": "tap_a", "reason": "first bounded input"},
                {"action_id": "tap_start", "reason": "second bounded input"},
                {"action_id": "tap_right", "reason": "third bounded input"},
            ]
        )
    )

    result = runtime.run_objective(
        {
            "max_steps": 3,
            "success": {"agent_steps_at_least": 3},
        }
    )

    assert result["ok"] is True
    assert result["status"] == "success"
    assert result["steps"] == 3
    assert result["score"] == {
        "success": True,
        "reason": "agent_steps_at_least",
        "observed": 3,
        "target": 3,
    }

def test_objective_delta_missing_should_not_claim_success(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(
        FakeAgentClient(
            [
                {"action_id": "inspect", "reason": "look once"},
                {"action_id": "inspect", "reason": "look again"},
            ]
        )
    )

    result = runtime.run_objective(
        {
            "description": "do not infer progress from action count",
            "max_steps": 2,
            "success": {"runtime_frame_at_least": 1},
        }
    )

    assert result["ok"] is False
    assert result["status"] == "step_limit"
    assert result["steps"] == 2
    assert all(step["delta"]["frame_delta"] == 0 for step in result["memory"]["steps"] if step["kind"] == "agent_step")

def test_objective_step_limit_should_stop_runner(tmp_path) -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator, state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient())

    result = runtime.run_objective(
        {
            "description": "wait for a distant frame",
            "max_steps": 2,
            "success": {"runtime_frame_at_least": 100},
        }
    )

    assert result["ok"] is False
    assert result["status"] == "step_limit"
    assert result["steps"] == 2
    assert emulator.frame_count == 30
    assert result["score"]["success"] is False

def test_objective_should_succeed_only_when_context_matches_criteria(tmp_path) -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator, state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient())

    result = runtime.run_objective(
        {
            "description": "wait for next frame interval",
            "max_steps": 3,
            "success": {"runtime_frame_at_least": 15},
        }
    )

    assert result["ok"] is True
    assert result["status"] == "success"
    assert result["steps"] == 1
    assert result["memory"]["steps"][-1]["delta"]["frame_delta"] == 15

def test_objective_stop_action_should_stop_runner(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient([{"action_id": "stop", "reason": "done"}]))

    result = runtime.run_objective(
        {
            "description": "stop on planner request",
            "max_steps": 3,
            "success": {"runtime_frame_at_least": 999},
        }
    )

    assert result["ok"] is False
    assert result["status"] == "stopped"
    assert result["steps"] == 1
