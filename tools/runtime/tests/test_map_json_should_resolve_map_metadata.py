from __future__ import annotations

from pathlib import Path

from tools.runtime.games.firered.map_data import load_map_registry


def test_map_json_should_resolve_pallet_town_metadata() -> None:
    registry = load_map_registry(Path.cwd())

    pallet_town = registry.describe_map_id("MAP_PALLET_TOWN")

    assert pallet_town["available"] is True
    assert pallet_town["id"] == "MAP_PALLET_TOWN"
    assert pallet_town["name"] == "PalletTown"
    assert pallet_town["map_group"] == 3
    assert pallet_town["layout"]["id"] == "LAYOUT_PALLET_TOWN"
    assert pallet_town["layout"]["width"] == 24
    assert pallet_town["layout"]["height"] == 20
    assert {connection["map"] for connection in pallet_town["connections"]} == {"MAP_ROUTE1", "MAP_ROUTE21_NORTH"}


def test_map_group_number_should_resolve_position_context() -> None:
    registry = load_map_registry(Path.cwd())

    location = registry.describe_location(3, 0, 6, 7)

    assert location["available"] is True
    assert location["id"] == "MAP_PALLET_TOWN"
    assert location["position"]["x"] == 6
    assert location["position"]["y"] == 7
    assert location["position"]["warps_here"][0]["dest_map"] == "MAP_PALLET_TOWN_PLAYERS_HOUSE_1F"


def test_unknown_map_group_should_report_unavailable() -> None:
    registry = load_map_registry(Path.cwd())

    assert registry.describe_location(99, 99) == {
        "available": False,
        "reason": "unknown_group_number",
        "map_group": 99,
        "map_num": 99,
    }
