from __future__ import annotations

import json
from pathlib import Path

from tools.runtime.agent_context import MAX_RECENT_TRACES, allowed_agent_actions, build_agent_context
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request


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
