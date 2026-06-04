"""Stable JSON state contracts for runtime telemetry consumers.

Game adapters can expose richer nested data, but `/telemetry`, the web deck,
and later agent context all rely on the small normalized envelope defined here:
schema version, target identity, runtime frame, explicit unavailable sections,
and capability flags derived from those sections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


TELEMETRY_SCHEMA_VERSION = 1
_UNAVAILABLE_REASON = "not_reported"
_REQUIRED_SECTIONS = ("rom", "symbols", "save_blocks", "location", "mode", "camera", "save")


def normalize_telemetry_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe telemetry snapshot with the stable v1 envelope."""

    normalized = _json_safe(snapshot)
    normalized["schema_version"] = TELEMETRY_SCHEMA_VERSION
    normalized.setdefault("game", "unknown")
    normalized.setdefault("revision", "unknown")
    normalized.setdefault("frame", 0)
    normalized["target"] = {
        "game": normalized["game"],
        "revision": normalized["revision"],
    }
    normalized["runtime"] = {
        "frame": normalized["frame"],
    }
    for section in _REQUIRED_SECTIONS:
        normalized.setdefault(section, _unavailable(section))
    normalized["capabilities"] = _capabilities(normalized)
    return normalized


def empty_telemetry_snapshot(frame: int) -> dict[str, Any]:
    """Return an explicit unavailable telemetry snapshot for adapter-less runtimes."""

    return normalize_telemetry_snapshot(
        {
            "game": "unknown",
            "revision": "unknown",
            "frame": frame,
            "status": "unavailable",
        }
    )


def _capabilities(snapshot: dict[str, Any]) -> dict[str, bool]:
    return {
        "symbols": _available(snapshot["symbols"]),
        "location": _available(snapshot["location"]),
        "mode": snapshot["mode"].get("name") not in (None, "unknown"),
        "camera": _available(snapshot["camera"]),
        "save": _available(snapshot["save"]),
        "party": _available(snapshot["save"]) and bool(snapshot["save"].get("party", {}).get("count")),
    }


def _available(value: Any) -> bool:
    return isinstance(value, dict) and value.get("available") is True


def _unavailable(section: str) -> dict[str, Any]:
    return {"available": False, "reason": _UNAVAILABLE_REASON, "section": section}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(nested) for nested in value]
    if isinstance(value, Path):
        return value.name
    return value
