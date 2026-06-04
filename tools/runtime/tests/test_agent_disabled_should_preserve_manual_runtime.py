from __future__ import annotations

import pytest

from tools.runtime.codex_client import AgentClientDisabled, FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore


def test_agent_disabled_should_preserve_manual_runtime() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    with pytest.raises(AgentClientDisabled):
        runtime.run_agent_step()

    manual = runtime.execute_action({"action": "tap", "button": "a", "frames": 3})

    assert manual["ok"] is True
    assert manual["frame"] == 3
    assert runtime.agent_status()["client"]["mode"] == "disabled"


def test_fake_agent_client_should_execute_one_policy_step() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)
    runtime.configure_agent_client(FakeAgentClient([{"action_id": "tap_a", "reason": "advance dialogue"}]))

    result = runtime.run_agent_step(operator_prompt="try a safe action")

    assert result["ok"] is True
    assert result["decision"]["action_id"] == "tap_a"
    assert result["result"]["result"]["frame"] == 12
    assert emulator.frame_count == 12
    assert runtime.agent_status()["step_count"] == 1


def test_fake_agent_client_should_reject_unadvertised_action() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())
    runtime.configure_agent_client(FakeAgentClient([{"action_id": "raw_lua", "reason": "do unsafe thing"}]))

    with pytest.raises(RuntimeError, match="unsupported action"):
        runtime.run_agent_step()

    assert runtime.agent_status()["last_error"] == "planner chose unsupported action: 'raw_lua'"
