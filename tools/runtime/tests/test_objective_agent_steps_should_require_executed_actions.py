"""Behavior coverage for action-count objective completion criteria."""

from __future__ import annotations

from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore


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
