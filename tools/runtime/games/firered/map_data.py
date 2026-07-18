"""FireRed map and layout metadata registry.

The registry loads `pret/pokefirered` JSON map assets into a compact lookup used
by runtime telemetry. Runtime map group/number values come from
`data/maps/map_groups.json`; map metadata comes from `data/maps/*/map.json`; and
dimensions/layout file paths come from `data/layouts/layouts.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FireRedMapRegistry:
    """Lookup for FireRed map metadata by id or runtime group/number."""

    maps_by_id: dict[str, dict[str, Any]]
    layouts_by_id: dict[str, dict[str, Any]]
    id_by_group_number: dict[tuple[int, int], str]

    def describe_map_id(self, map_id: str) -> dict[str, Any]:
        """Return compact metadata for `map_id` or an unavailable payload."""

        map_data = self.maps_by_id.get(map_id)
        if map_data is None:
            return {"available": False, "reason": "unknown_map", "map_id": map_id}
        group_number = _find_group_number(self.id_by_group_number, map_id)
        return self._describe(map_data, group_number)

    def describe_location(self, map_group: int, map_num: int, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        """Return compact metadata for a runtime map group/number."""

        map_id = self.id_by_group_number.get((map_group, map_num))
        if map_id is None:
            return {
                "available": False,
                "reason": "unknown_group_number",
                "map_group": map_group,
                "map_num": map_num,
            }
        map_data = self.maps_by_id[map_id]
        description = self._describe(map_data, (map_group, map_num))
        if x is not None and y is not None:
            description["position"] = self._describe_position(map_data, x, y)
        return description

    def _describe(self, map_data: dict[str, Any], group_number: tuple[int, int] | None) -> dict[str, Any]:
        layout = self.layouts_by_id.get(str(map_data.get("layout", "")))
        payload: dict[str, Any] = {
            "available": True,
            "id": map_data["id"],
            "name": map_data["name"],
            "layout_id": map_data.get("layout"),
            "map_type": map_data.get("map_type"),
            "region_map_section": map_data.get("region_map_section"),
            "connections": map_data.get("connections", []),
            "warps": map_data.get("warp_events", []),
            "object_events": map_data.get("object_events", []),
            "coord_events": map_data.get("coord_events", []),
            "bg_events": map_data.get("bg_events", []),
        }
        if group_number is not None:
            payload["map_group"], payload["map_num"] = group_number
        if layout is not None:
            payload["layout"] = {
                "id": layout["id"],
                "name": layout.get("name"),
                "width": layout.get("width"),
                "height": layout.get("height"),
                "blockdata_filepath": layout.get("blockdata_filepath"),
                "border_filepath": layout.get("border_filepath"),
            }
        return payload

    def _describe_position(self, map_data: dict[str, Any], x: int, y: int) -> dict[str, Any]:
        return {
            "x": x,
            "y": y,
            "warps_here": _events_at(map_data.get("warp_events", []), x, y),
            "coord_events_here": _events_at(map_data.get("coord_events", []), x, y),
            "bg_events_here": _events_at(map_data.get("bg_events", []), x, y),
        }


def load_map_registry(repo_root: Path) -> FireRedMapRegistry:
    """Load FireRed map and layout metadata from the source tree."""

    map_groups_path = repo_root / "data" / "maps" / "map_groups.json"
    layouts_path = repo_root / "data" / "layouts" / "layouts.json"
    maps_dir = repo_root / "data" / "maps"
    map_groups = json.loads(map_groups_path.read_text(encoding="utf-8"))
    layouts = json.loads(layouts_path.read_text(encoding="utf-8"))["layouts"]
    maps_by_id = _load_maps(maps_dir)
    return FireRedMapRegistry(
        maps_by_id=maps_by_id,
        layouts_by_id={layout["id"]: layout for layout in layouts if "id" in layout},
        id_by_group_number=_build_group_number_index(map_groups, maps_by_id),
    )


def try_load_map_registry(repo_root: Path) -> FireRedMapRegistry | None:
    """Load the map registry when map assets are present under `repo_root`."""

    if not (repo_root / "data" / "maps" / "map_groups.json").exists():
        return None
    if not (repo_root / "data" / "layouts" / "layouts.json").exists():
        return None
    return load_map_registry(repo_root)


def _load_maps(maps_dir: Path) -> dict[str, dict[str, Any]]:
    maps_by_id: dict[str, dict[str, Any]] = {}
    for path in maps_dir.glob("*/map.json"):
        map_data = json.loads(path.read_text(encoding="utf-8"))
        map_data["source_path"] = str(path)
        maps_by_id[map_data["id"]] = map_data
    return maps_by_id


def _build_group_number_index(
    map_groups: dict[str, Any],
    maps_by_id: dict[str, dict[str, Any]],
) -> dict[tuple[int, int], str]:
    index: dict[tuple[int, int], str] = {}
    ids_by_source_name = {metadata["name"]: map_id for map_id, metadata in maps_by_id.items()}
    for group_number, group_name in enumerate(map_groups["group_order"]):
        for map_number, map_name in enumerate(map_groups[group_name]):
            # Source names and IDs are both explicit. Guessing IDs from CamelCase
            # splits numeric floor names such as 2F and silently loses real maps.
            if map_name not in ids_by_source_name:
                raise ValueError(f"map group references missing source map: {map_name}")
            index[(group_number, map_number)] = ids_by_source_name[map_name]
    return index


def _find_group_number(index: dict[tuple[int, int], str], map_id: str) -> tuple[int, int] | None:
    return next((group_number for group_number, indexed_id in index.items() if indexed_id == map_id), None)


def _events_at(events: list[dict[str, Any]], x: int, y: int) -> list[dict[str, Any]]:
    return [event for event in events if event.get("x") == x and event.get("y") == y]
