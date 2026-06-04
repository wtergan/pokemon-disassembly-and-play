from __future__ import annotations

import hashlib
from pathlib import Path

from tools.runtime.emulators.base import EmulatorHealth, Snapshot
from tools.runtime.games.firered.symbols import SymbolTable, parse_symbol_text
from tools.runtime.games.firered.telemetry import FireRedTelemetryReader


class AddressedMemoryEmulator:
    def __init__(self) -> None:
        self._memory: dict[int, int] = {}
        self._frame_count = 88

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def health(self) -> EmulatorHealth:
        return EmulatorHealth(running=True, frame=self._frame_count, bridge="fixture")

    def snapshot(self) -> Snapshot:
        return Snapshot(frame=self._frame_count, image_base64="")

    def press_button(self, button: str) -> None:
        pass

    def release_button(self, button: str) -> None:
        pass

    def run_frames(self, frames: int) -> None:
        self._frame_count += frames

    def read8(self, address: int) -> int:
        return self._memory.get(address, 0)

    def read16(self, address: int) -> int:
        return self.read8(address) | (self.read8(address + 1) << 8)

    def read32(self, address: int) -> int:
        return self.read16(address) | (self.read16(address + 2) << 16)

    def write8(self, address: int, value: int) -> None:
        self._memory[address] = value & 0xFF

    def write16(self, address: int, value: int) -> None:
        self.write8(address, value)
        self.write8(address + 1, value >> 8)

    def write32(self, address: int, value: int) -> None:
        self.write16(address, value)
        self.write16(address + 2, value >> 16)


def test_firered_saveblock_fixture_should_decode_position(tmp_path: Path) -> None:
    rom_path = tmp_path / "firered_rev1.gba"
    rom_path.write_bytes(b"fixture rom")
    expected_sha1 = hashlib.sha1(b"fixture rom").hexdigest()
    symbols = SymbolTable(
        {
            "gSaveBlock1Ptr": 0x03005008,
            "gSaveBlock2Ptr": 0x0300500C,
            "gCamera": 0x02001000,
        },
        source=Path("pokefirered_rev1.sym"),
    )
    emulator = AddressedMemoryEmulator()
    save_block_1 = 0x02025000
    save_block_2 = 0x02024000
    emulator.write32(0x03005008, save_block_1)
    emulator.write32(0x0300500C, save_block_2)
    emulator.write16(save_block_1 + 0x0000, 10)
    emulator.write16(save_block_1 + 0x0002, 20)
    emulator.write8(save_block_1 + 0x0004, 3)
    emulator.write8(save_block_1 + 0x0005, 7)
    emulator.write8(save_block_1 + 0x0006, 255)
    emulator.write32(save_block_2 + 0x0F20, 0x12345678)
    emulator.write8(0x02001000, 1)
    emulator.write32(0x02001000 + 0x04, 1234)
    emulator.write32(0x02001000 + 0x08, 0xFFFFFED9)

    telemetry = FireRedTelemetryReader(symbols, rom_path=rom_path, expected_sha1=expected_sha1)(emulator)

    assert telemetry["frame"] == 88
    assert telemetry["rom"]["matches_expected"] is True
    assert telemetry["symbols"]["available"] is True
    assert telemetry["save_blocks"]["gSaveBlock1Ptr"]["value"] == save_block_1
    assert telemetry["save_blocks"]["gSaveBlock2Ptr"]["encryption_key"] == 0x12345678
    assert telemetry["location"] == {
        "available": True,
        "map_group": 3,
        "map_num": 7,
        "warp_id": -1,
        "player_x": 10,
        "player_y": 20,
    }
    assert telemetry["camera"] == {
        "available": True,
        "symbol_address": 0x02001000,
        "active": True,
        "x": 1234,
        "y": -295,
    }


def test_firered_telemetry_should_report_missing_symbols() -> None:
    telemetry = FireRedTelemetryReader(SymbolTable.empty())(AddressedMemoryEmulator())

    assert telemetry["symbols"]["available"] is False
    assert telemetry["symbols"]["missing"] == ["gSaveBlock1Ptr", "gSaveBlock2Ptr"]
    assert telemetry["save_blocks"]["gSaveBlock1Ptr"]["reason"] == "missing_symbol"
    assert telemetry["location"] == {"available": False, "reason": "missing_save_block_1"}
    assert telemetry["camera"] == {"available": False, "reason": "missing_symbol"}


def test_firered_symbol_text_should_parse_objdump_and_simple_formats() -> None:
    symbols = parse_symbol_text(
        """
02001000 g 0000000c gCamera
03005008 gSaveBlock1Ptr
ignored
"""
    )

    assert symbols == {"gCamera": 0x02001000, "gSaveBlock1Ptr": 0x03005008}
