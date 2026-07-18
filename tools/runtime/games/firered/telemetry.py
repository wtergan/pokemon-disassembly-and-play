"""Minimal FireRed Rev 1 telemetry decoding.

The first telemetry slice intentionally reads only source-backed, unencrypted
fields: ROM identity, SaveBlock pointers, map location, player coordinates, and
camera coordinates when the generated symbols are available.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...emulators.base import EmulatorBridge
from ...state_models import TELEMETRY_SCHEMA_VERSION, normalize_telemetry_snapshot
from .memory import BufferedMemory
from .map_data import FireRedMapRegistry
from .mode import classify_runtime_mode
from .save_blocks import (
    SAVE_BLOCK_1_LOCATION_MAP_GROUP,
    SAVE_BLOCK_1_LOCATION_MAP_NUM,
    SAVE_BLOCK_1_LOCATION_WARP_ID,
    SAVE_BLOCK_1_POS_X,
    SAVE_BLOCK_1_POS_Y,
    SAVE_BLOCK_2_ENCRYPTION_KEY,
    SAVE_BLOCK_1_SIZE,
    SAVE_BLOCK_2_SIZE,
    is_save_block_pointer,
    read_save_block_summary,
)
from .symbols import SymbolTable
from .text import FireRedCharmap


FIRERED_REV1_SHA1 = "dd5945db9b930750cb39d00c84da8571feebf417"
_TELEMETRY_SYMBOLS = ("gSaveBlock1Ptr", "gSaveBlock2Ptr", "gCamera")
_CAMERA_SYMBOL = "gCamera"


@dataclass(frozen=True)
class FireRedTelemetryReader:
    """Callable telemetry reader for FireRed Rev 1 runtime state."""

    symbols: SymbolTable
    rom_path: Path | None = None
    map_registry: FireRedMapRegistry | None = None
    text_decoder: FireRedCharmap | None = None
    expected_sha1: str = FIRERED_REV1_SHA1
    game: str = "firered"
    revision: str = "rev1"

    def __call__(self, emulator: EmulatorBridge) -> dict[str, Any]:
        """Read the smallest source-backed telemetry payload from `emulator`."""

        if callable(getattr(emulator, "read_range", None)):
            emulator = BufferedMemory(emulator)
        save_block_1 = self._read_pointer(emulator, "gSaveBlock1Ptr")
        save_block_2 = self._read_pointer(emulator, "gSaveBlock2Ptr")
        symbol_coverage = self.symbols.coverage(_TELEMETRY_SYMBOLS)

        location = self._read_location(emulator, save_block_1["value"])
        mode = classify_runtime_mode(emulator, self.symbols, location_available=location["available"])
        overworld_callback_active = mode["evidence"]["gMain"].get("callback2_name") == "CB2_Overworld"
        save_summary = (
            read_save_block_summary(
                emulator,
                save_block_1["value"],
                save_block_2["value"],
                text_decoder=self.text_decoder,
            )
            if overworld_callback_active
            else {"available": False, "reason": "overworld_callback_not_confirmed"}
        )
        payload: dict[str, Any] = {
            "schema_version": TELEMETRY_SCHEMA_VERSION,
            "game": self.game,
            "revision": self.revision,
            "frame": emulator.frame_count,
            "rom": self._rom_identity(),
            "symbols": {
                "available": symbol_coverage.available,
                "source": self.symbols.source.name if self.symbols.source else None,
                "missing": symbol_coverage.missing,
            },
            "save_blocks": {
                "gSaveBlock1Ptr": save_block_1,
                "gSaveBlock2Ptr": save_block_2,
            },
            "location": location,
            "mode": mode,
            "camera": self._read_camera(emulator),
            "save": save_summary,
        }
        if overworld_callback_active and is_save_block_pointer(save_block_2["value"], SAVE_BLOCK_2_SIZE):
            payload["save_blocks"]["gSaveBlock2Ptr"]["encryption_key"] = emulator.read32(
                save_block_2["value"] + SAVE_BLOCK_2_ENCRYPTION_KEY
            )
        return normalize_telemetry_snapshot(payload)

    def _read_pointer(self, emulator: EmulatorBridge, symbol_name: str) -> dict[str, Any]:
        symbol_address = self.symbols.get(symbol_name)
        if symbol_address is None:
            return {"available": False, "symbol_address": None, "value": None, "reason": "missing_symbol"}
        pointer = emulator.read32(symbol_address)
        pointer_size = SAVE_BLOCK_1_SIZE if symbol_name == "gSaveBlock1Ptr" else SAVE_BLOCK_2_SIZE
        pointer_is_valid = is_save_block_pointer(pointer, pointer_size)
        return {
            "available": pointer_is_valid,
            "symbol_address": symbol_address,
            "value": pointer,
            "reason": None if pointer_is_valid else "invalid_pointer",
        }

    def _read_location(self, emulator: EmulatorBridge, save_block_1: int | None) -> dict[str, Any]:
        if not is_save_block_pointer(save_block_1, SAVE_BLOCK_1_SIZE):
            return {"available": False, "reason": "missing_save_block_1"}
        map_group = _read_s8(emulator, save_block_1 + SAVE_BLOCK_1_LOCATION_MAP_GROUP)
        map_num = _read_s8(emulator, save_block_1 + SAVE_BLOCK_1_LOCATION_MAP_NUM)
        player_x = _read_s16(emulator, save_block_1 + SAVE_BLOCK_1_POS_X)
        player_y = _read_s16(emulator, save_block_1 + SAVE_BLOCK_1_POS_Y)
        map_context = (
            self.map_registry.describe_location(map_group, map_num, player_x, player_y)
            if self.map_registry is not None
            else {"available": False, "reason": "map_registry_unavailable"}
        )
        map_available = bool(map_context.get("available"))
        position_available = False
        position_reason = map_context.get("reason", "unknown_map")
        if map_available:
            layout = map_context.get("layout")
            width = layout.get("width") if isinstance(layout, dict) else None
            height = layout.get("height") if isinstance(layout, dict) else None
            if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
                position_reason = "map_layout_unavailable"
            else:
                position_available = 0 <= player_x < width and 0 <= player_y < height
                position_reason = None if position_available else "position_outside_layout"
                map_context["position"]["within_layout"] = position_available
        return {
            "available": position_available,
            "reason": position_reason,
            "map_group": map_group,
            "map_num": map_num,
            "warp_id": _read_s8(emulator, save_block_1 + SAVE_BLOCK_1_LOCATION_WARP_ID),
            "player_x": player_x,
            "player_y": player_y,
            "map": map_context,
        }

    def _read_camera(self, emulator: EmulatorBridge) -> dict[str, Any]:
        camera_address = self.symbols.get(_CAMERA_SYMBOL)
        if camera_address is None:
            return {"available": False, "reason": "missing_symbol"}
        return {
            "available": True,
            "symbol_address": camera_address,
            "active": bool(emulator.read8(camera_address) & 0x01),
            "x": _read_s32(emulator, camera_address + 0x04),
            "y": _read_s32(emulator, camera_address + 0x08),
        }

    def _rom_identity(self) -> dict[str, Any]:
        if self.rom_path is None:
            return {"available": False, "sha1": None, "expected_sha1": self.expected_sha1, "matches_expected": None}
        sha1 = _sha1_file(self.rom_path)
        return {
            "available": True,
            "name": self.rom_path.name,
            "sha1": sha1,
            "expected_sha1": self.expected_sha1,
            "matches_expected": sha1 == self.expected_sha1,
        }

def _read_s8(emulator: EmulatorBridge, address: int) -> int:
    value = emulator.read8(address)
    return value - 0x100 if value & 0x80 else value


def _read_s16(emulator: EmulatorBridge, address: int) -> int:
    value = emulator.read16(address)
    return value - 0x10000 if value & 0x8000 else value


def _read_s32(emulator: EmulatorBridge, address: int) -> int:
    value = emulator.read32(address)
    return value - 0x100000000 if value & 0x80000000 else value


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
