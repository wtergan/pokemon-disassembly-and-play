"""Validate objective success conditions against observed runtime state.

Action-count and frame-count criteria remain available for labelled smoke
checks. Gameplay objectives must combine a mode, known map, and position check;
position transitions compare the state before and after one planner action.
"""

from __future__ import annotations

from typing import Any


_SMOKE_CRITERIA = {"agent_steps_at_least", "runtime_frame_at_least"}
_SEMANTIC_CRITERIA = {"mode_is", "map_is", "position_is", "position_changed"}
_ALLOWED_CRITERIA = _SMOKE_CRITERIA | _SEMANTIC_CRITERIA


def validate_objective(objective: dict[str, Any]) -> dict[str, Any]:
    """Validate objective criteria before saving a checkpoint or asking the planner."""

    success = objective.get("success")
    if not isinstance(success, dict) or not success:
        return {"valid": False, "reason": "no_success_criteria"}

    unknown = sorted(set(success) - _ALLOWED_CRITERIA)
    if unknown:
        return {"valid": False, "reason": "unsupported_success_criteria", "unknown": unknown}

    semantic = bool(set(success) & _SEMANTIC_CRITERIA)
    if semantic:
        missing = []
        if not _nonempty_string(success.get("mode_is")):
            missing.append("mode_is")
        if not _nonempty_string(success.get("map_is")):
            missing.append("map_is")
        position_is = success.get("position_is")
        has_position_target = (
            isinstance(position_is, dict)
            and _is_coordinate(position_is.get("x"))
            and _is_coordinate(position_is.get("y"))
        )
        has_position_transition = success.get("position_changed") is True
        if "position_is" in success and not has_position_target:
            missing.append("position_is{x,y}")
        if "position_changed" in success and not has_position_transition:
            missing.append("position_changed=true")
        if not has_position_target and not has_position_transition:
            missing.append("position_is or position_changed")
        if missing:
            return {
                "valid": False,
                "reason": "incomplete_semantic_criteria",
                "classification": "semantic",
                "missing": missing,
            }

    for name in _SMOKE_CRITERIA & set(success):
        value = success[name]
        if not _is_nonnegative_integer(value):
            return {
                "valid": False,
                "reason": "invalid_smoke_criterion",
                "classification": "smoke",
                "criterion": name,
            }

    return {"valid": True, "classification": "semantic" if semantic else "smoke"}


def evaluate_objective(
    context: dict[str, Any],
    objective: dict[str, Any],
    *,
    agent_steps: int = 0,
    before_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate all requested success conditions conjunctively.

    Legacy action-count and frame-count objectives retain their existing result
    shape. The runner labels those bounded smoke checks separately from
    semantic objectives, whose success depends on available map and position
    telemetry in addition to the requested mode.
    """

    validation = validate_objective(objective)
    if not validation["valid"]:
        return {"success": False, **{key: value for key, value in validation.items() if key != "valid"}}

    success = objective["success"]
    semantic = validation["classification"] == "semantic"
    checks: dict[str, bool] = {}

    if "agent_steps_at_least" in success:
        checks["agent_steps_at_least"] = agent_steps >= int(success["agent_steps_at_least"])
    if "runtime_frame_at_least" in success:
        frame = int(context.get("runtime", {}).get("frame", 0))
        checks["runtime_frame_at_least"] = frame >= int(success["runtime_frame_at_least"])

    if semantic:
        state = context.get("state", {})
        location = state.get("location", {})
        map_context = location.get("map") or {}
        position = _position(location)
        location_available = location.get("available") is True
        checks["location_available"] = location_available
        checks["coordinates_available"] = position is not None
        checks["mode_is"] = _matches(state.get("mode", {}).get("name"), success["mode_is"])
        checks["map_is"] = _matches_map(location, map_context, success["map_is"])

        if "position_is" in success:
            target = success["position_is"]
            checks["position_is"] = position == (target["x"], target["y"])
        if success.get("position_changed") is True:
            checks["position_changed"] = _position_changed_on_same_map(before_context, context, success["map_is"])

    succeeded = all(checks.values())
    if not semantic:
        # Preserve the exact legacy score shape consumed by existing smoke tests.
        if "agent_steps_at_least" in success:
            target = int(success["agent_steps_at_least"])
            return {
                "success": succeeded,
                "reason": "agent_steps_at_least",
                "observed": agent_steps,
                "target": target,
            }
        target = int(success["runtime_frame_at_least"])
        frame = int(context.get("runtime", {}).get("frame", 0))
        return {
            "success": succeeded,
            "reason": "runtime_frame_at_least",
            "observed": frame,
            "target": target,
        }

    return {
        "success": succeeded,
        "reason": "semantic_state_verified" if succeeded else "semantic_state_not_verified",
        "classification": "semantic",
        "checks": checks,
    }


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


def _position(location: dict[str, Any]) -> tuple[int, int] | None:
    if location.get("available") is not True:
        return None
    x, y = location.get("player_x"), location.get("player_y")
    if not _is_coordinate(x) or not _is_coordinate(y):
        return None
    return x, y


def _position_changed_on_same_map(
    before_context: dict[str, Any] | None,
    after_context: dict[str, Any],
    target_map: str,
) -> bool:
    if before_context is None:
        return False
    before_state = before_context.get("state", {})
    before_location = before_state.get("location", {})
    after_state = after_context.get("state", {})
    after_location = after_state.get("location", {})
    before_map_context = before_location.get("map") or {}
    after_map_context = after_location.get("map") or {}
    before_position = _position(before_location)
    after_position = _position(after_location)
    if before_position is None or after_position is None:
        return False
    return (
        _matches_map(before_location, before_map_context, target_map)
        and _matches_map(after_location, after_map_context, target_map)
        and before_position != after_position
    )


def _matches_map(location: dict[str, Any], map_context: dict[str, Any], target: str) -> bool:
    if location.get("available") is not True:
        return False
    candidates = (location.get("map_id"), location.get("map_name"), map_context.get("id"), map_context.get("name"))
    return any(_matches(candidate, target) for candidate in candidates)


def _matches(observed: Any, target: str) -> bool:
    return isinstance(observed, str) and observed.casefold() == target.casefold()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_coordinate(value: Any) -> bool:
    return type(value) is int


def _is_nonnegative_integer(value: Any) -> bool:
    return type(value) is int and value >= 0
