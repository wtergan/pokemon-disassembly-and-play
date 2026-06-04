from __future__ import annotations

import hashlib
from pathlib import Path

from tools.runtime.emulators.base import EmulatorHealth, Snapshot
from tools.runtime.games.firered.symbols import (
    FIRERED_REV1_CORE_SYMBOLS,
    SymbolTable,
    discover_symbol_table,
    find_default_symbol_file,
    parse_symbol_text,
)
from tools.runtime.games.firered.telemetry import FireRedTelemetryReader
from tools.runtime.games.firered.map_data import load_map_registry
from tools.runtime.games.firered.text import load_charmap


SUBSTRUCT_ORDERS = (
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (0, 3, 1, 2),
    (0, 2, 3, 1),
    (0, 3, 2, 1),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (2, 0, 1, 3),
    (3, 0, 1, 2),
    (2, 0, 3, 1),
    (3, 0, 2, 1),
    (1, 2, 0, 3),
    (1, 3, 0, 2),
    (2, 1, 0, 3),
    (3, 1, 0, 2),
    (2, 3, 0, 1),
    (3, 2, 0, 1),
    (1, 2, 3, 0),
    (1, 3, 2, 0),
    (2, 1, 3, 0),
    (3, 1, 2, 0),
    (2, 3, 1, 0),
    (3, 2, 1, 0),
)


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
            "gMain": 0x03003000,
            "gPaletteFade": 0x02002000,
            "gTasks": 0x03004000,
            "CB2_ReturnToField": 0x08001000,
        },
        source=Path("pokefirered_rev1.sym"),
    )
    emulator = AddressedMemoryEmulator()
    save_block_1 = 0x02025000
    save_block_2 = 0x02024000
    emulator.write32(0x03005008, save_block_1)
    emulator.write32(0x0300500C, save_block_2)
    emulator.write32(0x03003000 + 0x04, 0x08001000)
    emulator.write16(save_block_1 + 0x0000, 10)
    emulator.write16(save_block_1 + 0x0002, 20)
    emulator.write8(save_block_1 + 0x0004, 3)
    emulator.write8(save_block_1 + 0x0005, 0)
    emulator.write8(save_block_1 + 0x0006, 255)
    emulator.write8(save_block_1 + 0x0034, 2)
    write_party_member(
        emulator,
        save_block_1 + 0x0038,
        personality=0x00000018,
        ot_id=0x13572468,
        nickname=[0xCA, 0xC3, 0xC5, 0xBB, 0xFF, 0, 0, 0, 0, 0],
        species=25,
        held_item=100,
        level=12,
        hp=31,
        max_hp=44,
        status=0x00000008,
    )
    write_party_member(
        emulator,
        save_block_1 + 0x0038 + 100,
        personality=0x00000019,
        ot_id=0x24681357,
        nickname=[0xBB, 0xD6, 0xE6, 0xD5, 0xFF, 0, 0, 0, 0, 0],
        species=1,
        held_item=0,
        level=5,
        hp=20,
        max_hp=20,
        status=0,
    )
    emulator.write32(save_block_1 + 0x0290, 12345 ^ 0x12345678)
    emulator.write16(save_block_1 + 0x0294, 42)
    emulator.write16(save_block_1 + 0x0310, 13)
    emulator.write16(save_block_1 + 0x0312, 5 ^ (0x12345678 & 0xFFFF))
    emulator.write8(save_block_1 + 0x0EE0, 0x80)
    emulator.write16(save_block_1 + 0x1000, 0x4000)
    for offset, value in enumerate([0xCC, 0xBF, 0xBE, 0xFF, 0x00, 0x00, 0x00, 0x00]):
        emulator.write8(save_block_2 + offset, value)
    emulator.write8(save_block_2 + 0x0008, 1)
    emulator.write8(save_block_2 + 0x000A, 0x12)
    emulator.write8(save_block_2 + 0x000B, 0x34)
    emulator.write8(save_block_2 + 0x000C, 0x56)
    emulator.write8(save_block_2 + 0x000D, 0x78)
    emulator.write16(save_block_2 + 0x000E, 99)
    emulator.write8(save_block_2 + 0x0010, 58)
    emulator.write8(save_block_2 + 0x0011, 57)
    emulator.write32(save_block_2 + 0x0F20, 0x12345678)
    emulator.write8(0x02001000, 1)
    emulator.write32(0x02001000 + 0x04, 1234)
    emulator.write32(0x02001000 + 0x08, 0xFFFFFED9)

    telemetry = FireRedTelemetryReader(
        symbols,
        rom_path=rom_path,
        map_registry=load_map_registry(Path.cwd()),
        text_decoder=load_charmap(Path.cwd() / "charmap.txt"),
        expected_sha1=expected_sha1,
    )(emulator)

    assert telemetry["frame"] == 88
    assert telemetry["rom"]["matches_expected"] is True
    assert telemetry["symbols"]["available"] is True
    assert telemetry["symbols"]["source"] == "pokefirered_rev1.sym"
    assert telemetry["save_blocks"]["gSaveBlock1Ptr"]["value"] == save_block_1
    assert telemetry["save_blocks"]["gSaveBlock2Ptr"]["encryption_key"] == 0x12345678
    assert telemetry["location"] == {
        "available": True,
        "map_group": 3,
        "map_num": 0,
        "warp_id": -1,
        "player_x": 10,
        "player_y": 20,
        "map": telemetry["location"]["map"],
    }
    assert telemetry["location"]["map"]["id"] == "MAP_PALLET_TOWN"
    assert telemetry["location"]["map"]["layout"]["width"] == 24
    assert telemetry["mode"]["name"] == "field"
    assert telemetry["mode"]["confidence"] == "medium"
    assert telemetry["mode"]["evidence"]["gMain"]["callback2_name"] == "CB2_ReturnToField"
    assert telemetry["camera"] == {
        "available": True,
        "symbol_address": 0x02001000,
        "active": True,
        "x": 1234,
        "y": -295,
    }
    assert telemetry["save"]["available"] is True
    assert telemetry["save"]["player"] == {
        "available": True,
        "name_bytes": [0xCC, 0xBF, 0xBE, 0xFF, 0x00, 0x00, 0x00, 0x00],
        "name": "RED",
        "gender": 1,
        "trainer_id": [0x12, 0x34, 0x56, 0x78],
        "play_time": {"hours": 99, "minutes": 58, "seconds": 57},
    }
    assert telemetry["save"]["party"]["count"] == 2
    assert telemetry["save"]["party"]["capacity"] == 6
    assert telemetry["save"]["party"]["members"][0] == {
        "available": True,
        "index": 0,
        "personality": 0x00000018,
        "ot_id": 0x13572468,
        "nickname_bytes": [0xCA, 0xC3, 0xC5, 0xBB, 0xFF, 0, 0, 0, 0, 0],
        "nickname": "PIKA",
        "species": 25,
        "held_item": 100,
        "level": 12,
        "hp": 31,
        "max_hp": 44,
        "status": 0x00000008,
        "checksum": telemetry["save"]["party"]["members"][0]["checksum"],
    }
    assert telemetry["save"]["party"]["members"][1]["species"] == 1
    assert telemetry["save"]["party"]["members"][1]["level"] == 5
    assert telemetry["save"]["money"] == {"available": True, "value": 12345}
    assert telemetry["save"]["coins"] == 42
    assert telemetry["save"]["bag_pockets"]["items"] == {
        "capacity": 42,
        "used_slots": 1,
        "total_quantity": 5,
        "quantity_available": True,
    }
    assert telemetry["save"]["flags"] == {"bytes": 288, "nonzero_bytes": 1}
    assert telemetry["save"]["vars"] == {"entries": 256, "nonzero_entries": 1}


def test_invalid_saveblock2_pointer_should_not_read_encryption_key() -> None:
    symbols = SymbolTable(
        {
            "gSaveBlock1Ptr": 0x03005008,
            "gSaveBlock2Ptr": 0x0300500C,
            "gCamera": 0x02001000,
        }
    )
    emulator = AddressedMemoryEmulator()
    emulator.write32(0x03005008, 0x02025000)
    emulator.write32(0x0300500C, 0x00000001)

    telemetry = FireRedTelemetryReader(symbols)(emulator)

    assert telemetry["save_blocks"]["gSaveBlock2Ptr"]["available"] is False
    assert telemetry["save_blocks"]["gSaveBlock2Ptr"]["reason"] == "invalid_pointer"
    assert "encryption_key" not in telemetry["save_blocks"]["gSaveBlock2Ptr"]
    assert telemetry["save"]["money"]["available"] is False
    assert telemetry["save"]["bag_pockets"]["items"]["quantity_available"] is False


def test_bad_party_checksum_should_report_unavailable_member() -> None:
    symbols = SymbolTable(
        {
            "gSaveBlock1Ptr": 0x03005008,
            "gSaveBlock2Ptr": 0x0300500C,
            "gCamera": 0x02001000,
        }
    )
    emulator = AddressedMemoryEmulator()
    save_block_1 = 0x02025000
    save_block_2 = 0x02024000
    emulator.write32(0x03005008, save_block_1)
    emulator.write32(0x0300500C, save_block_2)
    emulator.write8(save_block_1 + 0x0034, 1)
    write_party_member(
        emulator,
        save_block_1 + 0x0038,
        personality=0x00000018,
        ot_id=0x13572468,
        nickname=[0] * 10,
        species=25,
        held_item=0,
        level=12,
        hp=31,
        max_hp=44,
        status=0,
    )
    emulator.write16(save_block_1 + 0x0038 + 0x1C, 0xFFFF)

    telemetry = FireRedTelemetryReader(symbols)(emulator)

    member = telemetry["save"]["party"]["members"][0]
    assert member["available"] is False
    assert member["reason"] == "checksum_mismatch"
    assert member["calculated_checksum"] != member["checksum"]


def test_firered_telemetry_should_report_missing_symbols() -> None:
    telemetry = FireRedTelemetryReader(SymbolTable.empty())(AddressedMemoryEmulator())

    assert telemetry["symbols"]["available"] is False
    assert telemetry["symbols"]["missing"] == ["gSaveBlock1Ptr", "gSaveBlock2Ptr", "gCamera"]
    assert telemetry["save_blocks"]["gSaveBlock1Ptr"]["reason"] == "missing_symbol"
    assert telemetry["location"] == {"available": False, "reason": "missing_save_block_1"}
    assert telemetry["camera"] == {"available": False, "reason": "missing_symbol"}


def test_firered_symbol_text_should_parse_objdump_and_simple_formats() -> None:
    symbols = parse_symbol_text(
        """
02001000 g 0000000c gCamera
03005008 gSaveBlock1Ptr
                0x0300500c                gSaveBlock2Ptr
ignored
"""
    )

    assert symbols == {
        "gCamera": 0x02001000,
        "gSaveBlock1Ptr": 0x03005008,
        "gSaveBlock2Ptr": 0x0300500C,
    }


def test_firered_symbol_coverage_should_report_missing_core_symbols() -> None:
    coverage = SymbolTable({"gSaveBlock1Ptr": 0x03005008}).coverage(FIRERED_REV1_CORE_SYMBOLS)

    assert coverage.available is False
    assert coverage.addresses == {"gSaveBlock1Ptr": 0x03005008}
    assert "gSaveBlock2Ptr" in coverage.missing
    assert "gMain" in coverage.missing


def test_firered_default_symbol_file_should_be_discovered(tmp_path: Path) -> None:
    symbol_path = tmp_path / "pokefirered_rev1.sym"
    symbol_path.write_text("03005008 gSaveBlock1Ptr\n", encoding="utf-8")

    assert find_default_symbol_file(tmp_path) == symbol_path
    assert discover_symbol_table(tmp_path).require("gSaveBlock1Ptr") == 0x03005008


def write_party_member(
    emulator: AddressedMemoryEmulator,
    address: int,
    *,
    personality: int,
    ot_id: int,
    nickname: list[int],
    species: int,
    held_item: int,
    level: int,
    hp: int,
    max_hp: int,
    status: int,
) -> None:
    secure = bytearray(48)
    order = SUBSTRUCT_ORDERS[personality % len(SUBSTRUCT_ORDERS)]
    substruct0 = order[0] * 12
    secure[substruct0 : substruct0 + 2] = species.to_bytes(2, "little")
    secure[substruct0 + 2 : substruct0 + 4] = held_item.to_bytes(2, "little")
    checksum = sum(int.from_bytes(secure[offset : offset + 2], "little") for offset in range(0, len(secure), 2))
    key = personality ^ ot_id

    emulator.write32(address, personality)
    emulator.write32(address + 0x04, ot_id)
    for offset, value in enumerate(nickname):
        emulator.write8(address + 0x08 + offset, value)
    emulator.write16(address + 0x1C, checksum & 0xFFFF)
    for index in range(12):
        raw = int.from_bytes(secure[index * 4 : index * 4 + 4], "little")
        emulator.write32(address + 0x20 + (index * 4), raw ^ key)
    emulator.write32(address + 0x50, status)
    emulator.write8(address + 0x54, level)
    emulator.write16(address + 0x56, hp)
    emulator.write16(address + 0x58, max_hp)
