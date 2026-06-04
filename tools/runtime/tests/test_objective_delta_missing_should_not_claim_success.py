from __future__ import annotations

from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore


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
