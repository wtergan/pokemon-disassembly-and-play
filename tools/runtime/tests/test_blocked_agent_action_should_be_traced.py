from __future__ import annotations

import pytest

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.interaction_policy import AgentActionValidationError
from tools.runtime.runtime_core import RuntimeCore


def test_blocked_agent_action_should_be_traced_without_input() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    with pytest.raises(AgentActionValidationError, match="unsupported agent action"):
        runtime.execute_agent_action({"action_id": "raw_lua", "reason": "try unsupported command"})

    traces = runtime.recent_traces()
    assert emulator.frame_count == 0
    assert [trace["status"] for trace in traces] == ["proposed", "rejected"]
    assert traces[-1]["type"] == "agent_action"
    assert traces[-1]["detail"]["action_id"] == "raw_lua"


def test_agent_action_override_should_be_rejected() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())

    with pytest.raises(AgentActionValidationError, match="button must match advertised action"):
        runtime.execute_agent_action({"action_id": "tap_a", "button": "power", "reason": "press a button"})

    assert runtime.recent_traces()[-1]["status"] == "rejected"


def test_allowed_agent_tap_should_execute_bounded_runtime_action() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    result = runtime.execute_agent_action({"action_id": "tap_a", "reason": "advance one prompt"})

    assert result["ok"] is True
    assert result["action_id"] == "tap_a"
    assert result["status"] == "completed"
    assert result["result"]["frame"] == 12
    assert emulator.frame_count == 12
    assert emulator.pressed_buttons == frozenset()
    assert [trace["status"] for trace in runtime.recent_traces()] == [
        "proposed",
        "validated",
        "accepted",
        "executed",
    ]


def test_quick_state_agent_actions_should_use_contained_runtime_slot(tmp_path) -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator, state_dir=tmp_path)

    save = runtime.execute_agent_action({"action_id": "save_quick", "reason": "checkpoint before moving"})
    runtime.execute_agent_action({"action_id": "wait_short", "reason": "advance after checkpoint"})
    load = runtime.execute_agent_action({"action_id": "load_quick", "reason": "recover checkpoint"})

    assert save["ok"] is True
    assert load["ok"] is True
    assert emulator.frame_count == 0
    assert (tmp_path / "quick.ss").exists()


def test_inspect_and_stop_agent_actions_should_not_advance_frames() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    inspect = runtime.execute_agent_action({"action_id": "inspect", "reason": "state unclear"})
    stop = runtime.execute_agent_action({"action_id": "stop", "reason": "objective complete"})

    assert inspect["status"] == "observed"
    assert stop["status"] == "stopped"
    assert emulator.frame_count == 0
