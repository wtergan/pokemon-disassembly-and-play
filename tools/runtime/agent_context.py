"""Compact, privacy-safe context for planner-facing runtime agents.

The agent context is intentionally smaller than `/telemetry`: it summarizes the
current target, mode, location, save data, recent traces, and action affordances
without exposing local ROM paths, raw screenshots, or large debug payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


AGENT_CONTEXT_SCHEMA_VERSION = 1
MAX_RECENT_TRACES = 8
MAX_CONTEXT_JSON_BYTES = 16_000
_BUTTONS = ("up", "down", "left", "right", "a", "b", "start", "select", "l", "r")


def build_agent_context(
    telemetry: dict[str, Any],
    traces: list[dict[str, Any]],
    states: dict[str, Any],
    *,
    objective: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the compact model-facing runtime context."""

    context = {
        "schema_version": AGENT_CONTEXT_SCHEMA_VERSION,
        "goal": "Make verified progress in Pokemon FireRed one bounded action at a time.",
        "target": _clean(
            {
                "game": telemetry.get("target", {}).get("game", telemetry.get("game", "unknown")),
                "revision": telemetry.get("target", {}).get("revision", telemetry.get("revision", "unknown")),
                "rom": _rom_summary(telemetry.get("rom", {})),
            }
        ),
        "runtime": {
            "frame": telemetry.get("runtime", {}).get("frame", telemetry.get("frame", 0)),
            "capabilities": telemetry.get("capabilities", {}),
        },
        "state": _state_summary(telemetry),
        "objective": objective or {"active": False, "description": None, "step": 0, "max_steps": None},
        "available_state_slots": _state_slots(states),
        "allowed_actions": allowed_agent_actions(),
        "recent_traces": _recent_traces(traces),
        "rules": [
            "Choose one allowed action at a time.",
            "Prefer wait_short when mode or telemetry is unavailable.",
            "Use save_quick before risky exploration and load_quick only for recovery.",
            "Do not request raw emulator, memory-write, filesystem, or unlisted actions.",
            "Stop after success, repeated failure, or unclear state.",
        ],
        "output_contract": {
            "format": "json",
            "required": ["action_id", "reason"],
            "optional": ["button", "frames", "slot"],
        },
    }
    context["size"] = {"json_bytes": len(json.dumps(context, separators=(",", ":"), ensure_ascii=False))}
    context["truncated"] = context["size"]["json_bytes"] > MAX_CONTEXT_JSON_BYTES
    return context


def allowed_agent_actions() -> list[dict[str, Any]]:
    """Return action affordances exposed to the planner before policy execution."""

    actions: list[dict[str, Any]] = [
        {"id": "inspect", "type": "observe", "description": "Re-read agent context without pressing inputs."},
        {"id": "wait_short", "type": "wait", "frames": 15, "description": "Wait briefly and observe again."},
        {"id": "save_quick", "type": "save_state", "slot": "quick", "description": "Save a runtime-owned quick checkpoint."},
        {"id": "load_quick", "type": "load_state", "slot": "quick", "description": "Restore the quick checkpoint when recovery is needed."},
        {"id": "stop", "type": "control", "description": "Stop the current objective loop."},
    ]
    actions.extend(
        {"id": f"tap_{button}", "type": "tap", "button": button, "frames": 12, "description": f"Tap {button.upper()}."}
        for button in _BUTTONS
    )
    actions.extend(
        {
            "id": f"hold_{button}",
            "type": "hold",
            "button": button,
            "frames": 20,
            "description": f"Hold {button.upper()} for a short bounded interval.",
        }
        for button in ("up", "down", "left", "right", "a", "b")
    )
    return actions


def _state_summary(telemetry: dict[str, Any]) -> dict[str, Any]:
    save = telemetry.get("save", {})
    location = telemetry.get("location", {})
    return _clean(
        {
            "mode": _mode_summary(telemetry.get("mode", {})),
            "location": _location_summary(location),
            "player": _player_summary(location, save.get("player", {})),
            "party": _party_summary(save.get("party", {})),
            "bag": _bag_summary(save.get("bag_pockets", {})),
            "events": {
                "flags": save.get("flags", {}),
                "vars": save.get("vars", {}),
            },
            "symbols": telemetry.get("symbols", {}),
        }
    )


def _mode_summary(mode: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": mode.get("name", "unknown"),
        "confidence": mode.get("confidence"),
        "reason": mode.get("reason"),
    }


def _location_summary(location: dict[str, Any]) -> dict[str, Any]:
    map_context = location.get("map", {})
    return {
        "available": location.get("available") is True,
        "reason": location.get("reason"),
        "map_group": location.get("map_group"),
        "map_num": location.get("map_num"),
        "map_id": map_context.get("id"),
        "map_name": map_context.get("name"),
        "player_x": location.get("player_x"),
        "player_y": location.get("player_y"),
    }


def _player_summary(location: dict[str, Any], player: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": player.get("available") is True,
        "name": player.get("name"),
        "gender": player.get("gender"),
        "position": {"x": location.get("player_x"), "y": location.get("player_y")},
        "play_time": player.get("play_time"),
    }


def _party_summary(party: dict[str, Any]) -> dict[str, Any]:
    members = []
    for member in (party.get("members") or [])[:6]:
        members.append(
            {
                "index": member.get("index"),
                "available": member.get("available") is True,
                "nickname": member.get("nickname"),
                "species": member.get("species"),
                "level": member.get("level"),
                "hp": member.get("hp"),
                "max_hp": member.get("max_hp"),
                "status": member.get("status"),
            }
        )
    return {"count": party.get("count", 0), "capacity": party.get("capacity", 6), "members": members}


def _bag_summary(pockets: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "used_slots": pocket.get("used_slots"),
            "capacity": pocket.get("capacity"),
            "quantity_available": pocket.get("quantity_available"),
        }
        for name, pocket in pockets.items()
        if isinstance(pocket, dict)
    }


def _rom_summary(rom: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": rom.get("available") is True,
        "name": rom.get("name"),
        "matches_expected": rom.get("matches_expected"),
    }


def _state_slots(states: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": slot.get("name"), "exists": slot.get("exists"), "updated_at": slot.get("updated_at")}
        for slot in states.get("slots", [])[:10]
    ]


def _recent_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for trace in traces[-MAX_RECENT_TRACES:]:
        detail = trace.get("detail", {})
        compact.append(
            {
                "id": trace.get("id"),
                "type": trace.get("type"),
                "status": trace.get("status"),
                "action": detail.get("action"),
                "button": detail.get("button"),
                "slot": detail.get("slot"),
                "frame": detail.get("frame"),
                "error": detail.get("error"),
            }
        )
    return compact


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean(nested) for key, nested in value.items() if not _is_private_key(str(key))}
    if isinstance(value, list):
        return [_clean(nested) for nested in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def _is_private_key(key: str) -> bool:
    normalized = key.lower()
    return normalized.endswith("path") or normalized in {"sha1", "expected_sha1", "image_base64"}


def _sanitize_string(value: str) -> str:
    if "/" in value or "\\" in value:
        return value.replace("\\", "/").rstrip("/").split("/")[-1]
    return value
