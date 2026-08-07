"""Tests for agent action policy, context, and controls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.runtime.action_executor import ActionExecutor, ActionValidationError
from tools.runtime.agent_context import MAX_RECENT_TRACES, allowed_agent_actions, build_agent_context
from tools.runtime.codex_client import AgentClientDisabled, FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.interaction_policy import AgentActionValidationError
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request
from tools.runtime.trace_recorder import TraceRecorder


def test_action_not_allowed_should_be_rejected() -> None:
    emulator = FakeEmulatorBridge()
    traces = TraceRecorder()
    executor = ActionExecutor(emulator, traces)

    with pytest.raises(ActionValidationError):
        executor.execute({"action": "tap", "button": "power"})

    assert emulator.frame_count == 0
    assert traces.recent()[0]["status"] == "rejected"

def test_malformed_action_frames_should_return_validation_error() -> None:
    response = request(create_app(), "POST", "/action", json={"action": "wait", "frames": "oops"})

    assert response.status_code == 400
    assert response.json()["detail"] == "frames must be an integer"

def test_press_release_actions_should_track_held_buttons() -> None:
    emulator = FakeEmulatorBridge()
    executor = ActionExecutor(emulator, TraceRecorder())

    press = executor.execute({"action": "press", "button": "a"})
    release = executor.execute({"action": "release", "button": "a"})

    assert press["ok"] is True
    assert release["ok"] is True
    assert emulator.pressed_buttons == frozenset()

def test_control_markup_should_expose_accessible_hold_buttons() -> None:
    html = (Path.cwd() / "tools/runtime/static/index.html").read_text(encoding="utf-8")

    assert 'id="input-state" aria-live="polite"' in html
    for button in ("up", "down", "left", "right", "a", "b", "start", "select", "l", "r"):
        assert f'data-button="{button}"' in html
        assert 'aria-pressed="false"' in html
    assert '<script type="module" src="/app.js"></script>' in html

def test_agent_context_should_omit_private_paths_and_hashes() -> None:
    telemetry = {
        "target": {"game": "firered", "revision": "rev1"},
        "runtime": {"frame": 99},
        "rom": {
            "available": True,
            "name": "firered.gba",
            "path": "/home/user/private/firered.gba",
            "sha1": "secret-hash",
            "expected_sha1": "expected-secret",
            "matches_expected": True,
        },
        "symbols": {"available": True, "source": "/home/user/build/pokefirered_rev1.sym"},
        "debug": {"last_snapshot": r"C:\Users\player\private\firered.png"},
        "mode": {"name": "field", "confidence": "medium", "reason": "field_callback"},
        "location": {
            "available": True,
            "map_group": 3,
            "map_num": 0,
            "player_x": 6,
            "player_y": 7,
            "map": {"available": True, "id": "MAP_PALLET_TOWN", "name": "PalletTown"},
        },
        "save": {"available": True, "player": {"available": True, "name": "RED"}},
        "capabilities": {"location": True, "mode": True, "save": True},
    }

    context = build_agent_context(telemetry, [], {"slots": [{"name": "quick", "exists": True, "path": Path("/tmp/quick.ss")}]})
    encoded = json.dumps(context)

    assert context["target"]["game"] == "firered"
    assert context["target"]["rom"] == {"available": True, "name": "firered.gba", "matches_expected": True}
    assert context["state"]["location"]["map_id"] == "MAP_PALLET_TOWN"
    assert context["available_state_slots"] == [{"name": "quick", "exists": True, "updated_at": None}]
    assert "/home/user" not in encoded
    assert r"C:\Users\player" not in encoded
    assert "secret-hash" not in encoded
    assert "expected-secret" not in encoded
    assert "image_base64" not in encoded

def test_agent_context_should_cap_recent_traces() -> None:
    traces = [
        {"id": index, "type": "action", "status": "accepted", "detail": {"action": "tap", "button": "a"}}
        for index in range(20)
    ]

    context = build_agent_context({"frame": 1}, traces, {"slots": []})

    assert len(context["recent_traces"]) == MAX_RECENT_TRACES
    assert context["recent_traces"][0]["id"] == 12
    assert context["size"]["json_bytes"] < 16_000

def test_agent_context_allowed_actions_should_include_safe_affordances() -> None:
    actions = {action["id"]: action for action in allowed_agent_actions()}

    assert actions["inspect"]["type"] == "observe"
    assert actions["wait_short"]["frames"] == 15
    assert actions["tap_a"]["button"] == "a"
    assert actions["hold_up"]["frames"] == 20
    assert actions["save_quick"]["slot"] == "quick"
    assert actions["load_quick"]["slot"] == "quick"
    assert "raw_lua" not in actions

def test_agent_context_endpoint_should_return_context_for_fake_runtime() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "GET", "/agent_context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["target"]["game"] == "unknown"
    assert payload["runtime"]["frame"] == 0
    assert "allowed_actions" in payload

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

def test_fake_emulator_should_capture_snapshot_after_input() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    result = runtime.execute_action({"action": "tap", "button": "a", "frames": 3})
    snapshot = runtime.snapshot()

    assert result["ok"] is True
    assert result["frame"] == 3
    assert snapshot["frame"] == 3
    assert snapshot["mime_type"] == "image/png"
    assert emulator.pressed_buttons == frozenset()
