"""Behavior guards for semantic FireRed telemetry and safe memory reads.

These tests pin runtime mode and SaveBlock boundaries to pret/pokefirered
source, while tracking reads so startup snapshots cannot trigger a full save
scan before the actual overworld callback is active.
"""

from __future__ import annotations

from tools.runtime.games.firered.map_data import FireRedMapRegistry
from tools.runtime.games.firered.mode import classify_runtime_mode
from tools.runtime.games.firered.save_blocks import (
    GBA_EWRAM_END,
    GBA_EWRAM_START,
    SAVE_BLOCK_2_SIZE,
    read_save_block_summary,
)
from tools.runtime.games.firered.symbols import SymbolTable
from tools.runtime.games.firered.telemetry import FireRedTelemetryReader

SAVE_BLOCK_1_SIZE = 0x3D68


class TrackedMemory:
    """Small address-backed emulator fixture that records every memory read."""

    def __init__(self) -> None:
        self.memory: dict[int, int] = {}
        self.reads: list[tuple[int, int]] = []
        self.frame_count = 1

    def read8(self, address: int) -> int:
        self.reads.append((address, 1))
        return self.memory.get(address, 0)

    def read16(self, address: int) -> int:
        self.reads.append((address, 2))
        return self.read8(address) | (self.read8(address + 1) << 8)

    def read32(self, address: int) -> int:
        self.reads.append((address, 4))
        return self.read16(address) | (self.read16(address + 2) << 16)

    def write8(self, address: int, value: int) -> None:
        self.memory[address] = value & 0xFF

    def write16(self, address: int, value: int) -> None:
        self.write8(address, value)
        self.write8(address + 1, value >> 8)

    def write32(self, address: int, value: int) -> None:
        self.write16(address, value)
        self.write16(address + 2, value >> 16)


class RangeTrackedMemory(TrackedMemory):
    """Fixture for the page-read bridge method used by BufferedMemory."""

    def __init__(self) -> None:
        super().__init__()
        self.range_reads: list[tuple[int, int]] = []

    def read_range(self, address: int, length: int) -> bytes:
        self.range_reads.append((address, length))
        return bytes(self.memory.get(address + offset, 0) for offset in range(length))


def _map_registry(width: int = 24, height: int = 21) -> FireRedMapRegistry:
    return FireRedMapRegistry(
        maps_by_id={
            "MAP_PALLET_TOWN": {
                "id": "MAP_PALLET_TOWN",
                "name": "Pallet Town",
                "layout": "LAYOUT_PALLET_TOWN",
                "map_type": "town",
                "region_map_section": "PALLET_TOWN",
                "connections": [],
                "warp_events": [],
                "object_events": [],
                "coord_events": [],
                "bg_events": [],
            }
        },
        layouts_by_id={
            "LAYOUT_PALLET_TOWN": {
                "id": "LAYOUT_PALLET_TOWN",
                "name": "Pallet Town",
                "width": width,
                "height": height,
            }
        },
        id_by_group_number={(3, 0): "MAP_PALLET_TOWN"},
    )


def _runtime_symbols(callback_name: str = "CB2_Overworld") -> tuple[SymbolTable, TrackedMemory]:
    symbols = SymbolTable(
        {
            "gSaveBlock1Ptr": 0x03003000,
            "gSaveBlock2Ptr": 0x03003004,
            "gCamera": 0x02003000,
            "gMain": 0x03001000,
            "gPaletteFade": 0x02002000,
            "gTasks": 0x03004000,
            callback_name: 0x08000100,
        }
    )
    emulator = TrackedMemory()
    emulator.write32(0x03003000, 0x02010000)
    emulator.write32(0x03003004, 0x02008000)
    emulator.write32(0x03001004, 0x08000101)
    emulator.write8(0x02010000 + 0x04, 3)
    emulator.write8(0x02010000 + 0x05, 0)
    emulator.write16(0x02010000 + 0x00, 4)
    emulator.write16(0x02010000 + 0x02, 5)
    return symbols, emulator


def test_thumb_overworld_callback_should_confirm_field_mode() -> None:
    symbols, emulator = _runtime_symbols()

    mode = classify_runtime_mode(emulator, symbols, location_available=False)

    assert mode["name"] == "field"
    assert mode["confidence"] == "high"
    assert mode["evidence"]["gMain"]["callback2_name"] == "CB2_Overworld"
    assert mode["evidence"]["gMain"]["callback2_normalized"] == 0x08000100


def test_palette_fade_active_should_read_source_backed_byte_seven() -> None:
    symbols = SymbolTable({"gMain": 0x03001000, "gPaletteFade": 0x02002000, "gTasks": 0x03004000})
    emulator = TrackedMemory()
    emulator.write8(0x02002000 + 0x07, 0x80)

    mode = classify_runtime_mode(emulator, symbols, location_available=False)

    assert mode["name"] == "transition_loading"
    assert mode["evidence"]["gPaletteFade"]["active_byte"] == 0x80

    emulator = TrackedMemory()
    emulator.write8(0x02002000 + 0x08, 0x80)
    mode = classify_runtime_mode(emulator, symbols, location_available=False)

    assert mode["name"] == "unknown"


def test_battle_flag_should_use_gmain_flags_byte_439() -> None:
    symbols = SymbolTable({"gMain": 0x03001000, "gPaletteFade": 0x02002000, "gTasks": 0x03004000})
    emulator = TrackedMemory()
    emulator.write8(0x03001000 + 0x439, 0x02)

    mode = classify_runtime_mode(emulator, symbols, location_available=False)

    assert mode["name"] == "battle"
    assert mode["evidence"]["gMain"]["in_battle"] is True


def test_known_map_without_overworld_callback_should_not_decode_save_summary() -> None:
    symbols, emulator = _runtime_symbols("CB2_InitTitleScreen")

    telemetry = FireRedTelemetryReader(symbols, map_registry=_map_registry())(emulator)

    assert telemetry["mode"]["name"] == "unknown"
    assert telemetry["location"]["available"] is True
    assert telemetry["save"] == {"available": False, "reason": "overworld_callback_not_confirmed"}
    assert not any(0x02010000 + 0x0034 <= address < 0x02010000 + SAVE_BLOCK_1_SIZE for address, _ in emulator.reads)
    assert not any(0x02008000 <= address < 0x02008000 + 0xF24 for address, _ in emulator.reads)


def test_save_block_pointer_should_require_aligned_full_ewram_extent() -> None:
    for pointer in (
        GBA_EWRAM_START + 1,
        GBA_EWRAM_END - SAVE_BLOCK_1_SIZE + 4,
        0x03000000,
        0x08000000,
    ):
        emulator = TrackedMemory()

        summary = read_save_block_summary(emulator, pointer, None)

        assert summary == {"available": False, "reason": "missing_save_block_1"}
        assert emulator.reads == []


def test_save_block_2_pointer_should_not_read_past_ewram_end() -> None:
    emulator = TrackedMemory()
    save_block_1 = 0x02010000
    save_block_2 = GBA_EWRAM_END - SAVE_BLOCK_2_SIZE + 4

    summary = read_save_block_summary(emulator, save_block_1, save_block_2)

    assert summary["available"] is True
    assert summary["player"] == {"available": False, "reason": "missing_save_block_2"}
    assert not any(address >= save_block_2 for address, _ in emulator.reads)


def test_position_outside_layout_should_make_location_unavailable() -> None:
    symbols, emulator = _runtime_symbols()
    emulator.write16(0x02010000 + 0x00, 24)

    telemetry = FireRedTelemetryReader(symbols, map_registry=_map_registry())(emulator)

    assert telemetry["mode"]["name"] == "field"
    assert telemetry["location"]["available"] is False
    assert telemetry["location"]["reason"] == "position_outside_layout"
    assert telemetry["location"]["map"]["position"]["within_layout"] is False


def test_dialogue_task_thumb_pointer_should_keep_valid_location_available() -> None:
    symbols, emulator = _runtime_symbols()
    symbols = SymbolTable({**symbols.addresses, "Task_DrawFieldMessageBox": 0x08000200})
    emulator.write32(0x03004000, 0x08000201)
    emulator.write8(0x03004004, 1)

    telemetry = FireRedTelemetryReader(symbols, map_registry=_map_registry())(emulator)

    assert telemetry["mode"]["name"] == "dialogue_textbox"
    assert telemetry["mode"]["evidence"]["gTasks"]["active"][0]["func_name"] == "Task_DrawFieldMessageBox"
    assert telemetry["location"]["available"] is True


def test_read_range_bridge_should_use_one_cached_page_per_telemetry_call() -> None:
    symbols, _ = _runtime_symbols()
    emulator = RangeTrackedMemory()
    emulator.write32(0x03003000, 0x02010000)
    emulator.write32(0x03003004, 0x02008000)
    emulator.write32(0x03001004, 0x08000101)

    telemetry = FireRedTelemetryReader(symbols)(emulator)

    assert telemetry["mode"]["name"] == "field"
    assert 0 < len(emulator.range_reads) <= 11
    assert all(length == 4096 for _, length in emulator.range_reads)
    assert emulator.reads == []


def test_source_registry_should_resolve_starting_bedroom_with_number_suffix():
    from pathlib import Path
    from tools.runtime.games.firered.map_data import load_map_registry

    registry = load_map_registry(Path(__file__).resolve().parents[3])
    location = registry.describe_location(4, 1, 6, 6)
    assert location['available'] is True
    assert location['id'] == 'MAP_PALLET_TOWN_PLAYERS_HOUSE_2F'
    assert location['layout']['width'] == 12
