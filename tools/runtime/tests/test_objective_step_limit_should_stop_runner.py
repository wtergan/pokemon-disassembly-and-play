from __future__ import annotations

from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore


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
