"""Objective success checks and telemetry delta summaries for agent runs."""

from __future__ import annotations

from typing import Any


def evaluate_objective(context: dict[str, Any], objective: dict[str, Any]) -> dict[str, Any]:
    """Evaluate supported objective success criteria against agent context."""

    success = objective.get("success") or {}
    if not success:
        return {"success": False, "reason": "no_success_criteria"}

    runtime_frame_at_least = success.get("runtime_frame_at_least")
    if runtime_frame_at_least is not None:
        frame = int(context.get("runtime", {}).get("frame", 0))
        target = int(runtime_frame_at_least)
        return {
            "success": frame >= target,
            "reason": "runtime_frame_at_least",
            "observed": frame,
            "target": target,
        }

    mode_is = success.get("mode_is")
    if mode_is is not None:
        mode = context.get("state", {}).get("mode", {}).get("name")
        return {"success": mode == mode_is, "reason": "mode_is", "observed": mode, "target": mode_is}

    return {"success": False, "reason": "unsupported_success_criteria"}


def summarize_context_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return compact evidence describing what changed after one action."""

    before_runtime = before.get("runtime", {})
    after_runtime = after.get("runtime", {})
    before_state = before.get("state", {})
    after_state = after.get("state", {})
    before_location = before_state.get("location", {})
    after_location = after_state.get("location", {})
    return {
        "frame_before": before_runtime.get("frame"),
        "frame_after": after_runtime.get("frame"),
        "frame_delta": int(after_runtime.get("frame") or 0) - int(before_runtime.get("frame") or 0),
        "mode_before": before_state.get("mode", {}).get("name"),
        "mode_after": after_state.get("mode", {}).get("name"),
        "map_before": before_location.get("map_id"),
        "map_after": after_location.get("map_id"),
        "position_before": {"x": before_location.get("player_x"), "y": before_location.get("player_y")},
        "position_after": {"x": after_location.get("player_x"), "y": after_location.get("player_y")},
    }
